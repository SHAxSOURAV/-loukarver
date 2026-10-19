import asyncio
from typing import Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.db import get_client, get_db

from bson import ObjectId
from datetime import datetime, timezone, timedelta

from app.core.config import settings
from app.core.websocket import ws_manager
from app.services.notification import notification_service
from app.schemas.notification import NotificationCreate, NotificationType

class InteractionService:
    def __init__(self) -> None:
        self.client = get_client()
        self.db = get_db()
        self.interactions = self.db["partner_interactions"]
        self.users = self.db["users"]

    async def init_indexes(self):
        try:
            await self.interactions.create_index("created_at", expireAfterSeconds=172800)
            await self.interactions.create_index([("sender_id", 1), ("recipient_id", 1), ("date", 1)])
            await self.interactions.create_index([("recipient_id", 1), ("date", 1)])
        except Exception as e:
            print(f"Error initializing interaction indexes: {e}")

    async def _get_couple_info(self, user_id: str, user_doc: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        user = user_doc if user_doc is not None else await self.users.find_one({"_id": ObjectId(user_id)})
        if not user or not user.get("is_aligned") or not user.get("partner"):
            return None
        return {
            "user_id": user_id,
            "user_name": user.get("name", "User"),
            "partner_id": user["partner"]["user_id"],
            "partner_name": user["partner"].get("name", "Partner")
        }

    def _get_today_str(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    async def increment_count(self, user_id: str, user_doc: Optional[Dict[str, Any]] = None) -> bool:
        info = await self._get_couple_info(user_id, user_doc=user_doc)
        if not info:
            return False

        today = self._get_today_str()
        
        await self.interactions.update_one(
            {
                "sender_id": user_id, 
                "recipient_id": info["partner_id"],
                "date": today
            },
            {
                "$inc": {"count": 1},
                "$set": {
                    "last_activity": datetime.now(timezone.utc),
                    "created_at": datetime.now(timezone.utc)
                }
            },
            upsert=True
        )

        try:
            await ws_manager.broadcast_to_user(info["partner_id"], {"type": "POKE_RECEIVED"})
            await notification_service.schedule_notification(
                sender_id=user_id,
                payload=NotificationCreate(
                    recipient_id=info["partner_id"],
                    title="Thinking of you",
                    message=f"{info['user_name']} sent you a silent ping.",
                    type=NotificationType.THINKING_OF_YOU,
                    scheduled_for=datetime.now(timezone.utc),
                    timezone="UTC",
                    metadata={
                        "screen": "Home",
                        "section": "moment",
                        "action": "silent_ping"
                    }
                )
            )
        except Exception as e:
            print(f"Failed to send poke notification: {e}")

        return True

    async def get_interaction_stats(self, user_id: str, user_doc: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        info = await self._get_couple_info(user_id, user_doc=user_doc)
        if not info:
            return None

        today = self._get_today_str()
        
        # Concurrently fetch received and sent pokes
        received_doc, sent_doc = await asyncio.gather(
            self.interactions.find_one({
                "sender_id": info["partner_id"],
                "recipient_id": user_id,
                "date": today
            }),
            self.interactions.find_one({
                "sender_id": user_id,
                "recipient_id": info["partner_id"],
                "date": today
            })
        )

        return {
            "partner_name": info["partner_name"],
            "received_count": received_doc["count"] if received_doc else 0,
            "received_last_activity": received_doc["last_activity"] if received_doc else None,
            "sent_count": sent_doc["count"] if sent_doc else 0,
            "sent_last_activity": sent_doc["last_activity"] if sent_doc else None,
        }

interaction_service = InteractionService()
