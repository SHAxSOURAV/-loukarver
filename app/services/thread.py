import asyncio
import os
import uuid
import zoneinfo
import boto3
from typing import Dict, Any, List, Optional, Tuple
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.db import get_client, get_db

from bson import ObjectId
from datetime import datetime, timezone, timedelta
from fastapi import UploadFile

from app.core.config import settings
from app.services.s3_utils import s3_service
from app.schemas.thread import (
    ThreadCategory, PromptType, PromptQuestionCreate,
    LetterCreate, PhotoCreate, PromptAskCreate, AppreciationCreate, CheckInThreadCreate
)

DEFAULT_ROMANTIC_QUESTIONS = [
    {"category": "Emotional", "rating": "●●○○○", "text": "What's one thing I did recently that made you feel deeply loved?", "type": PromptType.ROMANTIC},
    {"category": "Emotional", "rating": "●○○○○", "text": "Describe the moment you knew this was something real.", "type": PromptType.ROMANTIC},
    {"category": "Desire", "rating": "●●●○○", "text": "If we had one uninterrupted hour right now, how would you want to spend it?", "type": PromptType.ROMANTIC},
    {"category": "Growth", "rating": "●○○○○", "text": "What part of our relationship are you most proud of?", "type": PromptType.ROMANTIC},
    {"category": "Depth", "rating": "●●○○○", "text": "Tell me something you've been holding in — good or complicated.", "type": PromptType.ROMANTIC},
    {"category": "Memory", "rating": "●●○○○", "text": "If you could relive one moment with me, which would it be?", "type": PromptType.ROMANTIC},
    {"category": "Growth", "rating": "●●○○○", "text": "What's your love language and how can I speak it better?", "type": PromptType.ROMANTIC},
    {"category": "Future", "rating": "●●○○○", "text": "What are you looking forward to most in our future?", "type": PromptType.ROMANTIC},
    {"category": "Emotional", "rating": "●○○○○", "text": "What do I do that makes you feel most seen?", "type": PromptType.ROMANTIC},
    {"category": "Adventure", "rating": "●●○○○", "text": "What's a dream date you've never told me about?", "type": PromptType.ROMANTIC},
]

DEFAULT_DESIRED_QUESTIONS = [
    {"category": "Intense", "rating": "●●●●●", "text": "Tell me exactly what you'd do if I was there right now.", "type": PromptType.DESIRED},
    {"category": "Daring", "rating": "●●●●●", "text": "What's the boldest thing you want to try together?", "type": PromptType.DESIRED},
    {"category": "Memory", "rating": "●●●●○", "text": "Describe your favorite memory of us in full detail.", "type": PromptType.DESIRED},
    {"category": "Vulnerable", "rating": "●●●●○", "text": "What's something you've been too shy to ask for?", "type": PromptType.DESIRED},
    {"category": "Intense", "rating": "●●●●●", "text": "If you could have me any way you wanted tonight, what would you choose?", "type": PromptType.DESIRED},
    {"category": "Desire", "rating": "●●●●○", "text": "What do you think about when you close your eyes and think of me?", "type": PromptType.DESIRED},
    {"category": "Intimate", "rating": "●●●●○", "text": "What's one thing about your body you want me to pay more attention to?", "type": PromptType.DESIRED},
    {"category": "Daring", "rating": "●●●●●", "text": "Tell me a fantasy you've never spoken out loud.", "type": PromptType.DESIRED},
]

class ThreadService:
    def __init__(self) -> None:
        self.client = get_client()
        self.db = get_db()
        self.messages_collection = self.db["thread_messages"]
        self.prompts_collection = self.db["thread_prompts"]
        self.users = self.db["users"]

    async def init_indexes(self):
        try:
            await self.messages_collection.create_index([("creator_id", 1), ("partner_id", 1)])
            await self.messages_collection.create_index([("creator_id", 1), ("created_at", -1)])
            await self.messages_collection.create_index([("partner_id", 1), ("is_seen", 1)])
            await self.messages_collection.create_index([("creator_id", 1), ("category", 1)])
            await self.messages_collection.create_index("created_at")
            await self.prompts_collection.create_index("type")
        except Exception as e:
            print(f"Error initializing thread indexes: {e}")

    async def _get_partner_id(self, user_id: str) -> Optional[str]:
        user = await self.users.find_one({"_id": ObjectId(user_id)})
        if user and user.get("is_aligned") and user.get("partner"):
            return user["partner"]["user_id"]
        return None

    async def _get_names(self, user_id: str, partner_id: str) -> Dict[str, str]:
        names = {user_id: "User", partner_id: "Partner"}
        async for user in self.users.find({"_id": {"$in": [ObjectId(user_id), ObjectId(partner_id)]}}):
            names[str(user["_id"])] = user.get("name", "User")
        return names

    async def _notify_partner(self, user_id: str, partner_id: str, message: Dict[str, Any], title: str, body: str):
        # 1. Websocket
        try:
            from app.core.websocket import ws_manager
            await ws_manager.broadcast_to_user(
                user_id=partner_id,
                message={"type": "THREAD_UPDATED", "message": message}
            )
            if user_id:
                await ws_manager.broadcast_to_user(
                    user_id=user_id,
                    message={"type": "THREAD_UPDATED", "message": message}
                )
        except Exception as e:
            print(f"Failed to send thread websocket: {e}")

        # 2. Push Notification & Presence History
        try:
            from app.services.notification import notification_service
            from app.schemas.notification import NotificationCreate, NotificationType
            cat_str = str(message.get("category", "")).lower()
            notif = NotificationCreate(
                title=title,
                message=body,
                type=NotificationType.THREAD_MESSAGE,
                recipient_id=partner_id,
                metadata={
                    "message_id": message.get("id"),
                    "category": cat_str,
                    "screen": "Thread"
                }
            )
            await notification_service.schedule_notification(user_id, notif)
        except Exception as e:
            print(f"Failed to send thread push notification: {e}")

    async def get_categories(self, user_id: str, partner_id: Optional[str] = None, user_doc: Optional[dict] = None) -> List[str]:
        if not partner_id:
            if user_doc and user_doc.get("partner"):
                partner_id = user_doc["partner"].get("user_id")
            else:
                partner_id = await self._get_partner_id(user_id)
        user_ids = [user_id]
        if partner_id: user_ids.append(partner_id)
        
        # Return categories that have at least one message in this couple's thread
        return await self.messages_collection.distinct("category", {"creator_id": {"$in": user_ids}})

    async def post_letter(self, user_id: str, payload: LetterCreate) -> Dict[str, Any]:
        partner_id = await self._get_partner_id(user_id)
        if not partner_id: raise ValueError("Partner alignment required.")
        if not payload.text or not payload.text.strip():
            raise ValueError("Letter content cannot be empty.")
        
        new_doc = {
            "category": ThreadCategory.LETTER,
            "creator_id": user_id,
            "partner_id": partner_id,
            "content": {"text": payload.text.strip()},
            "created_at": datetime.now(timezone.utc),
            "is_sent": True,
            "is_delivered": False,
            "is_seen": False
        }
        result = await self.messages_collection.insert_one(new_doc)
        new_doc["id"] = str(result.inserted_id)
        mapped = await self._map_message(new_doc, payload.timezone, user_id)
        
        sender_name = mapped.get("sender_name", "Your partner")
        snippet = payload.text.strip()[:100]
        await self._notify_partner(user_id, partner_id, mapped, f"Letter from {sender_name}", f'"{snippet}"')
        return mapped

    async def post_voice(self, user_id: str, file: UploadFile, timezone_str: str = "UTC") -> Dict[str, Any]:
        partner_id = await self._get_partner_id(user_id)
        if not partner_id: raise ValueError("Partner alignment required.")
        
        file_url = await s3_service.upload_file(file, folder="voice")
        
        new_doc = {
            "category": ThreadCategory.VOICE,
            "creator_id": user_id,
            "partner_id": partner_id,
            "content": {"file_url": file_url},
            "created_at": datetime.now(timezone.utc),
            "is_sent": True,
            "is_delivered": False,
            "is_seen": False
        }
        result = await self.messages_collection.insert_one(new_doc)
        new_doc["id"] = str(result.inserted_id)
        mapped = await self._map_message(new_doc, timezone_str, user_id)
        
        sender_name = mapped.get("sender_name", "Your partner")
        await self._notify_partner(user_id, partner_id, mapped, f"Voice Note from {sender_name}", "🔊 Left you a voice message in Thread.")
        return mapped

    async def post_voice_base64(self, user_id: str, payload: "VoiceBase64Create") -> Dict[str, Any]:
        import base64, io
        partner_id = await self._get_partner_id(user_id)
        if not partner_id: raise ValueError("Partner alignment required.")
        
        file_bytes = base64.b64decode(payload.file_base64)
        file_url = await s3_service.upload_bytes(file_bytes, payload.filename, payload.content_type, folder="voice")
            
        new_doc = {
            "category": ThreadCategory.VOICE,
            "creator_id": user_id,
            "partner_id": partner_id,
            "content": {"file_url": file_url},
            "created_at": datetime.now(timezone.utc),
            "is_sent": True,
            "is_delivered": False,
            "is_seen": False
        }
        result = await self.messages_collection.insert_one(new_doc)
        new_doc["id"] = str(result.inserted_id)
        mapped = await self._map_message(new_doc, payload.timezone, user_id)
        
        sender_name = mapped.get("sender_name", "Your partner")
        await self._notify_partner(user_id, partner_id, mapped, f"Voice Note from {sender_name}", "🔊 Left you a voice message in Thread.")
        return mapped

    async def post_photo(self, user_id: str, file: UploadFile, caption: str, timezone_str: str = "UTC") -> Dict[str, Any]:
        partner_id = await self._get_partner_id(user_id)
        if not partner_id: raise ValueError("Partner alignment required.")
        
        file_url = await s3_service.upload_file(file, folder="photo")
        
        new_doc = {
            "category": ThreadCategory.PHOTO,
            "creator_id": user_id,
            "partner_id": partner_id,
            "content": {"file_url": file_url, "caption": caption},
            "created_at": datetime.now(timezone.utc),
            "is_sent": True,
            "is_delivered": False,
            "is_seen": False
        }
        result = await self.messages_collection.insert_one(new_doc)
        new_doc["id"] = str(result.inserted_id)
        mapped = await self._map_message(new_doc, timezone_str, user_id)
        
        sender_name = mapped.get("sender_name", "Your partner")
        body_text = caption.strip() if caption and caption.strip() else "Shared a moment in Thread."
        await self._notify_partner(user_id, partner_id, mapped, f"Photo from {sender_name}", body_text)
        return mapped

    async def post_photo_base64(self, user_id: str, payload: "PhotoBase64Create") -> Dict[str, Any]:
        import base64, io
        partner_id = await self._get_partner_id(user_id)
        if not partner_id: raise ValueError("Partner alignment required.")
        
        file_bytes = base64.b64decode(payload.file_base64)
        file_url = await s3_service.upload_bytes(file_bytes, payload.filename, payload.content_type, folder="photo")
            
        new_doc = {
            "category": ThreadCategory.PHOTO,
            "creator_id": user_id,
            "partner_id": partner_id,
            "content": {"file_url": file_url, "caption": payload.caption},
            "created_at": datetime.now(timezone.utc),
            "is_sent": True,
            "is_delivered": False,
            "is_seen": False
        }
        result = await self.messages_collection.insert_one(new_doc)
        new_doc["id"] = str(result.inserted_id)
        mapped = await self._map_message(new_doc, payload.timezone, user_id)
        
        sender_name = mapped.get("sender_name", "Your partner")
        body_text = payload.caption.strip() if payload.caption and payload.caption.strip() else "Shared a moment in Thread."
        await self._notify_partner(user_id, partner_id, mapped, f"Photo from {sender_name}", body_text)
        return mapped

    async def ask_prompt(self, user_id: str, payload: PromptAskCreate) -> Dict[str, Any]:
        partner_id = await self._get_partner_id(user_id)
        if not partner_id: raise ValueError("Partner alignment required.")
        if not payload.question_text or not payload.question_text.strip():
            raise ValueError("Prompt question text cannot be empty.")
        
        new_doc = {
            "category": ThreadCategory.PROMPT,
            "creator_id": user_id,
            "partner_id": partner_id,
            "content": {
                "prompt_type": payload.prompt_type,
                "question": payload.question_text.strip(),
                "type": payload.type,
                "answer": None,
                "status": "asked"
            },
            "created_at": datetime.now(timezone.utc),
            "is_sent": True,
            "is_delivered": False,
            "is_seen": False
        }
        result = await self.messages_collection.insert_one(new_doc)
        new_doc["id"] = str(result.inserted_id)
        mapped = await self._map_message(new_doc, payload.timezone, user_id)
        
        sender_name = mapped.get("sender_name", "Your partner")
        await self._notify_partner(user_id, partner_id, mapped, f"New Prompt from {sender_name}", f'"{payload.question_text.strip()}"')
        return mapped

    async def reply_to_prompt(self, user_id: str, message_id: str, answer: str, timezone_str: str = "UTC") -> Dict[str, Any]:
        doc = await self.messages_collection.find_one({"_id": ObjectId(message_id), "partner_id": user_id})
        if not doc:
            raise ValueError("Prompt not found or you are not the recipient.")
        if not answer or not answer.strip():
            raise ValueError("Reply answer cannot be empty.")
        
        if doc["content"].get("status") == "replied":
            raise ValueError("This prompt has already been replied to.")

        result = await self.messages_collection.find_one_and_update(
            {"_id": ObjectId(message_id)},
            {"$set": {
                "content.answer": answer.strip(),
                "content.status": "replied",
                "is_seen": True, # Replied implies seen
                "is_delivered": True,
                "updated_at": datetime.now(timezone.utc)
            }},
            return_document=True
        )
        mapped = await self._map_message(result, timezone_str, user_id)
        
        # When user replies to a prompt, notify the creator of the prompt (the partner)
        creator_id = result.get("creator_id")
        sender_name = mapped.get("sender_name", "Your partner")
        await self._notify_partner(user_id, creator_id, mapped, f"Prompt Answered by {sender_name}", f'"{answer.strip()}"')
        return mapped

    async def post_appreciation(self, user_id: str, payload: AppreciationCreate) -> Dict[str, Any]:
        partner_id = await self._get_partner_id(user_id)
        if not partner_id: raise ValueError("Partner alignment required.")
        if not payload.text or not payload.text.strip():
            raise ValueError("Appreciation content cannot be empty.")
        
        new_doc = {
            "category": ThreadCategory.APPRECIATION,
            "creator_id": user_id,
            "partner_id": partner_id,
            "content": {"text": payload.text.strip()},
            "created_at": datetime.now(timezone.utc),
            "is_sent": True,
            "is_delivered": False,
            "is_seen": False
        }
        result = await self.messages_collection.insert_one(new_doc)
        new_doc["id"] = str(result.inserted_id)
        mapped = await self._map_message(new_doc, payload.timezone, user_id)
        
        sender_name = mapped.get("sender_name", "Your partner")
        snippet = payload.text.strip()[:100]
        await self._notify_partner(user_id, partner_id, mapped, f"Appreciation from {sender_name}", f'"{snippet}"')
        return mapped

    async def post_checkin(self, user_id: str, payload: CheckInThreadCreate) -> Dict[str, Any]:
        partner_id = await self._get_partner_id(user_id)
        if not partner_id: raise ValueError("Partner alignment required.")
        if not (payload.answer_1 or "").strip() and not (payload.answer_2 or "").strip() and not (payload.answer_3 or "").strip():
            raise ValueError("At least one check-in answer must be provided.")
        
        new_doc = {
            "category": ThreadCategory.CHECKIN,
            "creator_id": user_id,
            "partner_id": partner_id,
            "content": {
                "date": payload.date,
                "answer_1": (payload.answer_1 or "").strip(),
                "answer_2": (payload.answer_2 or "").strip(),
                "answer_3": (payload.answer_3 or "").strip()
            },
            "created_at": datetime.now(timezone.utc),
            "is_sent": True,
            "is_delivered": False,
            "is_seen": False
        }
        result = await self.messages_collection.insert_one(new_doc)
        new_doc["id"] = str(result.inserted_id)
        mapped = await self._map_message(new_doc, payload.timezone, user_id)
        
        sender_name = mapped.get("sender_name", "Your partner")
        await self._notify_partner(user_id, partner_id, mapped, f"Daily Check-in from {sender_name}", f"{sender_name} posted their daily check-in.")
        return mapped

    async def get_messages(self, user_id: str, page: int = 1, size: int = 20, timezone_str: str = "UTC", partner_id: Optional[str] = None, user_doc: Optional[dict] = None) -> Tuple[List[Dict[str, Any]], int]:
        if not partner_id:
            if user_doc and user_doc.get("partner"):
                partner_id = user_doc["partner"].get("user_id")
            else:
                partner_id = await self._get_partner_id(user_id)
        user_ids = [user_id]
        if partner_id: user_ids.append(partner_id)
        
        query = {
            "creator_id": {"$in": user_ids},
            "deleted_for": {"$ne": user_id}
        }
        
        # Parallelize update and fetches
        skip = (page - 1) * size
        cursor = self.messages_collection.find(query).sort("created_at", -1).skip(skip).limit(size)
        
        update_task = self.messages_collection.update_many(
            {"partner_id": user_id, "is_seen": False},
            {"$set": {"is_delivered": True, "is_seen": True}}
        )

        _, docs, total = await asyncio.gather(
            update_task,
            cursor.to_list(length=size),
            self.messages_collection.count_documents(query)
        )
        
        # Pre-fetch user profiles for all messages in one single query
        all_uids = set()
        for d in docs:
            cid = str(d.get("creator_id", ""))
            pid = str(d.get("partner_id", ""))
            if cid: all_uids.add(cid)
            if pid: all_uids.add(pid)
        all_uids.add(str(user_id))
        if partner_id: all_uids.add(str(partner_id))

        names_cache: Dict[str, str] = {}
        photos_cache: Dict[str, str] = {}
        obj_ids = [ObjectId(uid) for uid in all_uids if ObjectId.is_valid(uid)]
        if obj_ids:
            async for user in self.users.find({"_id": {"$in": obj_ids}}):
                uid_str = str(user["_id"])
                names_cache[uid_str] = user.get("name", "User")
                photo = user.get("profile_photo_url") or user.get("photo_url") or user.get("avatar")
                if not photo and user.get("partner"):
                    photo = user["partner"].get("profile_photo_url")
                if photo:
                    photos_cache[uid_str] = photo
                if user.get("partner") and user["partner"].get("user_id"):
                    p_uid = str(user["partner"]["user_id"])
                    if p_uid not in photos_cache and user["partner"].get("profile_photo_url"):
                        photos_cache[p_uid] = user["partner"]["profile_photo_url"]

        return [await self._map_message(d, timezone_str, user_id, names_cache=names_cache, photos_cache=photos_cache) for d in docs], total

    async def delete_message(self, user_id: str, message_id: str, mode: str = "everyone") -> bool:
        partner_id = await self._get_partner_id(user_id)
        user_ids = [user_id]
        if partner_id: user_ids.append(partner_id)
        
        doc = await self.messages_collection.find_one({"_id": ObjectId(message_id), "creator_id": {"$in": user_ids}})
        if not doc:
            return False
            
        is_own_message = (str(doc.get("creator_id")) == user_id)

        if mode == "me":
            # Delete for You: Hide from current user
            await self.messages_collection.update_one(
                {"_id": ObjectId(message_id)},
                {"$addToSet": {"deleted_for": user_id}}
            )
            try:
                from app.core.websocket import ws_manager
                await ws_manager.broadcast_to_user(
                    user_id=user_id,
                    message={"type": "THREAD_UPDATED", "deleted_id": message_id}
                )
            except Exception as e:
                print("Failed to send thread deletion ws:", e)
            return True

        elif mode == "everyone":
            if not is_own_message:
                raise ValueError("You can only delete your own messages for everyone.")

            file_url = doc.get("content", {}).get("file_url")
            if file_url:
                if "amazonaws.com" in file_url:
                    await s3_service.delete_file(file_url)
                else:
                    local_path = file_url.lstrip("/")
                    if os.path.exists(local_path):
                        try: os.remove(local_path)
                        except Exception: pass
                    
            result = await self.messages_collection.delete_one({"_id": ObjectId(message_id)})
            if result.deleted_count > 0:
                try:
                    from app.core.websocket import ws_manager
                    if partner_id:
                        await ws_manager.broadcast_to_user(
                            user_id=partner_id,
                            message={"type": "THREAD_UPDATED", "deleted_id": message_id}
                        )
                    await ws_manager.broadcast_to_user(
                        user_id=user_id,
                        message={"type": "THREAD_UPDATED", "deleted_id": message_id}
                    )
                except Exception as e:
                    print("Failed to send thread deletion ws:", e)
                return True
        return False

    async def update_message(self, user_id: str, message_id: str, updates: Dict[str, Any], file: Optional[UploadFile] = None, timezone_str: str = "UTC") -> Dict[str, Any]:
        doc = await self.messages_collection.find_one({"_id": ObjectId(message_id), "creator_id": user_id})
        if not doc:
            raise ValueError("Message not found or permission denied.")

        category = doc["category"]
        content_updates = {}
        
        if category == ThreadCategory.LETTER:
            if "text" in updates: content_updates["text"] = updates["text"]
        elif category == ThreadCategory.APPRECIATION:
            if "text" in updates: content_updates["text"] = updates["text"]
        elif category == ThreadCategory.PHOTO:
            if "caption" in updates: content_updates["caption"] = updates["caption"]
            if file:
                old_file = doc["content"].get("file_url")
                if old_file:
                    if "amazonaws.com" in old_file:
                        await s3_service.delete_file(old_file)
                    else:
                        lp = old_file.lstrip("/")
                        if os.path.exists(lp): os.remove(lp)
                
                content_updates["file_url"] = await s3_service.upload_file(file, folder="photo")
        elif category == ThreadCategory.VOICE:
            if file:
                old_file = doc["content"].get("file_url")
                if old_file:
                    if "amazonaws.com" in old_file:
                        await s3_service.delete_file(old_file)
                    else:
                        lp = old_file.lstrip("/")
                        if os.path.exists(lp): os.remove(lp)
                
                content_updates["file_url"] = await s3_service.upload_file(file, folder="voice")
        elif category == ThreadCategory.PROMPT:
            if doc["content"].get("status") == "replied":
                raise ValueError("Cannot update a prompt that has already been replied to.")
            if "prompt_type" in updates: content_updates["prompt_type"] = updates["prompt_type"]
            if "question" in updates: content_updates["question"] = updates["question"]
            if "type" in updates: content_updates["type"] = updates["type"]
        elif category == ThreadCategory.CHECKIN:
            for k in ["answer_1", "answer_2", "answer_3", "date"]:
                if k in updates: content_updates[k] = updates[k]

        if not content_updates:
            return await self._map_message(doc, timezone_str, user_id)

        new_content = doc["content"].copy()
        new_content.update(content_updates)

        result = await self.messages_collection.find_one_and_update(
            {"_id": ObjectId(message_id)},
            {"$set": {"content": new_content, "updated_at": datetime.now(timezone.utc)}},
            return_document=True
        )
        return await self._map_message(result, timezone_str, user_id)

    async def _map_message(self, d: Dict[str, Any], timezone_str: str, current_user_id: str, names_cache: Optional[Dict[str, str]] = None, photos_cache: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        d["id"] = str(d["_id"]) if "_id" in d else d.get("id")
        if "_id" in d: del d["_id"]
        
        creator_str = str(d.get("creator_id", ""))

        if names_cache is not None and photos_cache is not None:
            names = names_cache
            photos = photos_cache
        else:
            partner_id = await self._get_partner_id(creator_str)
            partner_str = str(partner_id) if partner_id else None

            user_ids_to_fetch = []
            for uid in [creator_str, partner_str, str(current_user_id)]:
                if uid:
                    user_ids_to_fetch.append(uid)
                    if ObjectId.is_valid(uid):
                        user_ids_to_fetch.append(ObjectId(uid))

            names = {}
            photos = {}
            if user_ids_to_fetch:
                async for user in self.users.find({"_id": {"$in": user_ids_to_fetch}}):
                    uid_str = str(user["_id"])
                    names[uid_str] = user.get("name", "User")
                    
                    photo = user.get("profile_photo_url") or user.get("photo_url") or user.get("avatar")
                    if not photo and user.get("partner"):
                        photo = user["partner"].get("profile_photo_url")
                    if photo:
                        photos[uid_str] = photo
                    if user.get("partner") and user["partner"].get("user_id"):
                        p_uid = str(user["partner"]["user_id"])
                        if p_uid not in photos and user["partner"].get("profile_photo_url"):
                            photos[p_uid] = user["partner"]["profile_photo_url"]

        u_name = names.get(str(current_user_id), "User")
        p_name = "Partner"
        for uid, name in names.items():
            if uid != str(current_user_id):
                p_name = name
                break

        d["user_name"] = u_name
        d["partner_name"] = p_name
        d["sender_name"] = names.get(creator_str, "User")
        d["sender_photo"] = photos.get(creator_str)
        d["sender_id"] = creator_str
        
        d["is_sent"] = d.get("is_sent", True)
        d["is_delivered"] = d.get("is_delivered", False)
        d["is_seen"] = d.get("is_seen", False)

        try:
            tz = zoneinfo.ZoneInfo(timezone_str)
        except Exception:
            tz = zoneinfo.ZoneInfo("UTC")
            
        dt = d["created_at"]
        if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
        d["created_at"] = dt.astimezone(tz)
        
        return d

    # --- Prompt Question CRUD ---
    async def get_prompt_questions(self, user_id: str, prompt_type: PromptType) -> List[Dict[str, Any]]:
        partner_id = await self._get_partner_id(user_id)
        creator_ids = [None, user_id]
        if partner_id: creator_ids.append(partner_id)
        
        query = {"type": prompt_type, "creator_id": {"$in": creator_ids}}
        cursor = self.prompts_collection.find(query)
        docs = await cursor.to_list(length=None)
        
        if not docs:
            defaults = DEFAULT_ROMANTIC_QUESTIONS if prompt_type == PromptType.ROMANTIC else DEFAULT_DESIRED_QUESTIONS
            for q in defaults:
                q_copy = q.copy()
                q_copy["creator_id"] = None
                await self.prompts_collection.update_one(
                    {"text": q_copy["text"], "type": q_copy["type"], "creator_id": None},
                    {"$setOnInsert": q_copy},
                    upsert=True
                )
            cursor = self.prompts_collection.find(query)
            docs = await cursor.to_list(length=None)

        for d in docs:
            d["id"] = str(d["_id"])
            del d["_id"]
        return docs

    async def create_prompt_question(self, user_id: str, payload: PromptQuestionCreate) -> Dict[str, Any]:
        new_doc = payload.model_dump()
        new_doc["creator_id"] = user_id
        result = await self.prompts_collection.insert_one(new_doc)
        new_doc["id"] = str(result.inserted_id)
        return new_doc

    async def update_prompt_question(self, user_id: str, question_id: str, payload: PromptQuestionCreate) -> Dict[str, Any]:
        result = await self.prompts_collection.find_one_and_update(
            {"_id": ObjectId(question_id), "creator_id": user_id},
            {"$set": payload.model_dump()},
            return_document=True
        )
        if not result: raise ValueError("Question not found or permission denied.")
        result["id"] = str(result["_id"])
        del result["_id"]
        return result

    async def delete_prompt_question(self, user_id: str, question_id: str) -> bool:
        result = await self.prompts_collection.delete_one({"_id": ObjectId(question_id), "creator_id": user_id})
        return result.deleted_count > 0

thread_service = ThreadService()
