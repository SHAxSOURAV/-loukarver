import os
import uuid
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from bson import ObjectId

from app.core.db import get_client, get_db
from app.core.websocket import ws_manager
from app.services.notification import notification_service
from app.schemas.notification import NotificationCreate, NotificationType, PresenceCreate
from app.services.s3_utils import s3_service

class RelationshipPhotoService:
    def __init__(self) -> None:
        self.client = get_client()
        self.db = get_db()
        self.collection = self.db["users"]

    async def add_profile_photo(self, user_id: str, file_url: str) -> Dict[str, Any]:
        """Adds a new profile photo to history and sets it as the active photo."""
        photo_id = uuid.uuid4().hex
        photo_entry = {
            "id": photo_id,
            "url": file_url,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        user = await self.collection.find_one({"_id": ObjectId(user_id)})
        current_photos = user.get("profile_photos") or []
        if not current_photos and user.get("profile_photo_url"):
            current_photos = [{
                "id": uuid.uuid4().hex,
                "url": user["profile_photo_url"],
                "created_at": datetime.now(timezone.utc).isoformat()
            }]
            
        new_photos = [photo_entry] + [p for p in current_photos if p.get("url") != file_url]
        
        await self.collection.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "profile_photo_url": file_url,
                    "profile_photos": new_photos
                }
            }
        )
        
        return await self._notify_profile_photo_update(user_id)

    async def get_profile_photos(self, user_id: str, user: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Retrieves all profile photos for the user."""
        if not user:
            user = await self.collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise ValueError("User not found.")
            
        photos = user.get("profile_photos") or []
        active_url = user.get("profile_photo_url")
        
        # Auto-migrate legacy photo if photos list is empty
        if not photos and active_url:
            migrated_photo = {
                "id": uuid.uuid4().hex,
                "url": active_url,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            photos = [migrated_photo]
            await self.collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"profile_photos": photos}}
            )
            
        return {
            "photos": photos,
            "active_url": active_url
        }

    async def select_profile_photo(self, user_id: str, photo_id: str) -> Dict[str, Any]:
        """Selects an existing photo from history as the active profile photo."""
        user = await self.collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise ValueError("User not found.")
            
        photos = user.get("profile_photos") or []
        selected = next((p for p in photos if str(p.get("id")) == str(photo_id) or p.get("url") == photo_id), None)
        if not selected:
            raise ValueError("Selected photo not found.")
            
        await self.collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"profile_photo_url": selected["url"]}}
        )
        
        return await self._notify_profile_photo_update(user_id)

    async def delete_profile_photo_item(self, user_id: str, photo_id: str) -> Dict[str, Any]:
        """Deletes a specific photo item from the user's gallery history."""
        user = await self.collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise ValueError("User not found.")
            
        photos = user.get("profile_photos") or []
        target = next((p for p in photos if str(p.get("id")) == str(photo_id) or p.get("url") == photo_id), None)
        
        active_url = user.get("profile_photo_url")
        if not target and active_url and (str(photo_id) == str(active_url) or str(photo_id) in str(active_url)):
            target = {"id": photo_id, "url": active_url}
            
        if not target:
            raise ValueError("Photo not found.")
            
        file_url = target.get("url")
        if file_url:
            if s3_service.is_s3_or_cdn_url(file_url):
                await s3_service.delete_file(file_url)
            elif os.path.exists(file_url.lstrip("/")):
                os.remove(file_url.lstrip("/"))
                
        remaining_photos = [p for p in photos if str(p.get("id")) != str(photo_id) and p.get("url") != target.get("url")]
        
        new_active_url = user.get("profile_photo_url")
        if new_active_url == file_url or not remaining_photos:
            new_active_url = remaining_photos[0]["url"] if remaining_photos else None
            
        await self.collection.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "profile_photo_url": new_active_url,
                    "profile_photos": remaining_photos
                }
            }
        )
        
        return await self._notify_profile_photo_update(user_id)

    async def update_profile_photo(self, user_id: str, file_path: str) -> Dict[str, Any]:
        """Updates the user's profile photo path."""
        if file_path:
            return await self.add_profile_photo(user_id, file_path)
        else:
            await self.collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"profile_photo_url": None}}
            )
            return await self._notify_profile_photo_update(user_id)

    async def _notify_profile_photo_update(self, user_id: str) -> Dict[str, Any]:
        """Internal helper to broadcast photo updates and return updated user object."""
        updated = await self.collection.find_one({"_id": ObjectId(user_id)})
        if updated and "_id" in updated:
            updated["id"] = str(updated["_id"])
            updated["_id"] = str(updated["_id"])
            
            if updated.get("partner") and updated["partner"].get("user_id"):
                partner_id = updated["partner"]["user_id"]
                user_name = updated.get("name", "Your partner")
                
                await ws_manager.broadcast_to_user(
                    partner_id, 
                    {"type": "PROFILE_PHOTO_UPDATED"}
                )
                
                try:
                    await notification_service.schedule_notification(
                        sender_id=user_id,
                        payload=NotificationCreate(
                            recipient_id=partner_id,
                            title="Profile Photo Updated",
                            message=f"{user_name} updated their profile picture.",
                            type=NotificationType.STATE_UPDATE,
                            scheduled_for=datetime.now(timezone.utc),
                            timezone="UTC"
                        )
                    )
                except Exception as e:
                    print(f"Failed to send profile photo notification: {e}")

                try:
                    await notification_service.log_presence(
                        user_id,
                        PresenceCreate(timezone="UTC")
                    )
                except Exception as e:
                    print(f"Failed to log profile photo presence: {e}")

        return updated

    async def get_profile_photo_path(self, user_id: str) -> str:
        """Retrieves the user's profile photo path."""
        user = await self.collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise ValueError("User not found.")
        return user.get("profile_photo_url")

relationship_photo_service = RelationshipPhotoService()

