import re
import os
import uuid
import shutil
from typing import Dict, Any, List, Optional, Tuple
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.db import get_client, get_db

from bson import ObjectId
from datetime import datetime, timezone, timedelta
import zoneinfo
from fastapi import UploadFile

from app.core.config import settings
from app.core.websocket import ws_manager
from app.services.s3_utils import s3_service
from app.services.notification import notification_service
import asyncio

def parse_duration(duration_str: str) -> timedelta:
    """Parses strings like '10 Minutes', '1 Hours', '10 Seconds'."""
    duration_str = duration_str.lower()
    
    # Check for hours
    hours_match = re.search(r"(\d+(\.\d+)?)\s*hour", duration_str)
    if hours_match:
        return timedelta(hours=float(hours_match.group(1)))
    
    # Check for minutes
    minutes_match = re.search(r"(\d+)\s*minute", duration_str)
    if minutes_match:
        return timedelta(minutes=int(minutes_match.group(1)))

    # Check for seconds
    seconds_match = re.search(r"(\d+)\s*second", duration_str)
    if seconds_match:
        return timedelta(seconds=int(seconds_match.group(1)))
        
    return timedelta(hours=24) # Default to 24 hours

class SecretService:
    def __init__(self) -> None:
        self.client = get_client()
        self.db = get_db()
        self.secrets_collection = self.db["secrets"]
        self.users = self.db["users"]

    async def init_indexes(self):
        try:
            # Auto-delete secrets at the exact expires_at timestamp
            await self.secrets_collection.create_index("expires_at", expireAfterSeconds=0)
            await self.secrets_collection.create_index([("recipient_id", 1), ("created_at", -1)])
            await self.secrets_collection.create_index([("sender_id", 1), ("created_at", -1)])
        except Exception as e:
            print(f"Error initializing secret indexes: {e}")

    async def _get_partner_id(self, user_id: str) -> Optional[str]:
        user = await self.users.find_one({"_id": ObjectId(user_id)}, {"partner.user_id": 1, "is_aligned": 1})
        if user and user.get("is_aligned") and user.get("partner"):
            return user["partner"]["user_id"]
        return None

    async def _get_names(self, user_id: str, partner_id: Optional[str]) -> Tuple[str, str]:
        user = await self.users.find_one({"_id": ObjectId(user_id)}, {"name": 1})
        u_name = user.get("name", "User") if user else "User"
        p_name = "Partner"
        if partner_id:
            pt = await self.users.find_one({"_id": ObjectId(partner_id)}, {"name": 1})
            if pt:
                p_name = pt.get("name", "Partner")
        return u_name, p_name

    async def save_secret(self, sender_id: str, file: UploadFile, prevent_screenshot: bool = True, delete_after: str = "24 Hours") -> Dict[str, Any]:
        partner_id = await self._get_partner_id(sender_id)
        if not partner_id:
            raise ValueError("You must be aligned with a partner to send secrets.")

        # Parse expiration
        duration = parse_duration(delete_after)
        now = datetime.now(timezone.utc)
        expires_at = now + duration

        # Save file to S3
        file_url = await s3_service.upload_file(file, folder="secrets")

        # Create database entry
        new_doc = {
            "sender_id": sender_id,
            "recipient_id": partner_id,
            "filename": file.filename,
            "stored_filename": file_url,
            "file_type": file.content_type,
            "size": file.size,
            "prevent_screenshot": prevent_screenshot,
            "delete_after": delete_after,
            "created_at": now,
            "expires_at": expires_at,
            "is_viewed": False,
            "status": "delivered",
            "rewatch_status": "none"
        }
        
        result = await self.secrets_collection.insert_one(new_doc)
        new_doc["id"] = str(result.inserted_id)
        
        # Fire websocket to recipient
        await ws_manager.broadcast_to_user(partner_id, {"type": "SECRET_DELIVERED"})
        
        # Send Push Notification
        u_name, p_name = await self._get_names(sender_id, partner_id)
        asyncio.create_task(notification_service.send_onesignal_push(
            partner_id, 
            f"New Secret from {u_name}!", 
            "They sent you something for your eyes only 🤫",
            {"url": "samesy://connect"}
        ))
        
        return new_doc

    async def _resolve_user_partner_names(self, user_id: str, user_doc: Optional[Dict[str, Any]] = None) -> Tuple[str, str]:
        if user_doc:
            user = user_doc
        else:
            user = await self.users.find_one({"_id": ObjectId(user_id)}, {"partner": 1, "name": 1, "is_aligned": 1})
        u_name = user.get("name", "User") if user else "User"
        p_name = "Partner"
        partner_id = user.get("partner", {}).get("user_id") if user and user.get("is_aligned") and user.get("partner") else None
        if partner_id:
            pt = await self.users.find_one({"_id": ObjectId(partner_id)}, {"name": 1})
            if pt:
                p_name = pt.get("name", "Partner")
        return u_name, p_name

    async def get_secrets_for_me(self, user_id: str, page: int = 1, size: int = 10, user_timezone: str = "UTC", user_doc: Optional[Dict[str, Any]] = None) -> Tuple[List[Dict[str, Any]], int]:
        skip = (page - 1) * size
        query = {"recipient_id": user_id}
        
        cursor = self.secrets_collection.find(query).sort("created_at", -1).skip(skip).limit(size)
        docs_task = cursor.to_list(length=None)
        total_task = self.secrets_collection.count_documents(query)
        names_task = self._resolve_user_partner_names(user_id, user_doc)
        
        docs, total, (u_name, p_name) = await asyncio.gather(docs_task, total_task, names_task)

        try:
            tz = zoneinfo.ZoneInfo(user_timezone)
        except Exception:
            tz = zoneinfo.ZoneInfo("UTC")

        results = []
        for d in docs:
            d["id"] = str(d["_id"])
            del d["_id"]
            d["user_name"] = u_name
            d["partner_name"] = p_name
            if "prevent_screenshot" not in d:
                d["prevent_screenshot"] = True
            
            # Timezone conversion
            for field in ["created_at", "expires_at"]:
                dt = d.get(field)
                if isinstance(dt, datetime):
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    d[field] = dt.astimezone(tz)
                    
            results.append(d)
        return results, total

    async def get_sent_secrets(self, user_id: str, page: int = 1, size: int = 10, user_timezone: str = "UTC", user_doc: Optional[Dict[str, Any]] = None) -> Tuple[List[Dict[str, Any]], int]:
        skip = (page - 1) * size
        query = {
            "sender_id": user_id,
            "$or": [
                {"is_viewed": False},
                {"rewatch_status": "requested"}
            ]
        }
        
        cursor = self.secrets_collection.find(query).sort("created_at", -1).skip(skip).limit(size)
        docs_task = cursor.to_list(length=None)
        total_task = self.secrets_collection.count_documents(query)
        names_task = self._resolve_user_partner_names(user_id, user_doc)
        
        docs, total, (u_name, p_name) = await asyncio.gather(docs_task, total_task, names_task)

        try:
            tz = zoneinfo.ZoneInfo(user_timezone)
        except Exception:
            tz = zoneinfo.ZoneInfo("UTC")

        results = []
        for d in docs:
            d["id"] = str(d["_id"])
            del d["_id"]
            d["user_name"] = u_name
            d["partner_name"] = p_name
            if "prevent_screenshot" not in d:
                d["prevent_screenshot"] = True

            # Timezone conversion
            for field in ["created_at", "expires_at"]:
                dt = d.get(field)
                if isinstance(dt, datetime):
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    d[field] = dt.astimezone(tz)

            results.append(d)
        return results, total

    async def patch_screenshot_protection(self, secret_id: str, user_id: str, prevent: bool) -> bool:
        result = await self.secrets_collection.update_one(
            {"_id": ObjectId(secret_id), "sender_id": user_id, "is_viewed": False},
            {"$set": {"prevent_screenshot": prevent}}
        )
        return result.matched_count > 0

    async def get_secret_metadata(self, secret_id: str, user_id: str, user_timezone: str = "UTC") -> Dict[str, Any]:
        now_utc = datetime.now(timezone.utc)
        doc = await self.secrets_collection.find_one({
            "_id": ObjectId(secret_id),
            "$or": [{"recipient_id": user_id}, {"sender_id": user_id}]
        })
        if not doc:
            raise ValueError("Secret not found or expired.")
        
        # Expiration check
        exp = doc.get("expires_at")
        if isinstance(exp, datetime):
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if now_utc > exp:
                raise ValueError("This secret has expired and is no longer available.")

        # Permission & viewing state check
        is_recipient = doc.get("recipient_id") == user_id
        is_sender = doc.get("sender_id") == user_id

        if is_recipient:
            # Recipient can view if:
            # 1. Not yet viewed (first open)
            # 2. Rewatch was approved by sender
            # 3. Currently within active streaming window (allow 24 hours or until expiry so video doesn't stall/fail)
            is_viewed = doc.get("is_viewed", False)
            rewatch_status = doc.get("rewatch_status", "none")
            
            if is_viewed and rewatch_status != "approved":
                # Check active viewing window
                viewed_at = doc.get("viewed_at")
                if viewed_at:
                    if isinstance(viewed_at, datetime):
                        if viewed_at.tzinfo is None:
                            viewed_at = viewed_at.replace(tzinfo=timezone.utc)
                        # Allow active streaming / rebuffering for 24 hours after opening
                        if now_utc - viewed_at > timedelta(hours=24):
                            raise ValueError("This secret was already viewed. Ask your partner to rewatch!")
                else:
                    raise ValueError("This secret was already viewed. Ask your partner to rewatch!")

        try:
            tz = zoneinfo.ZoneInfo(user_timezone)
        except Exception:
            tz = zoneinfo.ZoneInfo("UTC")

        # Timezone conversion for metadata
        for field in ["created_at", "expires_at", "viewed_at"]:
            dt = doc.get(field)
            if isinstance(dt, datetime):
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                doc[field] = dt.astimezone(tz)

        return doc

    async def mark_secret_viewed(self, secret_id: str):
        # Fetch it first to get the sender_id
        doc = await self.secrets_collection.find_one({"_id": ObjectId(secret_id)})
        if not doc:
            return

        now_utc = datetime.now(timezone.utc)
        already_viewed = doc.get("is_viewed", False)

        # Update viewed status and timestamp
        await self.secrets_collection.update_one(
            {"_id": ObjectId(secret_id)},
            {"$set": {
                "is_viewed": True, 
                "status": "viewed", 
                "viewed_at": now_utc,
                "rewatch_status": "none"
            }}
        )
        
        # Fire websocket back to sender for read receipts only if state changed
        if not already_viewed or doc.get("rewatch_status") == "approved":
            await ws_manager.broadcast_to_user(doc["sender_id"], {"type": "SECRET_VIEWED"})

    async def request_rewatch(self, secret_id: str, user_id: str):
        doc = await self.secrets_collection.find_one({"_id": ObjectId(secret_id), "recipient_id": user_id})
        if not doc:
            raise ValueError("Secret not found or you are not the recipient.")
        
        await self.secrets_collection.update_one(
            {"_id": ObjectId(secret_id)},
            {"$set": {"rewatch_status": "requested"}}
        )
        await ws_manager.broadcast_to_user(doc["sender_id"], {"type": "SECRET_REWATCH_REQUESTED"})
        
        # Send Push Notification to Sender
        u_name, p_name = await self._get_names(user_id, doc["sender_id"])
        asyncio.create_task(notification_service.send_onesignal_push(
            doc["sender_id"], 
            f"{u_name} asked to rewatch!", 
            "They want to see your secret one more time.",
            {"url": "samesy://connect"}
        ))
        
    async def approve_rewatch(self, secret_id: str, user_id: str):
        doc = await self.secrets_collection.find_one({"_id": ObjectId(secret_id), "sender_id": user_id})
        if not doc:
            raise ValueError("Secret not found or you are not the sender.")
            
        await self.secrets_collection.update_one(
            {"_id": ObjectId(secret_id)},
            {"$set": {"rewatch_status": "approved", "is_viewed": False, "status": "delivered"}}
        )
        await ws_manager.broadcast_to_user(doc["recipient_id"], {"type": "SECRET_REWATCH_APPROVED"})
        
        # Send Push Notification
        u_name, p_name = await self._get_names(user_id, doc["recipient_id"])
        asyncio.create_task(notification_service.send_onesignal_push(
            doc["recipient_id"], 
            f"{u_name} Approved!", 
            "You have 24 hours to rewatch their secret.",
            {"url": "samesy://secrethistory"}
        ))

    async def decline_rewatch(self, secret_id: str, user_id: str):
        doc = await self.secrets_collection.find_one({"_id": ObjectId(secret_id), "sender_id": user_id})
        if not doc:
            raise ValueError("Secret not found or you are not the sender.")
            
        await self.secrets_collection.update_one(
            {"_id": ObjectId(secret_id)},
            {"$set": {"rewatch_status": "denied"}}
        )
        await ws_manager.broadcast_to_user(doc["recipient_id"], {"type": "SECRET_REWATCH_DENIED"})
        
        # Send Push Notification to Recipient
        u_name, p_name = await self._get_names(user_id, doc["recipient_id"])
        asyncio.create_task(notification_service.send_onesignal_push(
            doc["recipient_id"], 
            f"Rewatch Denied", 
            f"{u_name} chose to keep it a secret.",
            {"url": "samesy://connect"}
        ))

    async def revoke_secret(self, secret_id: str, user_id: str):
        doc = await self.secrets_collection.find_one({"_id": ObjectId(secret_id), "sender_id": user_id})
        if not doc:
            raise ValueError("Secret not found or you are not the sender.")
        
        if doc.get("is_viewed"):
            raise ValueError("Cannot revoke a secret that has already been viewed.")
            
        # Delete file
        try:
            if doc["stored_filename"] and "amazonaws.com" in doc["stored_filename"]:
                await s3_service.delete_file(doc["stored_filename"])
            else:
                file_path = self.get_full_path(doc["stored_filename"])
                if os.path.exists(file_path):
                    os.remove(file_path)
        except Exception:
            pass
        
        # Delete from DB
        await self.secrets_collection.delete_one({"_id": ObjectId(secret_id)})
        
        # Emit WebSocket to recipient so it vanishes from their UI
        await ws_manager.broadcast_to_user(doc["recipient_id"], {"type": "SECRET_REVOKED"})

    def get_full_path(self, stored_filename: str) -> str:
        return os.path.join(self.storage_path, stored_filename)

    def delete_file(self, file_path: str):
        """Physical deletion of the file."""
        if os.path.exists(file_path):
            os.remove(file_path)

secret_service = SecretService()
