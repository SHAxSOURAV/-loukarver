import re
from datetime import datetime, date, timedelta, timezone
from typing import Dict, Any, List, Optional
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.db import get_client, get_db

from bson import ObjectId
from app.core.config import settings
from app.schemas.us import MilestoneCreate, MilestoneUpdate, NextMeetCreate, NextMeetUpdate
from app.services.streak import get_time_name

def parse_date(date_str: str) -> date:
    """Parses mm.dd.yyyy or mm.dd,yyyy to date object."""
    parts = re.split(r"[\.,]", date_str)
    return date(int(parts[2]), int(parts[0]), int(parts[1]))

class UsService:
    def __init__(self) -> None:
        self.client = get_client()
        self.db = get_db()
        self.users_collection = self.db["users"]
        self.milestones_collection = self.db["milestones"]
        self.next_meets_collection = self.db["next_meets"]

    async def init_indexes(self):
        try:
            await self.milestones_collection.create_index("user_id")
            await self.next_meets_collection.create_index("user_ids")
        except Exception as e:
            print(f"Error initializing us indexes: {e}")

    async def _get_partner_id(self, user_id: str) -> Optional[str]:
        user = await self.users_collection.find_one({"_id": ObjectId(user_id)})
        if user and user.get("is_aligned") and user.get("partner"):
            return user["partner"].get("user_id")
        return None

    async def get_stats(self, user_id: str, user_doc: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if user_doc:
            user = user_doc
        else:
            user = await self.users_collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise ValueError("User not found.")

        if not user.get("is_aligned") or not user.get("relationship_start_date"):
            return None

        # Reuse already fetched user document to avoid redundant DB roundtrip
        partner_id = user.get("partner", {}).get("user_id") if user.get("partner") else None
        start_date_str = user["relationship_start_date"]
        start_date = parse_date(start_date_str)
        today = date.today()
        
        if start_date > today:
            diff = timedelta(0)
        else:
            diff = today - start_date
            
        total_days = diff.days
        
        years = today.year - start_date.year
        months = today.month - start_date.month
        days = today.day - start_date.day
        
        if days < 0:
            months -= 1
            last_month = today.replace(day=1) - timedelta(days=1)
            days += last_month.day
            
        if months < 0:
            years -= 1
            months += 12
            
        # Next Anniversary
        anniversary_this_year = start_date.replace(year=today.year)
        if anniversary_this_year < today:
            next_anniversary = start_date.replace(year=today.year + 1)
        else:
            next_anniversary = anniversary_this_year
            
        days_until_anniversary = (next_anniversary - today).days
        
        # Milestones
        milestones = []
        
        # 1. Anniversary (Automatic)
        milestones.append({
            "id": f"anniversary_{next_anniversary.year}",
            "title": f"{next_anniversary.year - start_date.year} Year Anniversary",
            "date": next_anniversary.strftime("%m.%d.%Y"),
            "days_left": days_until_anniversary,
            "description": "Celebrating another year together!",
            "type": "anniversary"
        })
        
        # 2. Day Milestones (Automatic)
        milestone_days = [100, 365, 500, 1000, 2000, 5000]
        for md in milestone_days:
            if total_days < md:
                m_date = start_date + timedelta(days=md)
                milestones.append({
                    "id": f"days_{md}",
                    "title": f"{md} Days Together",
                    "date": m_date.strftime("%m.%d.%Y"),
                    "days_left": (m_date - today).days,
                    "description": f"Reaching {md} days of love.",
                    "type": "days"
                })
                break
        
        # 3. User Milestones (Manual)
        user_ids = [user_id]
        if partner_id:
            user_ids.append(partner_id)
            
        cursor = self.milestones_collection.find({"user_id": {"$in": user_ids}})
        db_milestones = await cursor.to_list(length=None)
        
        for m in db_milestones:
            try:
                m_date = parse_date(m["date"])
                days_left = (m_date - today).days
                if days_left >= 0:
                    milestones.append({
                        "id": str(m["_id"]),
                        "title": m["title"],
                        "date": m["date"],
                        "days_left": days_left,
                        "description": m.get("description"),
                        "type": m.get("type", "custom")
                    })
            except Exception:
                # Skip milestones with invalid dates or corrupted data
                continue
                
        milestones.sort(key=lambda x: x["days_left"])

        return {
            "days_passed": days,
            "months_passed": months,
            "years_passed": years,
            "total_days": total_days,
            "relationship_start_date": start_date_str,
            "next_anniversary_date": next_anniversary.strftime("%m.%d.%Y"),
            "days_until_anniversary": days_until_anniversary,
            "upcoming_milestones": milestones
        }

    # Update Start Date
    async def update_start_date(self, user_id: str, new_date: str) -> Dict[str, Any]:
        """Update the relationship_start_date on the user document."""
        user = await self.users_collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise ValueError("User not found.")
        
        # Also update partner's start date so both are in sync
        partner_id = await self._get_partner_id(user_id)
        
        await self.users_collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"relationship_start_date": new_date}}
        )
        
        if partner_id:
            await self.users_collection.update_one(
                {"_id": ObjectId(partner_id)},
                {"$set": {"relationship_start_date": new_date}}
            )
            from app.services.notification import notification_service
            from app.schemas.notification import NotificationCreate, NotificationType
            await notification_service.schedule_notification(
                sender_id=user_id,
                payload=NotificationCreate(
                    recipient_id=partner_id,
                    title="Us Section Update",
                    message="Partner updated the start date",
                    type=NotificationType.US_SECTION_UPDATE,
                    scheduled_for=datetime.now(timezone.utc),
                    timezone="UTC"
                )
            )
        
        return {"relationship_start_date": new_date}

    # Milestone CRUD
    async def create_milestone(self, user_id: str, payload: MilestoneCreate) -> Dict[str, Any]:
        partner_id = await self._get_partner_id(user_id)
        new_doc = {
            "user_id": user_id,
            "partner_id": partner_id,
            "title": payload.title,
            "date": payload.date,
            "description": payload.description,
            "type": payload.type,
            "created_at": datetime.now(timezone.utc)
        }
        result = await self.milestones_collection.insert_one(new_doc)
        new_doc["id"] = str(result.inserted_id)
        new_doc["_id"] = str(result.inserted_id)

        if partner_id:
            from app.core.websocket import ws_manager
            await ws_manager.broadcast_to_user(partner_id, {"type": "DATE_UPDATED"})
            await ws_manager.broadcast_to_user(partner_id, {"type": "MILESTONE_UPDATED"})

        return new_doc

    async def update_milestone(self, user_id: str, milestone_id: str, payload: MilestoneUpdate) -> Dict[str, Any]:
        partner_id = await self._get_partner_id(user_id)
        query = {"_id": ObjectId(milestone_id), "user_id": {"$in": [user_id, partner_id]}} if partner_id else {"_id": ObjectId(milestone_id), "user_id": user_id}
        
        updates = {k: v for k, v in payload.model_dump().items() if v is not None}
        if not updates:
            raise ValueError("No fields to update")
            
        result = await self.milestones_collection.update_one(query, {"$set": updates})
        if result.matched_count == 0:
            raise ValueError("Milestone not found or permission denied")
            
        updated = await self.milestones_collection.find_one({"_id": ObjectId(milestone_id)})
        if updated and "_id" in updated:
            updated["id"] = str(updated["_id"])
            updated["_id"] = str(updated["_id"])

        if partner_id:
            from app.core.websocket import ws_manager
            await ws_manager.broadcast_to_user(partner_id, {"type": "DATE_UPDATED"})
            await ws_manager.broadcast_to_user(partner_id, {"type": "MILESTONE_UPDATED"})

        return updated

    async def delete_milestone(self, user_id: str, milestone_id: str):
        partner_id = await self._get_partner_id(user_id)
        user_ids = [str(user_id)]
        try:
            user_ids.append(ObjectId(user_id))
        except Exception:
            pass
        if partner_id:
            user_ids.append(str(partner_id))
            try:
                user_ids.append(ObjectId(partner_id))
            except Exception:
                pass
        
        query = {
            "_id": ObjectId(milestone_id),
            "$or": [
                {"user_id": {"$in": user_ids}},
                {"creator_id": {"$in": user_ids}},
                {"partner_id": {"$in": user_ids}}
            ]
        }
        
        doc = await self.milestones_collection.find_one(query)
        if not doc:
            raise ValueError("Milestone not found or permission denied")

        result = await self.milestones_collection.delete_one({"_id": ObjectId(milestone_id)})
        if result.deleted_count == 0:
            raise ValueError("Milestone not found or permission denied")

        if partner_id:
            from app.core.websocket import ws_manager
            from app.services.notification import notification_service
            from app.schemas.notification import NotificationCreate, NotificationType

            milestone_title = doc.get("title") or doc.get("name") or "Marked Date"
            creator_id = str(doc.get("user_id") or doc.get("creator_id") or "")
            is_partner_created = bool(creator_id and creator_id == str(partner_id))

            # Broadcast WebSocket updates for instant UI refresh
            await ws_manager.broadcast_to_user(partner_id, {
                "type": "DATE_UPDATED",
                "action": "deleted",
                "milestone_id": str(milestone_id),
                "is_partner_created": is_partner_created,
            })
            await ws_manager.broadcast_to_user(partner_id, {
                "type": "MILESTONE_UPDATED",
                "action": "deleted",
                "milestone_id": str(milestone_id),
                "is_partner_created": is_partner_created,
            })

            try:
                user_doc = await self.users_collection.find_one({"_id": ObjectId(user_id)}, {"name": 1})
                deleter_name = user_doc.get("name", "Your partner") if user_doc else "Your partner"

                if is_partner_created:
                    title = "⚠️ Milestone Removed by Partner"
                    message = f'{deleter_name} removed your marked date: "{milestone_title}"'
                else:
                    title = "⚠️ Shared Marked Date Removed"
                    message = f'{deleter_name} removed the marked date: "{milestone_title}"'

                await notification_service.schedule_notification(
                    sender_id=user_id,
                    payload=NotificationCreate(
                        recipient_id=partner_id,
                        title=title,
                        message=message,
                        type=NotificationType.MILESTONE,
                        scheduled_for=datetime.now(timezone.utc),
                        timezone="UTC",
                        metadata={
                            "screen": "Dates",
                            "milestone_id": str(milestone_id),
                            "milestone_name": milestone_title,
                            "action": "deleted",
                            "is_partner_created": is_partner_created,
                            "deleted_by": user_id,
                            "deleted_by_name": deleter_name,
                        }
                    )
                )
            except Exception as e:
                print(f"Failed to notify partner on us delete_milestone: {e}")

    # Next Meet CRUD
    async def set_next_meet(self, user_id: str, payload: NextMeetCreate) -> Dict[str, Any]:
        partner_id = await self._get_partner_id(user_id)
        if not partner_id:
            raise ValueError("You must be aligned with a partner to set a next meet.")
            
        import zoneinfo
        try:
            zoneinfo.ZoneInfo(payload.timezone)
        except Exception:
            raise ValueError(f"Invalid timezone: {payload.timezone}")

        user_ids = sorted([user_id, partner_id])
        
        date_parts = re.split(r"[\.,]", payload.date)
        time_match = re.match(r"(\d{1,2}):(\d{2})\s*(AM|PM)", payload.time.upper())
        if not time_match:
            raise ValueError("Invalid time format. Expected e.g. 08:30 PM")
            
        hour = int(time_match.group(1))
        minute = int(time_match.group(2))
        ampm = time_match.group(3)
        if ampm == "PM" and hour < 12: hour += 12
        elif ampm == "AM" and hour == 12: hour = 0
            
        local_dt = datetime(int(date_parts[2]), int(date_parts[0]), int(date_parts[1]), hour, minute, tzinfo=zoneinfo.ZoneInfo(payload.timezone))
        utc_dt = local_dt.astimezone(timezone.utc)

        doc = {
            "user_ids": user_ids,
            "date": payload.date,
            "time": payload.time,
            "timezone": payload.timezone,
            "utc_timestamp": utc_dt,
            "city_name": payload.city_name,
            "updated_at": datetime.now(timezone.utc)
        }
        
        await self.next_meets_collection.update_one(
            {"user_ids": user_ids},
            {"$set": doc},
            upsert=True
        )
        
        full_doc = await self.next_meets_collection.find_one({"user_ids": user_ids})
        if full_doc and "_id" in full_doc:
            full_doc["id"] = str(full_doc["_id"])
            full_doc["_id"] = str(full_doc["_id"])
            full_doc["utc_timestamp"] = full_doc["utc_timestamp"].isoformat()
        return full_doc

    async def update_next_meet(self, user_id: str, payload: NextMeetUpdate) -> Dict[str, Any]:
        partner_id = await self._get_partner_id(user_id)
        if not partner_id:
            raise ValueError("You must be aligned with a partner.")
            
        user_ids = sorted([user_id, partner_id])
        existing = await self.next_meets_collection.find_one({"user_ids": user_ids})
        if not existing:
            raise ValueError("Next meet not found.")

        updates = {k: v for k, v in payload.model_dump().items() if v is not None}
        
        if any(k in updates for k in ["date", "time", "timezone"]):
            import zoneinfo
            new_date = updates.get("date", existing["date"])
            new_time = updates.get("time", existing["time"])
            new_tz = updates.get("timezone", existing["timezone"])
            
            date_parts = re.split(r"[\.,]", new_date)
            time_match = re.match(r"(\d{1,2}):(\d{2})\s*(AM|PM)", new_time.upper())
            hour = int(time_match.group(1))
            minute = int(time_match.group(2))
            ampm = time_match.group(3)
            if ampm == "PM" and hour < 12: hour += 12
            elif ampm == "AM" and hour == 12: hour = 0
            
            local_dt = datetime(int(date_parts[2]), int(date_parts[0]), int(date_parts[1]), hour, minute, tzinfo=zoneinfo.ZoneInfo(new_tz))
            updates["utc_timestamp"] = local_dt.astimezone(timezone.utc)

        updates["updated_at"] = datetime.now(timezone.utc)
        
        await self.next_meets_collection.update_one({"user_ids": user_ids}, {"$set": updates})
        updated = await self.next_meets_collection.find_one({"user_ids": user_ids})
        updated["id"] = str(updated["_id"])
        updated["_id"] = str(updated["_id"])
        updated["utc_timestamp"] = updated["utc_timestamp"].isoformat()
        return updated

    async def delete_next_meet(self, user_id: str):
        partner_id = await self._get_partner_id(user_id)
        if not partner_id:
            raise ValueError("You must be aligned with a partner.")
        user_ids = sorted([user_id, partner_id])
        await self.next_meets_collection.delete_one({"user_ids": user_ids})

    async def get_next_meet_countdown(self, user_id: str, viewer_timezone: str = "UTC", user_doc: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        partner_id = user_doc.get("partner", {}).get("user_id") if user_doc and user_doc.get("is_aligned") and user_doc.get("partner") else None
        if partner_id is None and not user_doc:
            partner_id = await self._get_partner_id(user_id)
        if not partner_id:
            return None
            
        user_ids = sorted([user_id, partner_id])
        meet = await self.next_meets_collection.find_one({"user_ids": user_ids})
        if not meet:
            return None
            
        import zoneinfo
        try:
            tz = zoneinfo.ZoneInfo(viewer_timezone)
        except Exception:
            tz = zoneinfo.ZoneInfo("UTC")

        utc_meet_dt = meet["utc_timestamp"]
        if utc_meet_dt.tzinfo is None:
            utc_meet_dt = utc_meet_dt.replace(tzinfo=timezone.utc)
            
        local_meet_dt = utc_meet_dt.astimezone(tz)
        now_utc = datetime.now(timezone.utc)
        
        diff = utc_meet_dt - now_utc
        if diff.total_seconds() < 0:
            countdown = {"days": 0, "hours": 0, "minutes": 0, "seconds": 0}
        else:
            days = diff.days
            hours, remainder = divmod(diff.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            countdown = {"days": days, "hours": hours, "minutes": minutes, "seconds": seconds}
            
        return {
            "date": local_meet_dt.strftime("%m.%d.%Y"),
            "time": local_meet_dt.strftime("%I:%M %p"),
            "time_name": get_time_name(local_meet_dt.hour),
            "city_name": meet["city_name"],
            "countdown": countdown
        }

us_service = UsService()
