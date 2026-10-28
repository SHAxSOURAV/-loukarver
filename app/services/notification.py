import zoneinfo
from typing import Dict, Any, List, Optional, Tuple
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.db import get_client, get_db

from bson import ObjectId
from datetime import datetime, timezone

from app.core.config import settings
from app.schemas.notification import (
    NotificationCreate, NotificationStatus, NotificationType
)

import asyncio

class NotificationService:
    def __init__(self) -> None:
        self.client = get_client()
        self.db = get_db()
        self.notifications_collection = self.db["notifications"]
        self.users = self.db["users"]

    async def init_indexes(self):
        try:
            await self.notifications_collection.create_index([("recipient_id", 1), ("scheduled_for", -1)])
            await self.notifications_collection.create_index([("recipient_id", 1), ("status", 1), ("scheduled_for", 1)])
            await self.notifications_collection.create_index([("recipient_id", 1), ("status", 1)])
            await self.notifications_collection.create_index("scheduled_for")
        except Exception as e:
            print(f"Index initialization note in notification: {e}")

    async def create_notification(self, payload: NotificationCreate, sender_id: Optional[str] = None) -> Dict[str, Any]:
        """Creates and dispatches an instant notification with WebSocket and Push delivery."""
        return await self.schedule_notification(sender_id or payload.recipient_id, payload)

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
                "message": new_doc["message"],
                "metadata": new_doc.get("metadata") or {}
            }
        }
        await ws_manager.broadcast_to_user(payload.recipient_id, ws_payload)
        
        # Send OneSignal Push Notification
        import asyncio
        asyncio.create_task(self.send_onesignal_push(
            payload.recipient_id,
            new_doc.get("title", ""),
            new_doc.get("message", ""),
            custom_data=new_doc.get("metadata")
        ))
        
        return await self._map_notification(new_doc, payload.timezone)

    async def send_onesignal_push(self, user_id: str, title: str, message: str, custom_data: dict = None) -> None:
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
            "priority": 10,
            "ios_interruption_level": "time-sensitive",
            "ios_badgeType": "Increase",
            "ios_badgeCount": 1,
            "ios_sound": "default",
            "android_sound": "default",
            "android_visibility": 1,
            "android_accent_color": "FF4F8B",
        }
        if custom_data:
            payload["data"] = custom_data
        
        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(url, json=payload, headers=headers, timeout=5.0)
                if res.status_code >= 400:
                    print(f"OneSignal Error: {res.text}")
        except Exception as e:
            print(f"Failed to send OneSignal push: {str(e)}")

    def _recipient_filter(self, user_id: str) -> Dict[str, Any]:
        targets = [str(user_id)]
        if ObjectId.is_valid(user_id):
            targets.append(ObjectId(user_id))
        return {"$in": targets}

    async def get_my_notifications(self, user_id: str, page: int = 1, size: int = 20, user_timezone: str = "UTC", types: Optional[List[str]] = None, is_hidden: Optional[bool] = None) -> Tuple[List[Dict[str, Any]], int, int]:
        rf = self._recipient_filter(user_id)
        query = {"recipient_id": rf}
        if types:
            query["type"] = {"$in": types}
        if is_hidden is not None:
            query["is_hidden"] = is_hidden
        
        # Auto-mark delivered if scheduled time has passed
        now = datetime.now(timezone.utc)
        
        # Update delivered status only for the filtered types (if any)
        delivered_query = {"recipient_id": rf, "status": NotificationStatus.SCHEDULED, "scheduled_for": {"$lte": now}}
        if types:
            delivered_query["type"] = {"$in": types}
            
        # Fire background task to mark delivered notifications without blocking the response
        async def _do_update():
            try:
                await self.notifications_collection.update_many(
                    delivered_query,
                    {"$set": {"status": NotificationStatus.DELIVERED, "delivered_at": now}}
                )
            except Exception:
                pass

        asyncio.create_task(_do_update())

        skip = (page - 1) * size
        cursor = self.notifications_collection.find(query).sort("scheduled_for", -1).skip(skip).limit(size)
        
        unread_query = {"recipient_id": rf, "status": {"$ne": NotificationStatus.SEEN}}
        if types:
            unread_query["type"] = {"$in": types}
        if is_hidden is not None:
            unread_query["is_hidden"] = is_hidden
        else:
            unread_query["is_hidden"] = {"$ne": True}

        docs, total, unread_count = await asyncio.gather(
            cursor.to_list(length=size),
            self.notifications_collection.count_documents(query),
            self.notifications_collection.count_documents(unread_query)
        )

        return [self._map_notification_sync(d, user_timezone) for d in docs], total, unread_count

    async def mark_as_seen(self, notification_id: str, user_id: str) -> bool:
        now_utc = datetime.now(timezone.utc)
        rf = self._recipient_filter(user_id)
        result = await self.notifications_collection.update_one(
            {"_id": ObjectId(notification_id), "recipient_id": rf},
            {"$set": {"status": NotificationStatus.SEEN, "seen_at": now_utc}}
        )
        if result.matched_count > 0:
            await self.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"last_active_at": now_utc}}
            )
            return True
        return False

    async def mark_all_as_seen(self, user_id: str) -> int:
        now_utc = datetime.now(timezone.utc)
        rf = self._recipient_filter(user_id)
        result = await self.notifications_collection.update_many(
            {"recipient_id": rf, "status": {"$ne": NotificationStatus.SEEN}},
            {"$set": {"status": NotificationStatus.SEEN, "seen_at": now_utc}}
        )
        if result.modified_count > 0:
            await self.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"last_active_at": now_utc}}
            )
        return result.modified_count

    async def mark_as_unread(self, notification_id: str, user_id: str) -> bool:
        rf = self._recipient_filter(user_id)
        result = await self.notifications_collection.update_one(
            {"_id": ObjectId(notification_id), "recipient_id": rf},
            {"$set": {"status": NotificationStatus.DELIVERED}, "$unset": {"seen_at": ""}}
        )
        return result.modified_count > 0

    async def delete_notification(self, notification_id: str, user_id: str) -> bool:
        rf = self._recipient_filter(user_id)
        result = await self.notifications_collection.delete_one(
            {"_id": ObjectId(notification_id), "recipient_id": rf}
        )
        return result.deleted_count > 0

    async def hide_notification(self, notification_id: str, user_id: str) -> bool:
        rf = self._recipient_filter(user_id)
        result = await self.notifications_collection.update_one(
            {"_id": ObjectId(notification_id), "recipient_id": rf},
            {"$set": {"is_hidden": True}}
        )
        return result.modified_count > 0

    async def unhide_notification(self, notification_id: str, user_id: str) -> bool:
        rf = self._recipient_filter(user_id)
        result = await self.notifications_collection.update_one(
            {"_id": ObjectId(notification_id), "recipient_id": rf},
            {"$set": {"is_hidden": False}}
        )
        return result.modified_count > 0

    async def clear_all_notifications(self, user_id: str) -> int:
        rf = self._recipient_filter(user_id)
        result = await self.notifications_collection.delete_many(
            {"recipient_id": rf}
        )
        return result.deleted_count

    async def _map_notification(self, d: Dict[str, Any], user_timezone: str) -> Dict[str, Any]:
        return self._map_notification_sync(d, user_timezone)

    def _map_notification_sync(self, d: Dict[str, Any], user_timezone: str) -> Dict[str, Any]:
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
        if payload.timezone: update_data["timezone"] = payload.timezone
        
        await self.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_data}
        )
        
        return {"success": True, "message": "Presence logged."}

notification_service = NotificationService()
