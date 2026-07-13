import re
import zoneinfo
from typing import Dict, Any, List, Optional, Tuple
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from datetime import datetime, timezone, timedelta

from app.core.config import settings
from app.schemas.dates import (
    DateCreate, DateUpdate, DateStatus, DateRespond, DateReviewCreate
)
from app.core.websocket import ws_manager
from app.services.notification import notification_service
from app.schemas.notification import NotificationCreate, NotificationType

def parse_date_time(date_str: str, time_str: str, tz_str: str) -> datetime:
    """Parses date and time strings into a UTC datetime object."""
    date_parts = re.split(r"[\.,-]", date_str)
    
    if len(date_parts) == 3:
        if len(date_parts[0]) == 4:
            year, month, day = int(date_parts[0]), int(date_parts[1]), int(date_parts[2])
        else:
            month, day, year = int(date_parts[0]), int(date_parts[1]), int(date_parts[2])
    else:
        raise ValueError("Invalid date format. Expected YYYY-MM-DD or MM.DD.YYYY")
        
    time_match = re.match(r"(\d{1,2}):(\d{2})\s*(AM|PM|am|pm)", time_str)
    if not time_match:
        raise ValueError("Invalid time format. Expected e.g. 09:00 PM")
        
    hour = int(time_match.group(1))
    minute = int(time_match.group(2))
    ampm = time_match.group(3).upper()
    if ampm == "PM" and hour < 12: hour += 12
    elif ampm == "AM" and hour == 12: hour = 0
        
    local_dt = datetime(year, month, day, hour, minute, tzinfo=zoneinfo.ZoneInfo(tz_str))
    return local_dt.astimezone(timezone.utc)

class DateService:
    def __init__(self) -> None:
        self.client = AsyncIOMotorClient(settings.MONGO_URL)
        self.db = self.client[settings.MONGO_DB_NAME]
        self.dates_collection = self.db["dates"]
        self.users = self.db["users"]

    async def init_indexes(self):
        await self.dates_collection.create_index([("creator_id", 1), ("partner_id", 1)])
        await self.dates_collection.create_index("utc_timestamp")
        await self.dates_collection.create_index("status")

    async def _get_partner_id(self, user_id: str) -> Optional[str]:
        user = await self.users.find_one({"_id": ObjectId(user_id)})
        if user and user.get("is_aligned") and user.get("partner"):
            return user["partner"]["user_id"]
        return None

    async def create_date(self, user_id: str, payload: DateCreate) -> Dict[str, Any]:
        partner_id = await self._get_partner_id(user_id)
        if not partner_id:
            raise ValueError("You must be aligned with a partner to create dates.")

        utc_ts = parse_date_time(payload.date, payload.time, payload.timezone)
        
        new_doc = payload.model_dump()
        new_doc["creator_id"] = user_id
        new_doc["partner_id"] = partner_id
        new_doc["proposed_by"] = user_id
        new_doc["status"] = DateStatus.PROPOSED
        new_doc["utc_timestamp"] = utc_ts
        new_doc["created_at"] = datetime.now(timezone.utc)
        new_doc["updated_at"] = datetime.now(timezone.utc)
        new_doc["reviews"] = []
        new_doc["notification_fired"] = False

        result = await self.dates_collection.insert_one(new_doc)
        new_doc["id"] = str(result.inserted_id)
        
        try:
            await ws_manager.broadcast_to_user(partner_id, {"type": "DATE_UPDATED"})
            await notification_service.schedule_notification(
                sender_id=user_id,
                payload=NotificationCreate(
                    recipient_id=partner_id,
                    title="New Date Proposal!",
                    message="Your partner proposed a new date.",
                    type=NotificationType.SYSTEM
                )
            )
        except Exception as e:
            print(f"Failed to notify partner on create_date: {e}")

        return await self._map_date(new_doc, payload.timezone)
    async def get_dates(self, user_id: str, status: Optional[str] = None, search: Optional[str] = None, sort: Optional[str] = None, page: int = 1, size: int = 10, target_timezone: str = "UTC") -> Tuple[List[Dict[str, Any]], int]:
        query = {
            "$or": [{"creator_id": user_id}, {"partner_id": user_id}],
            "deleted_by": {"$ne": user_id}
        }
        
        if status:
            if status.lower() == "reviewed":
                query["reviews.1"] = {"$exists": True}
            elif status.lower() == "pending":
                query["status"] = "Proposed"
                query["proposed_by"] = user_id
            elif status.lower() == "invited":
                query["status"] = "Proposed"
                query["proposed_by"] = {"$ne": user_id}
            else:
                query["status"] = {"$regex": f"^{status}$", "$options": "i"}

        if search:
            search_regex = {"$regex": search, "$options": "i"}
            query["$and"] = [{"$or": [{"creator_id": user_id}, {"partner_id": user_id}]}]
            query["$or"] = [
                {"where": search_regex},
                {"mood": search_regex},
                {"vibe": search_regex},
                {"date": search_regex},
                {"time": search_regex},
                {"city_name": search_regex},
                {"title": search_regex}
            ]
            
        sort_criteria = [("utc_timestamp", 1)]
        if sort == "Upcoming First":
            if "status" not in query:
                query["status"] = {"$nin": ["Completed", "Rejected", "Cancelled"]}
        elif sort == "Latest First":
            sort_criteria = [("utc_timestamp", -1)]
        elif sort == "Recently Created":
            sort_criteria = [("_id", -1)]
            
        skip = (page - 1) * size
        cursor = self.dates_collection.find(query).sort(sort_criteria).skip(skip).limit(size)
        total = await self.dates_collection.count_documents(query)
        
        dates = [await self._map_date(doc, target_timezone) for doc in await cursor.to_list(length=size)]
        return dates, total

    async def get_date_by_id(self, date_id: str, user_id: str, user_timezone: str = "UTC") -> Optional[Dict[str, Any]]:
        doc = await self.dates_collection.find_one({
            "_id": ObjectId(date_id),
            "$or": [{"creator_id": user_id}, {"partner_id": user_id}]
        })
        if doc:
            return await self._map_date(doc, user_timezone)
        return None

    async def update_date(self, date_id: str, user_id: str, payload: DateUpdate) -> Optional[Dict[str, Any]]:
        existing = await self.dates_collection.find_one({
            "_id": ObjectId(date_id), 
            "$or": [{"creator_id": user_id}, {"partner_id": user_id}]
        })
        if not existing:
            raise ValueError("Date not found or you are not a participant.")

        allowed_statuses = [DateStatus.PROPOSED, DateStatus.ACCEPTED]
        if existing["status"] not in allowed_statuses:
            raise ValueError(f"Cannot update date in '{existing['status']}' status.")

        updates = {k: v for k, v in payload.model_dump().items() if v is not None}
        if not updates:
            return await self._map_date(existing, existing["timezone"])

        if any(k in updates for k in ["date", "time", "timezone"]):
            new_date = updates.get("date", existing["date"])
            new_time = updates.get("time", existing["time"])
            new_tz = updates.get("timezone", existing["timezone"])
            updates["utc_timestamp"] = parse_date_time(new_date, new_time, new_tz)

        # Any modification triggers a new proposal from the updater
        updates["status"] = DateStatus.PROPOSED
        updates["proposed_by"] = user_id

        if existing["status"] == DateStatus.ACCEPTED:
            # In a real app, trigger push notification here
            print(f"DEBUG: Push notification sent to partner for rescheduled date {date_id}")

        updates["updated_at"] = datetime.now(timezone.utc)
        
        result = await self.dates_collection.find_one_and_update(
            {"_id": ObjectId(date_id)},
            {"$set": updates},
            return_document=True
        )
        
        target_id = existing["creator_id"] if user_id == existing["partner_id"] else existing["partner_id"]
        try:
            await ws_manager.broadcast_to_user(target_id, {"type": "DATE_UPDATED"})
            await notification_service.schedule_notification(
                sender_id=user_id,
                payload=NotificationCreate(
                    recipient_id=target_id,
                    title="Date Rescheduled!",
                    message="Your partner updated the date details.",
                    type=NotificationType.SYSTEM
                )
            )
        except Exception as e:
            print(f"Failed to notify partner on update_date: {e}")

        return await self._map_date(result, updates.get("timezone", existing["timezone"]))

    async def delete_date(self, date_id: str, user_id: str) -> bool:
        doc = await self.dates_collection.find_one({
            "_id": ObjectId(date_id),
            "$or": [{"creator_id": user_id}, {"partner_id": user_id}]
        })
        if not doc:
            raise ValueError("Date not found.")
            
        if doc["status"] not in [DateStatus.COMPLETED, DateStatus.CANCELLED, DateStatus.REJECTED]:
            raise ValueError("Only completed, cancelled, or rejected dates can be deleted.")
            
        # Check if partner already deleted it
        deleted_by = doc.get("deleted_by", [])
        if user_id not in deleted_by:
            deleted_by.append(user_id)
            
        partner_id = doc["creator_id"] if user_id == doc["partner_id"] else doc["partner_id"]
        
        # If both deleted, hard delete
        if partner_id in deleted_by:
            result = await self.dates_collection.delete_one({"_id": ObjectId(date_id)})
            return result.deleted_count > 0
        else:
            result = await self.dates_collection.update_one(
                {"_id": ObjectId(date_id)},
                {"$addToSet": {"deleted_by": user_id}}
            )
            return result.modified_count > 0

    async def respond_to_date(self, date_id: str, user_id: str, response: DateRespond) -> Dict[str, Any]:
        doc = await self.dates_collection.find_one({
            "_id": ObjectId(date_id),
            "$or": [{"creator_id": user_id}, {"partner_id": user_id}]
        })
        if not doc:
            raise ValueError("Date not found.")

        if doc["proposed_by"] == user_id:
            raise ValueError("You cannot accept or reject a date that you proposed.")

        if doc["status"] not in [DateStatus.PROPOSED, DateStatus.CANCEL_REQUESTED]:
            raise ValueError("Date is not currently proposed or cancel-requested.")

        if response.action == "accept":
            new_status = DateStatus.ACCEPTED if doc["status"] == DateStatus.PROPOSED else DateStatus.CANCELLED
            updates = {"status": new_status}
            
        elif response.action == "reject":
            new_status = DateStatus.REJECTED if doc["status"] == DateStatus.PROPOSED else DateStatus.ACCEPTED
            updates = {"status": new_status}
            
        else:
            raise ValueError("Invalid action. Use 'accept' or 'reject'.")

        updates["updated_at"] = datetime.now(timezone.utc)
        
        result = await self.dates_collection.find_one_and_update(
            {"_id": ObjectId(date_id)},
            {"$set": updates},
            return_document=True
        )
        
        target_id = doc["creator_id"] if user_id == doc["partner_id"] else doc["partner_id"]
        try:
            await ws_manager.broadcast_to_user(target_id, {"type": "DATE_UPDATED"})
            await notification_service.schedule_notification(
                sender_id=user_id,
                payload=NotificationCreate(
                    recipient_id=target_id,
                    title="Date Response!",
                    message=f"Your partner {response.action}ed the date proposal.",
                    type=NotificationType.SYSTEM
                )
            )
        except Exception as e:
            print(f"Failed to notify partner on respond_to_date: {e}")

        return await self._map_date(result, updates.get("timezone", doc["timezone"]))

    async def complete_date(self, date_id: str, user_id: str) -> Dict[str, Any]:
        doc = await self.dates_collection.find_one({
            "_id": ObjectId(date_id),
            "$or": [{"creator_id": user_id}, {"partner_id": user_id}]
        })
        if not doc:
            raise ValueError("Date not found.")

        if doc["status"] == DateStatus.COMPLETED:
            return await self._map_date(doc, doc["timezone"])

        if doc["status"] != DateStatus.ACCEPTED:
            raise ValueError("Only accepted dates can be marked completed.")

        now = datetime.now(timezone.utc)
        completed_by = doc.get("completed_by", [])
        
        if user_id not in completed_by:
            completed_by.append(user_id)
            
        partner_id = doc["creator_id"] if user_id == doc["partner_id"] else doc["partner_id"]
        
        updates = {"completed_by": completed_by, "updated_at": now}
        
        if partner_id in completed_by:
            updates["status"] = DateStatus.COMPLETED
            
        result = await self.dates_collection.find_one_and_update(
            {"_id": ObjectId(date_id)},
            {"$set": updates},
            return_document=True
        )
        
        target_id = doc["creator_id"] if user_id == doc["partner_id"] else doc["partner_id"]
        try:
            await ws_manager.broadcast_to_user(target_id, {"type": "DATE_UPDATED"})
            
            if updates.get("status") == DateStatus.COMPLETED:
                await notification_service.schedule_notification(
                    sender_id=user_id,
                    payload=NotificationCreate(
                        recipient_id=target_id,
                        title="Date Completed!",
                        message="Your partner also marked the date as completed.",
                        type=NotificationType.SYSTEM
                    )
                )
            else:
                await notification_service.schedule_notification(
                    sender_id=user_id,
                    payload=NotificationCreate(
                        recipient_id=target_id,
                        title="Date Completion",
                        message="Your partner marked the date as completed. Tap to confirm.",
                        type=NotificationType.SYSTEM
                    )
                )
        except Exception as e:
            print(f"Failed to notify partner on complete_date: {e}")
            
        return await self._map_date(result, doc["timezone"])

    async def add_review(self, date_id: str, user_id: str, review_payload: DateReviewCreate) -> Dict[str, Any]:
        doc = await self.dates_collection.find_one({
            "_id": ObjectId(date_id),
            "$or": [{"creator_id": user_id}, {"partner_id": user_id}]
        })
        if not doc:
            raise ValueError("Date not found.")

        if doc["status"] not in [DateStatus.COMPLETED, DateStatus.ACCEPTED]:
            raise ValueError("Reviews can only be added to accepted or completed dates.")

        for r in doc.get("reviews", []):
            if r["user_id"] == user_id:
                raise ValueError("You have already reviewed this date.")

        review = {
            "user_id": user_id,
            "rating": review_payload.rating,
            "text": review_payload.text,
            "photos": review_payload.photos,
            "created_at": datetime.now(timezone.utc)
        }

        result = await self.dates_collection.find_one_and_update(
            {"_id": ObjectId(date_id)},
            {"$push": {"reviews": review}, "$set": {"updated_at": datetime.now(timezone.utc)}},
            return_document=True
        )
        return await self._map_date(result, doc["timezone"])

    async def update_review(self, date_id: str, user_id: str, review_payload: DateReviewCreate) -> Dict[str, Any]:
        doc = await self.dates_collection.find_one({
            "_id": ObjectId(date_id),
            "$or": [{"creator_id": user_id}, {"partner_id": user_id}]
        })
        if not doc:
            raise ValueError("Date not found.")
            
        reviews = doc.get("reviews", [])
        found_idx = None
        for idx, r in enumerate(reviews):
            if r["user_id"] == user_id:
                found_idx = idx
                break
                
        if found_idx is None:
            raise ValueError("You have not reviewed this date yet.")
            
        reviews[found_idx]["rating"] = review_payload.rating
        reviews[found_idx]["text"] = review_payload.text
        reviews[found_idx]["photos"] = review_payload.photos
        reviews[found_idx]["updated_at"] = datetime.now(timezone.utc)
        
        result = await self.dates_collection.find_one_and_update(
            {"_id": ObjectId(date_id)},
            {"$set": {"reviews": reviews, "updated_at": datetime.now(timezone.utc)}},
            return_document=True
        )
        
        target_id = doc["creator_id"] if user_id == doc["partner_id"] else doc["partner_id"]
        try:
            await ws_manager.broadcast_to_user(target_id, {"type": "DATE_UPDATED"})
        except Exception:
            pass
            
        return await self._map_date(result, doc["timezone"])

    async def _get_names(self, user_id: str, partner_id: str) -> Dict[str, str]:
        names = {user_id: "User", partner_id: "Partner"}
        async for user in self.users.find({"_id": {"$in": [ObjectId(user_id), ObjectId(partner_id)]}}):
            names[str(user["_id"])] = user.get("name", "User")
        return names

    async def get_date_reviews(self, date_id: str, user_id: str, user_timezone: str = "UTC") -> List[Dict[str, Any]]:
        doc = await self.dates_collection.find_one({
            "_id": ObjectId(date_id),
            "$or": [{"creator_id": user_id}, {"partner_id": user_id}]
        })
        if not doc:
            raise ValueError("Date not found.")
        
        names = await self._get_names(doc["creator_id"], doc["partner_id"])
        results = []
        for r in doc.get("reviews", []):
            created_at = r.get("created_at")
            if created_at and isinstance(created_at, datetime):
                dt = created_at
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                try:
                    created_at = dt.astimezone(zoneinfo.ZoneInfo(user_timezone))
                except Exception:
                    created_at = dt
            results.append({
                "user_id": r["user_id"],
                "user_name": names.get(r["user_id"], "User"),
                "rating": r["rating"],
                "text": r["text"],
                "photos": r.get("photos", []),
                "created_at": created_at
            })
        return results

    async def ping_date(self, date_id: str, user_id: str, delay: str, note: str) -> None:
        doc = await self.dates_collection.find_one({
            "_id": ObjectId(date_id),
            "$or": [{"creator_id": user_id}, {"partner_id": user_id}]
        })
        if not doc:
            raise ValueError("Date not found.")
            
        target_id = doc["creator_id"] if user_id == doc["partner_id"] else doc["partner_id"]
        try:
            await ws_manager.broadcast_to_user(target_id, {"type": "DATE_UPDATED"})
            await notification_service.schedule_notification(
                sender_id=user_id,
                payload=NotificationCreate(
                    recipient_id=target_id,
                    title="Running Late!",
                    message=f"Your partner will be {delay} late. {note}",
                    type=NotificationType.SYSTEM
                )
            )
        except Exception as e:
            print(f"Failed to send ping notification: {e}")

    async def request_cancel(self, date_id: str, user_id: str, reason: str) -> Dict[str, Any]:
        doc = await self.dates_collection.find_one({
            "_id": ObjectId(date_id),
            "$or": [{"creator_id": user_id}, {"partner_id": user_id}]
        })
        if not doc:
            raise ValueError("Date not found.")

        if doc["status"] != DateStatus.ACCEPTED:
            raise ValueError("Only accepted dates can be cancelled via request.")

        result = await self.dates_collection.find_one_and_update(
            {"_id": ObjectId(date_id)},
            {"$set": {"status": DateStatus.CANCEL_REQUESTED, "updated_at": datetime.now(timezone.utc)}},
            return_document=True
        )
        
        target_id = doc["creator_id"] if user_id == doc["partner_id"] else doc["partner_id"]
        try:
            await ws_manager.broadcast_to_user(target_id, {"type": "DATE_UPDATED"})
            await notification_service.schedule_notification(
                sender_id=user_id,
                payload=NotificationCreate(
                    recipient_id=target_id,
                    title="Date Cancel Request",
                    message=f"Your partner requested to cancel the date: {reason}",
                    type=NotificationType.SYSTEM
                )
            )
        except Exception as e:
            print(f"Failed to notify partner on request_cancel: {e}")
            
        return await self._map_date(result, doc["timezone"])

    async def cancel_date(self, date_id: str, user_id: str) -> Dict[str, Any]:
        doc = await self.dates_collection.find_one({
            "_id": ObjectId(date_id),
            "$or": [{"creator_id": user_id}, {"partner_id": user_id}]
        })
        if not doc:
            raise ValueError("Date not found.")

        if doc["status"] != DateStatus.ACCEPTED:
            raise ValueError("Only accepted dates can be cancelled.")

        result = await self.dates_collection.find_one_and_update(
            {"_id": ObjectId(date_id)},
            {"$set": {"status": DateStatus.CANCELLED, "updated_at": datetime.now(timezone.utc)}},
            return_document=True
        )
        
        target_id = doc["creator_id"] if user_id == doc["partner_id"] else doc["partner_id"]
        try:
            await ws_manager.broadcast_to_user(target_id, {"type": "DATE_UPDATED"})
            await notification_service.schedule_notification(
                sender_id=user_id,
                payload=NotificationCreate(
                    recipient_id=target_id,
                    title="Date Cancelled",
                    message=f"Your partner has cancelled the date.",
                    type=NotificationType.SYSTEM
                )
            )
        except Exception as e:
            print(f"Failed to notify partner on cancel_date: {e}")
            
        return await self._map_date(result, doc["timezone"])

    async def _map_date(self, d: Dict[str, Any], user_timezone: str = "UTC") -> Dict[str, Any]:
        d["id"] = str(d["_id"])
        if "_id" in d: del d["_id"]
        
        try:
            tz = zoneinfo.ZoneInfo(user_timezone)
        except Exception:
            tz = zoneinfo.ZoneInfo("UTC")

        for field in ["utc_timestamp", "created_at", "updated_at"]:
            dt = d.get(field)
            if isinstance(dt, datetime):
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                d[field] = dt.astimezone(tz)

        if d.get("reviews"):
            names = await self._get_names(d["creator_id"], d["partner_id"])
            for r in d["reviews"]:
                r["user_name"] = names.get(r["user_id"], "User")
                if "created_at" in r and isinstance(r["created_at"], datetime):
                    dt = r["created_at"]
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    r["created_at"] = dt.astimezone(tz)
                if "updated_at" in r and isinstance(r["updated_at"], datetime):
                    dt = r["updated_at"]
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    r["updated_at"] = dt.astimezone(tz)

        now = datetime.now(timezone.utc)
        if d["status"] == DateStatus.ACCEPTED and not d.get("notification_fired"):
            time_reached = now >= d["utc_timestamp"].replace(tzinfo=timezone.utc) if d["utc_timestamp"].tzinfo is None else now >= d["utc_timestamp"]
            if time_reached:
                d["notification_fired"] = True
        
        return d

    async def request_delete_photo(self, date_id: str, user_id: str, photo_url: str) -> Dict[str, Any]:
        doc = await self.dates_collection.find_one({
            "_id": ObjectId(date_id),
            "$or": [{"creator_id": user_id}, {"partner_id": user_id}]
        })
        if not doc:
            raise ValueError("Date not found.")
            
        # Verify photo exists
        found_review = None
        for review in doc.get("reviews", []):
            if photo_url in review.get("photos", []):
                found_review = review
                break
                
        if not found_review:
            raise ValueError("Photo not found in this date.")
            
        if found_review["user_id"] == user_id:
            # User's own photo, delete it directly
            result = await self.dates_collection.find_one_and_update(
                {"_id": ObjectId(date_id), "reviews.user_id": user_id},
                {"$pull": {"reviews.$.photos": photo_url}},
                return_document=True
            )
            return await self._map_date(result, doc["timezone"])
            
        # Partner's photo, request deletion
        requests = doc.get("photo_delete_requests", [])
        if photo_url not in requests:
            requests.append(photo_url)
            
        result = await self.dates_collection.find_one_and_update(
            {"_id": ObjectId(date_id)},
            {"$set": {"photo_delete_requests": requests}},
            return_document=True
        )
        
        target_id = found_review["user_id"]
        try:
            await ws_manager.broadcast_to_user(target_id, {"type": "DATE_UPDATED"})
            await notification_service.schedule_notification(
                sender_id=user_id,
                payload=NotificationCreate(
                    recipient_id=target_id,
                    title="Photo Deletion Request",
                    message="Your partner wants to delete a photo from your memory.",
                    type=NotificationType.SYSTEM
                )
            )
        except Exception as e:
            print(f"Failed to notify partner on request_delete_photo: {e}")
            
        return await self._map_date(result, doc["timezone"])
        
    async def approve_delete_photo(self, date_id: str, user_id: str, photo_url: str) -> Dict[str, Any]:
        doc = await self.dates_collection.find_one({"_id": ObjectId(date_id)})
        if not doc:
            raise ValueError("Date not found.")
            
        if photo_url not in doc.get("photo_delete_requests", []):
            raise ValueError("No delete request found for this photo.")
            
        # Only the owner of the photo can approve it
        owner_id = None
        for review in doc.get("reviews", []):
            if photo_url in review.get("photos", []):
                owner_id = review["user_id"]
                break
                
        if owner_id != user_id:
            raise ValueError("You can only approve deletion of your own photos.")
            
        result = await self.dates_collection.find_one_and_update(
            {"_id": ObjectId(date_id), "reviews.user_id": user_id},
            {
                "$pull": {
                    "reviews.$.photos": photo_url,
                    "photo_delete_requests": photo_url
                }
            },
            return_document=True
        )
        
        target_id = doc["creator_id"] if user_id == doc["partner_id"] else doc["partner_id"]
        await ws_manager.broadcast_to_user(target_id, {"type": "DATE_UPDATED"})
        return await self._map_date(result, doc["timezone"])
        
    async def reject_delete_photo(self, date_id: str, user_id: str, photo_url: str) -> Dict[str, Any]:
        doc = await self.dates_collection.find_one({"_id": ObjectId(date_id)})
        if not doc:
            raise ValueError("Date not found.")
            
        if photo_url not in doc.get("photo_delete_requests", []):
            raise ValueError("No delete request found for this photo.")
            
        result = await self.dates_collection.find_one_and_update(
            {"_id": ObjectId(date_id)},
            {"$pull": {"photo_delete_requests": photo_url}},
            return_document=True
        )
        
        target_id = doc["creator_id"] if user_id == doc["partner_id"] else doc["partner_id"]
        await ws_manager.broadcast_to_user(target_id, {"type": "DATE_UPDATED"})
        return await self._map_date(result, doc["timezone"])

date_service = DateService()
