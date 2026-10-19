import re
import zoneinfo
from datetime import datetime, date, timedelta, timezone
from typing import Dict, Any, List, Optional
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.db import get_client, get_db

from bson import ObjectId
from app.core.config import settings
from app.schemas.lifecycle import PeriodCreate, PeriodUpdate, PhaseNoteCreate, PhaseNoteUpdate

def parse_date(date_str: str) -> date:
    """Parses mm.dd.yyyy or mm.dd,yyyy to date object."""
    parts = re.split(r"[\.,]", date_str)
    return date(int(parts[2]), int(parts[0]), int(parts[1]))

import asyncio

class LifeCycleService:
    def __init__(self) -> None:
        self.client = get_client()
        self.db = get_db()
        self.periods = self.db["period_history"]
        self.notes = self.db["lifecycle_notes"]
        self.users = self.db["users"]

    async def init_indexes(self):
        try:
            await self.periods.create_index([("user_id", 1), ("start_date", -1)])
            await self.notes.create_index([("user_id", 1), ("date", 1)])
            await self.notes.create_index([("user_id", 1), ("cycle_day", 1)])
        except Exception as e:
            print(f"Error initializing lifecycle indexes: {e}")

    async def _get_owner_and_partner(self, user_id: str, user_doc: Optional[Dict[str, Any]] = None):
        """Returns the user ID of the woman in the relationship (the owner), partner ID, and owner user doc."""
        if user_doc:
            user = user_doc
        else:
            user = await self.users.find_one({"_id": ObjectId(user_id)}, {"gender": 1, "is_aligned": 1, "partner": 1, "name": 1, "cycle_data_shared": 1})
            
        partner_id = None
        if user and user.get("is_aligned") and user.get("partner"):
            partner_id = user["partner"].get("user_id")

        # Determine if user is Female
        user_gender = user.get("gender", "Male") if user else "Male"
        
        partner_gender = "Male"
        partner = None
        if partner_id:
            partner = await self.users.find_one({"_id": ObjectId(partner_id)}, {"gender": 1, "name": 1, "cycle_data_shared": 1})
            if partner:
                partner_gender = partner.get("gender", "Male")

        # If user is female, she owns her cycle dashboard view.
        if user_gender == "Female":
            return user_id, partner_id, user
            
        # If user is Male and partner is Female, partner owns the cycle.
        if partner_gender == "Female":
            return partner_id, user_id, partner
            
        # Default fallback if neither or both are male
        return user_id, partner_id, user

    @staticmethod
    def _get_relative_time(created_at: datetime) -> str:
        """Returns a human-readable relative time string like '2 hours ago'."""
        now = datetime.now(timezone.utc)
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        diff = now - created_at
        total_seconds = int(diff.total_seconds())

        if total_seconds < 0:
            return "just now"
        if total_seconds < 60:
            return "just now"
        
        minutes = total_seconds // 60
        if minutes < 60:
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        
        hours = minutes // 60
        if hours < 24:
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        
        days = hours // 24
        if days < 7:
            return f"{days} day{'s' if days != 1 else ''} ago"
        
        weeks = days // 7
        if weeks < 4:
            return f"{weeks} week{'s' if weeks != 1 else ''} ago"
        
        months = days // 30
        if months < 12:
            return f"{months} month{'s' if months != 1 else ''} ago"
        
        years = days // 365
        return f"{years} year{'s' if years != 1 else ''} ago"

    async def set_share_status(self, user_id: str, is_shared: bool) -> Dict[str, Any]:
        """Sets the sharing status of cycle data for the user."""
        from bson import ObjectId
        await self.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"cycle_data_shared": is_shared}}
        )
        return {"success": True}

    async def get_cycle_stats(self, user_id: str, user_doc: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        owner_id, partner_id, owner_user = await self._get_owner_and_partner(user_id, user_doc=user_doc)
        
        # Fetch the period owner's name and sharing status
        period_user_name = owner_user.get("name") if owner_user else None
        is_shared = owner_user.get("cycle_data_shared", True) if owner_user else True
        
        # If user is a partner and sharing is disabled, return empty data
        if user_id != owner_id and not is_shared:
            return {
                "period_user_name": period_user_name,
                "is_shared": False,
                "stats": None,
                "history": [],
                "current_note": None
            }
        
        # Concurrently fetch periods and current note
        history_task = self.periods.find({"user_id": owner_id}).sort("start_date", -1).to_list(length=10)
        note_task = self._get_current_note(owner_id, user_id, viewer_tz="UTC")
        history, current_note = await asyncio.gather(history_task, note_task)
        
        if not history:
            return {
                "period_user_name": period_user_name,
                "is_shared": is_shared,
                "stats": None,
                "history": [],
                "current_note": current_note
            }
            
        # 1. Parse and sort history chronologically descending (since start_date is mm.dd.yyyy string)
        parsed_history = []
        for h in history:
            curr_date = parse_date(h["start_date"])
            parsed_history.append({
                "id": str(h["_id"]),
                "user_id": h["user_id"],
                "start_date": h["start_date"],
                "dt": curr_date
            })
        parsed_history.sort(key=lambda x: x["dt"], reverse=True)

        cycle_lengths = []
        for i in range(len(parsed_history) - 1):
            diff = (parsed_history[i]["dt"] - parsed_history[i+1]["dt"]).days
            if 20 < diff < 45: # Filter out outliers
                cycle_lengths.append(diff)
                    
        avg_cycle = int(sum(cycle_lengths) / len(cycle_lengths)) if cycle_lengths else 28
        
        # 2. Calculate Current Phase
        last_period = parsed_history[0]["dt"]
        today = date.today()
        days_since_start = (today - last_period).days
        
        # If it's been more than one full cycle, predict based on a new start
        # This handles cases where user forgot to log for months
        if days_since_start >= avg_cycle:
             # Just show Luteal/Late or reset to 0 relative to prediction
             days_in_current_cycle = days_since_start % avg_cycle
        else:
             days_in_current_cycle = days_since_start

        phase = ""
        description = ""
        if days_in_current_cycle < 5:
            phase = "Menstrual"
            description = "The period phase. Focus on rest and iron-rich foods."
        elif days_in_current_cycle < 13:
            phase = "Follicular"
            description = "Estrogen is rising. High energy and creativity."
        elif days_in_current_cycle < 16:
            phase = "Ovulatory"
            description = "Highest fertility. Peak communication and social energy."
        else:
            phase = "Luteal"
            description = "PMS may occur. Prioritize self-care and calming activities."

        next_period = last_period + timedelta(days=avg_cycle)
        while next_period <= today:
            next_period += timedelta(days=avg_cycle)
            
        days_left = (next_period - today).days

        stats = {
            "current_phase": phase,
            "days_since_start": days_since_start,
            "cycle_length_used": avg_cycle,
            "next_period_date": next_period.strftime("%m.%d.%Y"),
            "days_until_next_period": days_left,
            "phase_description": description
        }
        
        return {
            "period_user_name": period_user_name,
            "is_shared": is_shared,
            "stats": stats,
            "history": [{"id": p["id"], "user_id": p["user_id"], "start_date": p["start_date"]} for p in parsed_history],
            "current_note": current_note
        }

    async def _notify_partner_cycle_update(self, user_id: str):
        try:
            owner_id, partner_id, owner_user = await self._get_owner_and_partner(user_id)
            if not partner_id:
                return
            
            is_shared = owner_user.get("cycle_data_shared", True) if owner_user else True
            if not is_shared:
                return
                
            owner_name = owner_user.get("name", "Your partner") if owner_user else "Your partner"
            now_utc = datetime.now(timezone.utc)
            
            # 1. Schedule notification (saves in DB, sends OneSignal push, sends WebSocket NEW_NOTIFICATION)
            from app.services.notification import notification_service
            from app.schemas.notification import NotificationCreate, NotificationType
            await notification_service.schedule_notification(
                sender_id=user_id,
                payload=NotificationCreate(
                    recipient_id=partner_id,
                    type=NotificationType.CYCLE_UPDATE,
                    title="Cycle Updated",
                    message=f"{owner_name} updated her cycle dates.",
                    scheduled_for=now_utc,
                    timezone="UTC",
                    metadata={"screen": "Home", "section": "cycle"}
                )
            )
            
            # 2. Real-time WebSocket broadcast to partner
            from app.core.websocket import ws_manager
            await ws_manager.broadcast_to_user(partner_id, {
                "type": "STATE_UPDATE",
                "message": f"{owner_name} updated her cycle dates.",
                "data": {
                    "type": "CYCLE_UPDATE",
                    "user_id": user_id
                }
            })
            await ws_manager.broadcast_to_user(partner_id, {
                "type": "CYCLE_UPDATED",
                "message": f"{owner_name} updated her cycle dates.",
                "data": {
                    "type": "CYCLE_UPDATE",
                    "user_id": user_id
                }
            })
        except Exception as e:
            print(f"Failed to notify partner of cycle update: {e}")

    async def add_period(self, user_id: str, payload: PeriodCreate) -> Dict[str, Any]:
        new_period = {
            "user_id": user_id,
            "start_date": payload.start_date,
            "created_at": datetime.now(timezone.utc)
        }
        # Avoid duplicates for same date
        await self.periods.delete_many({"user_id": user_id, "start_date": payload.start_date})
        result = await self.periods.insert_one(new_period)
        
        # Ensure _id is a string and added as 'id'
        new_period["id"] = str(result.inserted_id)
        new_period["_id"] = str(result.inserted_id)
        
        await self._notify_partner_cycle_update(user_id)
        return new_period

    async def update_period(self, user_id: str, period_id: str, payload: PeriodUpdate) -> Dict[str, Any]:
        result = await self.periods.update_one(
            {"_id": ObjectId(period_id), "user_id": user_id},
            {"$set": {"start_date": payload.start_date}}
        )
        if result.matched_count == 0:
            raise ValueError("Period record not found.")
        
        updated = await self.periods.find_one({"_id": ObjectId(period_id)})
        if updated:
            updated["id"] = str(updated["_id"])
            updated["_id"] = str(updated["_id"])
        
        await self._notify_partner_cycle_update(user_id)
        return updated

    async def delete_period(self, user_id: str, period_id: str):
        await self.periods.delete_one({"_id": ObjectId(period_id), "user_id": user_id})
        await self._notify_partner_cycle_update(user_id)

    # --- Phase Notes ---

    async def _get_current_note(self, owner_id: str, viewer_id: str, viewer_tz: str = "UTC") -> Optional[Dict[str, Any]]:
        """Gets the most recent note for today (based on viewer timezone)."""
        try:
            tz = zoneinfo.ZoneInfo(viewer_tz)
        except Exception:
            tz = zoneinfo.ZoneInfo("UTC")
        
        local_now = datetime.now(tz)
        today_str = local_now.strftime("%m.%d.%Y")
        
        note = await self.notes.find_one({"user_id": owner_id, "date": today_str})
        if note:
            created_at = note.get("created_at")
            created_ago = self._get_relative_time(created_at) if created_at else "unknown"
            return {
                "id": str(note["_id"]),
                "user_id": note["user_id"],
                "date": note["date"],
                "text": note["text"],
                "created_ago": created_ago,
                "created_at": created_at.isoformat() if created_at else None,
                "is_owner": note["user_id"] == viewer_id
            }
        return None

    async def add_note(self, user_id: str, payload: PhaseNoteCreate) -> Dict[str, Any]:
        """Adds or updates a text note. Date is auto-resolved from the user's timezone."""
        try:
            tz = zoneinfo.ZoneInfo(payload.timezone)
        except Exception:
            raise ValueError(f"Invalid timezone: {payload.timezone}")
        
        local_now = datetime.now(tz)
        auto_date = local_now.strftime("%m.%d.%Y")
        now_utc = datetime.now(timezone.utc)

        new_note = {
            "user_id": user_id,
            "date": auto_date,
            "text": payload.text,
            "timezone": payload.timezone,
            "created_at": now_utc
        }
        # Upsert for specific date
        await self.notes.update_one(
            {"user_id": user_id, "date": auto_date},
            {"$set": new_note},
            upsert=True
        )
        
        # Notify partner
        try:
            from app.services.notification import notification_service
            from app.schemas.notification import NotificationCreate, NotificationType
            user = await self.users.find_one({"_id": ObjectId(user_id)})
            if user and user.get("is_aligned") and user.get("partner"):
                partner_id = user["partner"].get("user_id")
                if partner_id:
                    user_name = user.get("name", "Your partner")
                    await notification_service.schedule_notification(
                        sender_id=user_id,
                        payload=NotificationCreate(
                            recipient_id=partner_id,
                            title="Cycle Note Update",
                            message=f"{user_name} added a note about her cycle: \"{payload.text[:30]}...\"",
                            type=NotificationType.CYCLE_UPDATE,
                            scheduled_for=now_utc,
                            timezone="UTC"
                        )
                    )
        except Exception as e:
            print(f"Failed to send note notification: {e}")

        # Update partner WebSocket if aligned to partner if sharing is enabled
        owner_id, partner_id = await self._get_owner_and_partner(user_id)
        if partner_id:
            owner_user = await self.users.find_one({"_id": ObjectId(owner_id)})
            is_shared = owner_user.get("cycle_data_shared", True) if owner_user else True
            if is_shared:
                from app.services.notification import notification_service
                from app.schemas.notification import NotificationCreate, NotificationType
                owner_name = owner_user.get("name", "Your partner") if owner_user else "Your partner"
                await notification_service.schedule_notification(
                    sender_id=user_id,
                    payload=NotificationCreate(
                        recipient_id=partner_id,
                        type=NotificationType.CYCLE_UPDATE,
                        title="Cycle Note Updated",
                        message=f"{owner_name} added a cycle note.",
                        scheduled_for=now_utc,
                        timezone=payload.timezone
                    )
                )

        doc = await self.notes.find_one({"user_id": user_id, "date": auto_date})
        created_at = doc.get("created_at")
        created_ago = self._get_relative_time(created_at) if created_at else "just now"
        return {
            "id": str(doc["_id"]),
            "user_id": doc["user_id"],
            "date": doc["date"],
            "text": doc["text"],
            "created_ago": created_ago,
            "is_owner": True
        }

    async def update_note(self, user_id: str, note_id: str, payload: PhaseNoteUpdate) -> Dict[str, Any]:
        result = await self.notes.update_one(
            {"_id": ObjectId(note_id), "user_id": user_id},
            {"$set": {"text": payload.text}}
        )
        if result.matched_count == 0:
            raise PermissionError("Note not found or you are not the owner.")
        return {"success": True}

    async def delete_note(self, user_id: str, note_id: str):
        result = await self.notes.delete_one({"_id": ObjectId(note_id), "user_id": user_id})
        if result.deleted_count == 0:
            raise PermissionError("Note not found or you are not the owner.")

lifecycle_service = LifeCycleService()
