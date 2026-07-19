from typing import Dict, Any, List, Optional
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.db import get_client, get_db

from bson import ObjectId
from datetime import datetime, timezone

from app.core.config import settings
from app.schemas.energy import EnergyCreate, EnergyUpdate, EnergyPatchShare
from app.services.notification import notification_service
from app.schemas.notification import NotificationCreate, NotificationType, PresenceCreate
from app.core.websocket import ws_manager

class EnergyService:
    def __init__(self) -> None:
        self.client = get_client()
        self.db = get_db()
        self.energy_logs = self.db["energy_logs"]
        self.users = self.db["users"]

    async def create_energy_log(self, user_id: str, payload: EnergyCreate) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Check if the user already has a log for today — upsert instead of duplicating
        existing = await self.energy_logs.find_one({
            "user_id": user_id,
            "created_at": {"$gte": start_of_day}
        }, sort=[("created_at", -1)])
        
        if existing:
            # Update the existing log
            updates = payload.model_dump()
            updates["updated_at"] = now
            await self.energy_logs.update_one(
                {"_id": existing["_id"]},
                {"$set": updates}
            )
            new_doc = {**existing, **updates}
            new_doc["id"] = str(existing["_id"])
            if "_id" in new_doc:
                del new_doc["_id"]
        else:
            # Create a brand new log
            new_doc = payload.model_dump()
            new_doc["user_id"] = user_id
            new_doc["created_at"] = now
            new_doc["updated_at"] = now
            result = await self.energy_logs.insert_one(new_doc)
            new_doc["id"] = str(result.inserted_id)
        
        # Send Notification and WebSocket
        user = await self.users.find_one({"_id": ObjectId(user_id)})
        if user and user.get("partner") and user["partner"].get("user_id"):
            partner_id = user["partner"]["user_id"]
            user_name = user.get("name", "Your partner")
            
            # Websocket broadcast is sent always to trigger UI sync
            await ws_manager.broadcast_to_user(
                partner_id, 
                {"type": "ENERGY_UPDATED"}
            )
            
            # Push notification and presence logged if shared
            if payload.share_with_partner:
                try:
                    await notification_service.schedule_notification(
                        sender_id=user_id,
                        payload=NotificationCreate(
                            recipient_id=partner_id,
                            title="State Updated",
                            message=f"{user_name} just updated their daily energy & sleep.",
                            type=NotificationType.SYSTEM,
                            scheduled_for=datetime.now(timezone.utc),
                            timezone="UTC"
                        )
                    )
                except Exception as e:
                    print(f"Failed to send energy notification: {e}")
                    
                # Log Presence
                try:
                    await notification_service.log_presence(
                        user_id,
                        PresenceCreate(timezone="UTC")
                    )
                except Exception as e:
                    print(f"Failed to log energy presence: {e}")
                    
        return new_doc

    async def get_energy_logs(self, user_id: str) -> List[Dict[str, Any]]:
        cursor = self.energy_logs.find({"user_id": user_id}).sort("created_at", -1)
        docs = await cursor.to_list(length=None)
        results = []
        for d in docs:
            d["id"] = str(d["_id"])
            del d["_id"]
            results.append(d)
        return results

    async def get_energy_log(self, log_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        doc = await self.energy_logs.find_one({"_id": ObjectId(log_id), "user_id": user_id})
        if doc:
            doc["id"] = str(doc["_id"])
            del doc["_id"]
            return doc
        return None

    async def update_energy_log(self, log_id: str, user_id: str, payload: EnergyUpdate) -> Optional[Dict[str, Any]]:
        updates = {k: v for k, v in payload.model_dump().items() if v is not None}
        if not updates:
            return await self.get_energy_log(log_id, user_id)
            
        updates["updated_at"] = datetime.now(timezone.utc)
        
        result = await self.energy_logs.find_one_and_update(
            {"_id": ObjectId(log_id), "user_id": user_id},
            {"$set": updates},
            return_document=True
        )
        if result:
            result["id"] = str(result["_id"])
            del result["_id"]
            
            # Send Notification and WebSocket
            user = await self.users.find_one({"_id": ObjectId(user_id)})
            if user and user.get("partner") and user["partner"].get("user_id"):
                partner_id = user["partner"]["user_id"]
                user_name = user.get("name", "Your partner")
                
                # Websocket broadcast is sent always to trigger UI sync
                await ws_manager.broadcast_to_user(
                    partner_id, 
                    {"type": "ENERGY_UPDATED"}
                )
                
                # Push notification if shared in final state
                if result.get("share_with_partner"):
                    try:
                        await notification_service.schedule_notification(
                            sender_id=user_id,
                            payload=NotificationCreate(
                                recipient_id=partner_id,
                                title="State Updated",
                                message=f"{user_name} updated their daily energy & sleep.",
                                type=NotificationType.STATE_UPDATE,
                                scheduled_for=datetime.now(timezone.utc),
                                timezone="UTC"
                            )
                        )
                    except Exception as e:
                        print(f"Failed to send energy notification: {e}")
                        
            return result
        return None

    async def delete_energy_log(self, log_id: str, user_id: str) -> bool:
        result = await self.energy_logs.delete_one({"_id": ObjectId(log_id), "user_id": user_id})
        return result.deleted_count > 0

    async def patch_share_status(self, log_id: str, user_id: str, payload: EnergyPatchShare) -> bool:
        result = await self.energy_logs.update_one(
            {"_id": ObjectId(log_id), "user_id": user_id},
            {"$set": {
                "share_with_partner": payload.share_with_partner,
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        if result.matched_count > 0:
            user = await self.users.find_one({"_id": ObjectId(user_id)})
            if user and user.get("partner") and user["partner"].get("user_id"):
                partner_id = user["partner"]["user_id"]
                await ws_manager.broadcast_to_user(
                    partner_id, 
                    {"type": "ENERGY_UPDATED"}
                )
        return result.matched_count > 0

    async def get_partner_energy(self, user_id: str) -> List[Dict[str, Any]]:
        user = await self.users.find_one({"_id": ObjectId(user_id)})
        if not user or not user.get("partner"):
            return []
            
        partner_id = user["partner"]["user_id"]
        cursor = self.energy_logs.find({
            "user_id": partner_id
        }).sort("created_at", -1).limit(1)
        
        docs = await cursor.to_list(length=None)
        results = []
        if docs:
            d = docs[0]
            if d.get("share_with_partner", True):
                d["id"] = str(d["_id"])
                del d["_id"]
                results.append(d)
        return results

energy_service = EnergyService()
