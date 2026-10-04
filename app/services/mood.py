from typing import Dict, Any, List
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.db import get_client, get_db

from bson import ObjectId
from datetime import datetime, timezone

from app.core.config import settings
from app.schemas.mood import MoodListCreate, MoodListUpdate, MoodLogCreate, MoodLogUpdate
from app.services.notification import notification_service
from app.schemas.notification import NotificationCreate, NotificationType

class MoodService:
    def __init__(self) -> None:
        self.client = get_client()
        self.db = get_db()
        self.mood_list = self.db["mood_list"]
        self.mood_history = self.db["mood_history"]
        self.users = self.db["users"]

    async def init_indexes(self):
        try:
            await self.mood_list.create_index([("couple_id", 1), ("is_active", 1), ("order_index", 1)])
            await self.mood_list.create_index([("is_active", 1), ("order_index", 1)])
            await self.mood_list.create_index("couple_id")
            await self.mood_history.create_index([("couple_id", 1), ("created_at", -1)])
            await self.mood_history.create_index([("user_id", 1), ("created_at", -1)])
        except Exception as e:
            print(f"Error initializing mood indexes: {e}")

    async def seed_defaults(self):
        count = await self.mood_list.count_documents({"couple_id": {"$exists": False}})
        if count == 0:
            defaults = [
                {"name": "At peace", "symbol": "◯", "order_index": 1, "is_active": True},
                {"name": "Loving", "symbol": "◈", "order_index": 2, "is_active": True},
                {"name": "Flirtatious", "symbol": "✦", "order_index": 3, "is_active": True},
                {"name": "Passionate", "symbol": "◆", "order_index": 4, "is_active": True},
                {"name": "Needing you", "symbol": "✧", "order_index": 5, "is_active": True},
                {"name": "Thinking of you", "symbol": "·", "order_index": 6, "is_active": True}
            ]
            await self.mood_list.insert_many(defaults)

    # --- Scoping & Helper Functions ---

    async def _get_couple_id(self, user_id: str, user_doc: Optional[Dict[str, Any]] = None) -> str:
        if user_doc:
            user = user_doc
        else:
            user = await self.users.find_one({"_id": ObjectId(user_id)}, {"partner.user_id": 1, "is_aligned": 1})
        if not user:
            return user_id
        if user.get("is_aligned") and user.get("partner"):
            partner_id = user["partner"]["user_id"]
            return "_".join(sorted([user_id, partner_id]))
        return user_id

    async def _ensure_custom_mood_list(self, couple_id: str) -> None:
        count = await self.mood_list.count_documents({"couple_id": couple_id})
        if count > 0:
            return
            
        cursor = self.mood_list.find({"couple_id": {"$exists": False}, "is_active": True}).sort("order_index", 1)
        defaults = await cursor.to_list(length=None)
        
        if not defaults:
            defaults = [
                {"name": "At peace", "symbol": "◯", "order_index": 1, "is_active": True},
                {"name": "Loving", "symbol": "◈", "order_index": 2, "is_active": True},
                {"name": "Flirtatious", "symbol": "✦", "order_index": 3, "is_active": True},
                {"name": "Passionate", "symbol": "◆", "order_index": 4, "is_active": True},
                {"name": "Needing you", "symbol": "✧", "order_index": 5, "is_active": True},
                {"name": "Thinking of you", "symbol": "·", "order_index": 6, "is_active": True}
            ]
            
        cloned_moods = []
        for d in defaults:
            cloned = {
                "name": d["name"],
                "symbol": d["symbol"],
                "order_index": d["order_index"],
                "is_active": d["is_active"],
                "couple_id": couple_id,
                "original_default_id": str(d["_id"]) if "_id" in d else None
            }
            cloned_moods.append(cloned)
            
        if cloned_moods:
            await self.mood_list.insert_many(cloned_moods)

    async def _resolve_mood_id(self, couple_id: str, mood_id: str) -> ObjectId:
        try:
            obj_id = ObjectId(mood_id)
        except Exception:
            raise ValueError("Invalid mood ID format")
            
        # 1. Check if the mood is in their custom list
        doc = await self.mood_list.find_one({"_id": obj_id, "couple_id": couple_id})
        if doc:
            return obj_id
            
        # 2. Check if the mood is a clone of a default mood
        doc = await self.mood_list.find_one({"original_default_id": mood_id, "couple_id": couple_id})
        if doc:
            return doc["_id"]
            
        # 3. Check if it's a global default mood (and custom list hasn't been cloned yet)
        global_doc = await self.mood_list.find_one({"_id": obj_id, "couple_id": {"$exists": False}})
        if global_doc:
            await self._ensure_custom_mood_list(couple_id)
            doc = await self.mood_list.find_one({"original_default_id": mood_id, "couple_id": couple_id})
            if doc:
                return doc["_id"]
                
        raise ValueError("Mood option not found")

    # --- Mood List CRUD ---
    
    async def get_mood_list(self, user_id: str, user_doc: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        couple_id = await self._get_couple_id(user_id, user_doc=user_doc)
        cursor = self.mood_list.find({"couple_id": couple_id, "is_active": True}).sort("order_index", 1)
        docs = await cursor.to_list(length=None)
        if not docs:
            cursor = self.mood_list.find({"couple_id": {"$exists": False}, "is_active": True}).sort("order_index", 1)
            docs = await cursor.to_list(length=None)
            
        results = []
        for d in docs:
            d["id"] = str(d["_id"])
            del d["_id"]
            results.append(d)
        return results

    async def create_mood_option(self, user_id: str, payload: MoodListCreate) -> Dict[str, Any]:
        couple_id = await self._get_couple_id(user_id)
        await self._ensure_custom_mood_list(couple_id)
        
        new_doc = payload.model_dump()
        new_doc["couple_id"] = couple_id
        
        result = await self.mood_list.insert_one(new_doc)
        new_doc["id"] = str(result.inserted_id)
        return new_doc

    async def update_mood_option(self, user_id: str, mood_id: str, payload: MoodListUpdate) -> None:
        couple_id = await self._get_couple_id(user_id)
        resolved_id = await self._resolve_mood_id(couple_id, mood_id)
        
        updates = {k: v for k, v in payload.model_dump().items() if v is not None}
        if not updates:
            return
        await self.mood_list.update_one({"_id": resolved_id}, {"$set": updates})

    async def delete_mood_option(self, user_id: str, mood_id: str) -> None:
        couple_id = await self._get_couple_id(user_id)
        resolved_id = await self._resolve_mood_id(couple_id, mood_id)
        await self.mood_list.update_one({"_id": resolved_id}, {"$set": {"is_active": False}})


    # --- Mood Input CRUD ---

    async def log_mood(self, user_id: str, payload: MoodLogCreate) -> Dict[str, Any]:
        couple_id = await self._get_couple_id(user_id)
        resolved_id = await self._resolve_mood_id(couple_id, payload.mood_id)
        
        mood_option = await self.mood_list.find_one({"_id": resolved_id})
        if not mood_option:
            raise ValueError("Invalid mood option ID")
            
        new_doc = {
            "user_id": user_id,
            "mood_id": str(resolved_id),
            "mood_name": mood_option["name"],
            "mood_symbol": mood_option["symbol"],
            "created_at": datetime.now(timezone.utc)
        }
        result = await self.mood_history.insert_one(new_doc)
        new_doc["id"] = str(result.inserted_id)
        
        # Notify partner about mood change
        try:
            user = await self.users.find_one({"_id": ObjectId(user_id)})
            if user and user.get("is_aligned") and user.get("partner"):
                partner_id = user["partner"].get("user_id")
                user_name = user.get("name", "Your partner")
                mood_name = mood_option["name"]
                if partner_id:
                    await notification_service.schedule_notification(
                        sender_id=user_id,
                        payload=NotificationCreate(
                            recipient_id=partner_id,
                            title="Mood Update",
                            message=f"{user_name} is feeling {mood_name}.",
                            type=NotificationType.MOOD_CHANGE,
                            scheduled_for=datetime.now(timezone.utc),
                            timezone="UTC"
                        )
                    )
        except Exception as e:
            print(f"Failed to send mood change notification: {e}")
        
        return new_doc

    async def get_mood_history(self, user_id: str) -> List[Dict[str, Any]]:
        cursor = self.mood_history.find({"user_id": user_id}).sort("created_at", -1).limit(50)
        docs = await cursor.to_list(length=None)
        results = []
        for d in docs:
            d["id"] = str(d["_id"])
            del d["_id"]
            results.append(d)
        return results

    async def update_logged_mood(self, log_id: str, user_id: str, payload: MoodLogUpdate) -> None:
        couple_id = await self._get_couple_id(user_id)
        resolved_id = await self._resolve_mood_id(couple_id, payload.mood_id)
        
        mood_option = await self.mood_list.find_one({"_id": resolved_id})
        if not mood_option:
            raise ValueError("Invalid mood option ID")
            
        result = await self.mood_history.update_one(
            {"_id": ObjectId(log_id), "user_id": user_id},
            {"$set": {
                "mood_id": str(resolved_id),
                "mood_name": mood_option["name"],
                "mood_symbol": mood_option["symbol"],
                "created_at": datetime.now(timezone.utc)
            }}
        )
        if result.matched_count == 0:
            raise PermissionError("Mood log not found or not owned by user")

    async def delete_logged_mood(self, log_id: str, user_id: str) -> None:
        result = await self.mood_history.delete_one({"_id": ObjectId(log_id), "user_id": user_id})
        if result.deleted_count == 0:
            raise PermissionError("Mood log not found or not owned by user")


    # --- Current Mood Sync ---

    async def get_current_moods(self, user_id: str, user_doc: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        import asyncio
        user = user_doc if user_doc is not None else await self.users.find_one({"_id": ObjectId(user_id)})
        partner_id = None
        user_name = user.get("name", "Me") if user else "Me"
        partner_name = "Partner"
        
        if user and user.get("partner"):
            partner_id = user["partner"].get("user_id")
            partner_name = user["partner"].get("name", "Partner")
            
        states = []
        
        tasks = [self.mood_history.find_one({"user_id": user_id}, sort=[("created_at", -1)])]
        if partner_id:
            tasks.append(self.mood_history.find_one({"user_id": partner_id}, sort=[("created_at", -1)]))
            
        results = await asyncio.gather(*tasks)
        my_latest = results[0]
        pt_latest = results[1] if partner_id else None
        
        if my_latest:
            states.append({
                "mood_name": my_latest["mood_name"],
                "mood_symbol": my_latest["mood_symbol"],
                "updated_at": my_latest["created_at"],
                "is_partner": False,
                "author_name": user_name
            })
            
        if pt_latest:
            states.append({
                "mood_name": pt_latest["mood_name"],
                "mood_symbol": pt_latest["mood_symbol"],
                "updated_at": pt_latest["created_at"],
                "is_partner": True,
                "author_name": partner_name
            })
                
        return states

mood_service = MoodService()
