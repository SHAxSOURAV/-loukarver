import zoneinfo
from typing import Dict, Any, List, Optional, Tuple
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from datetime import datetime, timezone

from app.core.config import settings
from app.schemas.notification import (
    NotificationCreate, NotificationStatus, NotificationType
)

class NotificationService:
    def __init__(self) -> None:
        self.client = AsyncIOMotorClient(settings.MONGO_URL)
        self.db = self.client[settings.MONGO_DB_NAME]
        self.notifications_collection = self.db["notifications"]
        self.users = self.db["users"]

    async def init_indexes(self):
        await self.notifications_collection.create_index([("recipient_id", 1), ("status", 1)])
        await self.notifications_collection.create_index("scheduled_for")

    async def schedule_notification(self, sender_id: str, payload: NotificationCreate) -> Dict[str, Any]:
        new_doc = payload.model_dump()
        new_doc["sender_id"] = sender_id
        new_doc["status"] = NotificationStatus.SCHEDULED
        new_doc["created_at"] = datetime.now(timezone.utc)
        if not new_doc.get("scheduled_for"):
            new_doc["scheduled_for"] = new_doc["created_at"]
        
        result = await self.notifications_collection.insert_one(new_doc)
        new_doc["id"] = str(result.inserted_id)
        
        # Broadcast via WebSocket
        from app.core.websocket import ws_manager
        
        # Prepare a small payload for websocket
        ws_payload = {
            "type": "NEW_NOTIFICATION",
            "notification": {
                "id": new_doc["id"],
                "type": new_doc["type"],
                "title": new_doc["title"],
                "message": new_doc["message"]
            }
        }
        await ws_manager.broadcast_to_user(payload.recipient_id, ws_payload)
        
        # Send OneSignal Push Notification
        import asyncio
        asyncio.create_task(self._send_onesignal_push(payload.recipient_id, new_doc.get("title", ""), new_doc.get("message", "")))
        
        return await self._map_notification(new_doc, payload.timezone)

    async def _send_onesignal_push(self, user_id: str, title: str, message: str) -> None:
        if not settings.ONESIGNAL_APP_ID or not settings.ONESIGNAL_REST_API_KEY:
            return
            
        import httpx
        url = "https://onesignal.com/api/v1/notifications"
        headers = {
            "Authorization": f"Basic {settings.ONESIGNAL_REST_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "app_id": settings.ONESIGNAL_APP_ID,
            "include_aliases": {"external_id": [user_id]},
            "target_channel": "push",
            "headings": {"en": title},
            "contents": {"en": message},
        }
        
        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(url, json=payload, headers=headers, timeout=5.0)
                if res.status_code >= 400:
                    print(f"OneSignal Error: {res.text}")
        except Exception as e:
            print(f"Failed to send OneSignal push: {str(e)}")

    async def get_my_notifications(self, user_id: str, page: int = 1, size: int = 20, user_timezone: str = "UTC", types: Optional[List[str]] = None, is_hidden: Optional[bool] = None) -> Tuple[List[Dict[str, Any]], int, int]:
        query = {"recipient_id": user_id}
        if types:
            query["type"] = {"$in": types}
        if is_hidden is not None:
            query["is_hidden"] = is_hidden
        else:
            # By default, treat missing is_hidden as false or missing, unless explicitly querying for hidden
            # Actually if not specified, it's safer to just let it return anything (or we can enforce unhidden only if we want, but returning all is fine if they don't ask).
            pass
        
        # Auto-mark delivered if scheduled time has passed
        now = datetime.now(timezone.utc)
        
        # Update delivered status only for the filtered types (if any)
        delivered_query = {"recipient_id": user_id, "status": NotificationStatus.SCHEDULED, "scheduled_for": {"$lte": now}}
        if types:
            delivered_query["type"] = {"$in": types}
            
        await self.notifications_collection.update_many(
            delivered_query,
            {"$set": {"status": NotificationStatus.DELIVERED, "delivered_at": now}}
        )

        skip = (page - 1) * size
        cursor = self.notifications_collection.find(query).sort("scheduled_for", -1).skip(skip).limit(size)
        docs = await cursor.to_list(length=None)
        total = await self.notifications_collection.count_documents(query)
        
        unread_query = {"recipient_id": user_id, "status": {"$ne": NotificationStatus.SEEN}}
        if types:
            unread_query["type"] = {"$in": types}
        if is_hidden is not None:
            unread_query["is_hidden"] = is_hidden
        unread_count = await self.notifications_collection.count_documents(unread_query)

        return [await self._map_notification(d, user_timezone) for d in docs], total, unread_count

    async def mark_as_seen(self, notification_id: str, user_id: str) -> bool:
        now_utc = datetime.now(timezone.utc)
        result = await self.notifications_collection.update_one(
            {"_id": ObjectId(notification_id), "recipient_id": user_id},
            {"$set": {"status": NotificationStatus.SEEN, "seen_at": now_utc}}
        )
        if result.modified_count > 0:
            await self.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"last_active_at": now_utc}}
            )
            return True
        return False

    async def mark_as_unread(self, notification_id: str, user_id: str) -> bool:
        result = await self.notifications_collection.update_one(
            {"_id": ObjectId(notification_id), "recipient_id": user_id},
            {"$set": {"status": NotificationStatus.DELIVERED}, "$unset": {"seen_at": ""}}
        )
        return result.modified_count > 0

    async def delete_notification(self, notification_id: str, user_id: str) -> bool:
        result = await self.notifications_collection.delete_one(
            {"_id": ObjectId(notification_id), "recipient_id": user_id}
        )
        return result.deleted_count > 0

    async def hide_notification(self, notification_id: str, user_id: str) -> bool:
        result = await self.notifications_collection.update_one(
            {"_id": ObjectId(notification_id), "recipient_id": user_id},
            {"$set": {"is_hidden": True}}
        )
        return result.modified_count > 0

    async def unhide_notification(self, notification_id: str, user_id: str) -> bool:
        result = await self.notifications_collection.update_one(
            {"_id": ObjectId(notification_id), "recipient_id": user_id},
            {"$set": {"is_hidden": False}}
        )
        return result.modified_count > 0

    async def clear_all_notifications(self, user_id: str) -> int:
        result = await self.notifications_collection.delete_many(
            {"recipient_id": user_id}
        )
        return result.deleted_count

    async def _map_notification(self, d: Dict[str, Any], user_timezone: str) -> Dict[str, Any]:
        d["id"] = str(d["_id"])
        if "_id" in d: del d["_id"]
        
        d["is_hidden"] = d.get("is_hidden", False)

        try:
            tz = zoneinfo.ZoneInfo(user_timezone)
        except Exception:
            tz = zoneinfo.ZoneInfo("UTC")

        for field in ["scheduled_for", "created_at", "delivered_at", "seen_at"]:
            dt = d.get(field)
            if isinstance(dt, datetime):
                if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
                d[field] = dt.astimezone(tz)

        return d

    async def log_presence(self, user_id: str, payload: "PresenceCreate") -> Dict[str, Any]:
        from bson import ObjectId
        from app.schemas.notification import NotificationType, NotificationStatus
        
        now_utc = datetime.now(timezone.utc)
        
        # 1. Update user's last active and location
        update_data = {"last_active_at": now_utc}
        if payload.city: update_data["location_city"] = payload.city
        if payload.latitude: update_data["location_lat"] = payload.latitude
        if payload.longitude: update_data["location_lon"] = payload.longitude
        
        await self.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_data}
        )
        
        # 2. Get user to find partner
        user = await self.users.find_one({"_id": ObjectId(user_id)})
        if not user or not user.get("is_aligned"):
            return {"success": True, "message": "Presence logged. No partner aligned."}
            
        partner_id = user.get("partner", {}).get("user_id")
        if not partner_id:
            return {"success": True, "message": "Presence logged. Partner ID missing."}
            
        # 3. Calculate local hour
        try:
            tz = zoneinfo.ZoneInfo(payload.timezone)
        except Exception:
            tz = zoneinfo.ZoneInfo("UTC")
            
        local_time = now_utc.astimezone(tz)
        h = local_time.hour
        
        if h < 5: phrase = 'still awake'
        elif h < 12: phrase = 'just waking up'
        elif h < 17: phrase = 'in the middle of their day'
        elif h < 21: phrase = 'winding down'
        else: phrase = 'probably asleep'
        
        # 4. Check if we already sent this exact phrase today
        start_of_day = local_time.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
        
        existing = await self.notifications_collection.find_one({
            "sender_id": user_id,
            "recipient_id": partner_id,
            "type": NotificationType.PRESENCE.value,
            "message": phrase,
            "created_at": {"$gte": start_of_day}
        })
        
        if not existing:
            new_doc = {
                "title": "Presence",
                "message": phrase,
                "type": NotificationType.PRESENCE.value,
                "timezone": payload.timezone,
                "scheduled_for": now_utc,
                "sender_id": user_id,
                "recipient_id": partner_id,
                "status": NotificationStatus.DELIVERED.value, # Delivered immediately
                "created_at": now_utc,
                "delivered_at": now_utc
            }
            await self.notifications_collection.insert_one(new_doc)
            return {"success": True, "message": f"Presence logged and notification '{phrase}' sent to partner."}
            
        return {"success": True, "message": "Presence logged. Notification skipped (already sent today)."}

notification_service = NotificationService()
