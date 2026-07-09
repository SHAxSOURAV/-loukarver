import random
import string
import os
from typing import Dict, Any, Optional, List
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from datetime import datetime, timezone, timedelta
from app.core.config import settings
from app.schemas.vibe_check import VibeCheckProfileCreate, VibeInviteResponse, VibeInviteValidateResponse, VibeInviteAcceptResponse

class VibeCheckService:
    def __init__(self) -> None:
        self.client = AsyncIOMotorClient(settings.MONGO_URL)
        self.db = self.client[settings.MONGO_DB_NAME]
        self.profiles = self.db["vibe_check_profiles"]
        self.connections = self.db["vibe_check_connections"]
        self.requests = self.db["vibe_check_requests"]
        self.invites = self.db["vibe_check_invites"]
        self.cumulative_scores = self.db["vibe_cumulative_scores"]
        self.user_streaks = self.db["vibe_user_streaks"]

    async def init_indexes(self):
        await self.profiles.create_index("user_id", unique=True)
        await self.profiles.create_index("vibe_key", unique=True)
        await self.connections.create_index([("user_id", 1), ("partner_id", 1)], unique=True)
        await self.requests.create_index([("sender_id", 1), ("recipient_id", 1)], unique=True)
        await self.requests.create_index("recipient_id")
        await self.invites.create_index("invite_code", unique=True)
        await self.invites.create_index("inviter_id")

    async def generate_unique_vibe_key(self) -> str:
        """Generates a unique 12-character vibe key like VIBE-X7R2P9."""
        while True:
            random_part = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
            vibe_key = f"VIBE-{random_part}"
            existing = await self.profiles.find_one({"vibe_key": vibe_key})
            if not existing:
                return vibe_key

    async def get_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        now = datetime.now(timezone.utc)
        
        # Update user's last activity whenever they fetch their profile
        # This allows us to track "active" users
        doc = await self.profiles.find_one_and_update(
            {"user_id": user_id},
            {"$set": {"updated_at": now}},
            return_document=True
        )
        
        if doc:
            # AUTO-FIX: If vibe_key is missing for some reason, generate and save it
            if not doc.get("vibe_key"):
                vibe_key = await self.generate_unique_vibe_key()
                await self.profiles.update_one(
                    {"_id": doc["_id"]},
                    {"$set": {"vibe_key": vibe_key}}
                )
                doc["vibe_key"] = vibe_key
            
            # 1. Count connections (connect)
            connect_count = await self.connections.count_documents({"user_id": user_id})
            
            # 2. Categorize partners (active vs inactive) - Threshold: 5 minutes
            active_threshold = now - timedelta(minutes=5)
            
            # Fetch all partner IDs for this user
            cursor = self.connections.find({"user_id": user_id}, {"partner_id": 1})
            connection_docs = await cursor.to_list(length=None)
            partner_ids = [c["partner_id"] for c in connection_docs]
            
            active_users = []
            inactive_users = []
            
            if partner_ids:
                # Fetch all partner profiles
                partner_profiles_cursor = self.profiles.find({"user_id": {"$in": partner_ids}})
                partner_profiles = await partner_profiles_cursor.to_list(length=None)
                
                for p in partner_profiles:
                    p_id = p["user_id"]
                    
                    # 1. Determine activity
                    last_active = p.get("updated_at")
                    if last_active and last_active.tzinfo is None:
                        last_active = last_active.replace(tzinfo=timezone.utc)
                    
                    is_active = last_active and last_active >= active_threshold
                    
                    # 2. Get match percentage
                    score_doc = await self.cumulative_scores.find_one({
                        "user_id": user_id, 
                        "partner_id": p_id
                    })
                    match_percentage = round(score_doc["score"], 1) if score_doc else 0.0
                    
                    # 3. Get partner's streak
                    streak_doc = await self.user_streaks.find_one({"user_id": p_id})
                    streak_days = streak_doc["current_streak"] if streak_doc else 0
                    
                    stats = {
                        "user_id": p["user_id"],
                        "name": p["name"],
                        "match_percentage": match_percentage,
                        "streak_days": streak_days
                    }
                    
                    if is_active:
                        active_users.append(stats)
                    else:
                        inactive_users.append(stats)
                
            doc["id"] = str(doc["_id"])
            doc["connect"] = connect_count
            doc["active"] = len(active_users)
            doc["active_users"] = active_users
            doc["inactive"] = len(inactive_users)
            doc["inactive_users"] = inactive_users
            return doc
        return None

    async def create_or_update_profile(self, user_id: str, payload: VibeCheckProfileCreate) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        existing = await self.profiles.find_one({"user_id": user_id})
        
        if existing:
            update_data = {"name": payload.name, "updated_at": now}
            if not existing.get("vibe_key"):
                update_data["vibe_key"] = await self.generate_unique_vibe_key()
                
            await self.profiles.update_one(
                {"user_id": user_id},
                {"$set": update_data}
            )
        else:
            vibe_key = await self.generate_unique_vibe_key()
            doc = {
                "user_id": user_id,
                "name": payload.name,
                "vibe_key": vibe_key,
                "created_at": now,
                "updated_at": now
            }
            await self.profiles.insert_one(doc)

        return await self.get_profile(user_id)

    async def update_settings(self, user_id: str, payload: VibeCheckProfileUpdate) -> Dict[str, Any]:
        """Update VibeCheck settings such as vibe_key_enabled."""
        now = datetime.now(timezone.utc)
        existing = await self.profiles.find_one({"user_id": user_id})
        if not existing:
            raise ValueError("VibeCheck profile not found.")
            
        update_data = {"updated_at": now}
        if payload.name is not None:
            update_data["name"] = payload.name
        if payload.vibe_key_enabled is not None:
            update_data["vibe_key_enabled"] = payload.vibe_key_enabled
            
        await self.profiles.update_one(
            {"user_id": user_id},
            {"$set": update_data}
        )
        return await self.get_profile(user_id)

    async def update_profile_picture(self, user_id: str, file_path: str) -> Dict[str, Any]:
        """Update the user's VibeCheck profile picture."""
        # Convert local path to an accessible URL path (assuming StaticFiles mounted at /uploads)
        url_path = f"/{file_path.replace(os.sep, '/')}"
        
        await self.profiles.update_one(
            {"user_id": user_id},
            {"$set": {"profile_picture": url_path, "updated_at": datetime.now(timezone.utc)}}
        )
        return await self.get_profile(user_id)

    async def delete_profile_picture(self, user_id: str) -> Dict[str, Any]:
        """Remove the user's VibeCheck profile picture."""
        await self.profiles.update_one(
            {"user_id": user_id},
            {"$set": {"profile_picture": None, "updated_at": datetime.now(timezone.utc)}}
        )
        return await self.get_profile(user_id)

    async def get_connections(self, user_id: str) -> List[Dict[str, Any]]:
        """List all people this user is connected with in VibeCheck."""
        cursor = self.connections.find({"user_id": user_id})
        connection_docs = await cursor.to_list(length=None)
        
        partner_ids = [c["partner_id"] for c in connection_docs]
        partner_profiles = await self.profiles.find({"user_id": {"$in": partner_ids}}).to_list(length=None)
        profile_map = {p["user_id"]: p for p in partner_profiles}
        
        user_answers_col = self.db["vibe_user_answers"]
        now = datetime.now(timezone.utc)
        active_threshold = now - timedelta(minutes=5)
        
        results = []
        for c in connection_docs:
            p_id = c["partner_id"]
            p_profile = profile_map.get(p_id, {})
            
            # Online status check
            is_online = False
            p_updated = p_profile.get("updated_at")
            if p_updated:
                if p_updated.tzinfo is None:
                    p_updated = p_updated.replace(tzinfo=timezone.utc)
                if p_updated >= active_threshold:
                    is_online = True
                    
            # Pending questions check
            current_day = c.get("current_journey_day", 1)
            p_ans_doc = await user_answers_col.find_one({
                "user_id": p_id,
                "partner_id": user_id,
                "journey_day": current_day
            })
            answers_count = len(p_ans_doc.get("answers", [])) if p_ans_doc else 0
            pending_questions = max(0, 3 - answers_count)
            
            results.append({
                "user_id": p_id,
                "name": p_profile.get("name", "Unknown User"),
                "connected_at": c["connected_at"],
                "profile_picture": p_profile.get("profile_picture"),
                "is_online": is_online,
                "pending_questions": pending_questions,
                "current_journey_day": current_day
            })
        return results

    async def connect_with_partner(self, user_id: str, vibe_key: str) -> Dict[str, Any]:
        """Create a pending connection request using a Vibe Key."""
        # 1. Fetch initiator profile
        initiator = await self.profiles.find_one({"user_id": user_id})
        if not initiator:
            raise ValueError("Your VibeCheck profile is not setup.")

        # 2. Fetch target profile
        target = await self.profiles.find_one({"vibe_key": vibe_key})
        if not target:
            raise ValueError("User with this Vibe Key not found.")
            
        if not target.get("vibe_key_enabled", True):
            raise ValueError("This user has disabled new connections via Vibe Key.")
            
        if target["user_id"] == user_id:
            raise ValueError("You cannot connect with yourself.")

        # 3. Check if already connected
        existing_conn = await self.connections.find_one({"user_id": user_id, "partner_id": target["user_id"]})
        if existing_conn:
            raise ValueError(f"You are already connected with {target['name']}.")

        now = datetime.now(timezone.utc)
        
        # 4. Check if a request already exists
        existing_request = await self.requests.find_one({
            "sender_id": user_id, 
            "recipient_id": target["user_id"]
        })
        if existing_request:
            raise ValueError(f"You have already sent a request to {target['name']}.")

        # 5. Check if they already sent us a request
        reverse_request = await self.requests.find_one({
            "sender_id": target["user_id"], 
            "recipient_id": user_id
        })
        if reverse_request:
            raise ValueError(f"{target['name']} has already sent you a request. Please approve it from your requests panel.")

        from pymongo.errors import DuplicateKeyError
        try:
            res = await self.requests.insert_one({
                "sender_id": user_id,
                "sender_name": initiator["name"],
                "recipient_id": target["user_id"],
                "recipient_name": target["name"],
                "created_at": now
            })
            request_id = str(res.inserted_id)
        except DuplicateKeyError:
            raise ValueError(f"You have already sent a request to {target['name']}.")

        from app.services.notification import notification_service
        from app.schemas.notification import NotificationCreate, NotificationType
        
        await notification_service.schedule_notification(
            sender_id=initiator["user_id"],
            payload=NotificationCreate(
                recipient_id=target["user_id"],
                title="New Vibe Check Request",
                message=f"{initiator['name']} wants to connect with you on VibeCheck! Tap to accept or reject.",
                type=NotificationType.VIBE_SYSTEM,
                metadata={
                    "type": "vibe_check_request",
                    "request_id": request_id,
                    "sender_id": initiator["user_id"],
                    "sender_name": initiator["name"],
                    "sender_picture": initiator.get("profile_picture")
                }
            )
        )

        return {"success": True, "message": f"Connection request sent to {target['name']}!"}

    async def get_pending_requests(self, user_id: str) -> List[Dict[str, Any]]:
        """List all pending connection requests for this user (incoming and outgoing)."""
        cursor = self.requests.find({
            "$or": [
                {"recipient_id": user_id},
                {"sender_id": user_id}
            ]
        })
        docs = await cursor.to_list(length=None)
        
        results = []
        for d in docs:
            direction = "incoming" if d["recipient_id"] == user_id else "outgoing"
            results.append({
                "request_id": str(d["_id"]),
                "sender_id": d["sender_id"],
                "sender_name": d["sender_name"],
                "recipient_id": d["recipient_id"],
                "recipient_name": d.get("recipient_name", "Unknown"),
                "type": d.get("type"),
                "direction": direction,
                "created_at": d["created_at"]
            })
        return results

    async def respond_to_request(self, user_id: str, request_id: str, accept: bool) -> Dict[str, Any]:
        """Accept or reject a pending connection request."""
        request = await self.requests.find_one({"_id": ObjectId(request_id), "recipient_id": user_id})
        if not request:
            raise ValueError("Request not found.")

        if accept:
            now = datetime.now(timezone.utc)
            # Create mutual connections
            # Recipient -> Sender
            await self.connections.update_one(
                {"user_id": user_id, "partner_id": request["sender_id"]},
                {"$setOnInsert": {
                    "user_id": user_id, 
                    "partner_id": request["sender_id"], 
                    "connected_at": now,
                    "current_journey_day": 1,
                    "status": "active",
                    "stalled_since": None,
                    "silent_partner_id": None
                }},
                upsert=True
            )
            # Sender -> Recipient
            await self.connections.update_one(
                {"user_id": request["sender_id"], "partner_id": user_id},
                {"$setOnInsert": {
                    "user_id": request["sender_id"], 
                    "partner_id": user_id, 
                    "connected_at": now,
                    "current_journey_day": 1,
                    "status": "active",
                    "stalled_since": None,
                    "silent_partner_id": None
                }},
                upsert=True
            )
            message = "Connection accepted."
            
            # Send Push Notification and WebSocket event to the original sender
            from app.services.notification import notification_service
            from app.schemas.notification import NotificationCreate, NotificationType
            from app.core.websocket import ws_manager
            
            # Find the recipient's profile to get their name
            recipient_profile = await self.profiles.find_one({"user_id": user_id})
            recipient_name = recipient_profile.get("name", "Someone") if recipient_profile else "Someone"

            await notification_service.schedule_notification(
                sender_id=user_id,
                payload=NotificationCreate(
                    recipient_id=request["sender_id"],
                    title="Request Accepted!",
                    message=f"{recipient_name} accept your vibe connection",
                    type=NotificationType.VIBE_SYSTEM,
                    metadata={
                        "type": "vibe_check_accepted",
                        "partner_id": user_id
                    }
                )
            )
            
            await ws_manager.broadcast_to_user(
                request["sender_id"], 
                {"type": "VIBE_CONNECTION_UPDATED"}
            )
            
        else:
            message = "Connection request rejected."

        # Delete the request
        await self.requests.delete_one({"_id": ObjectId(request_id)})
        
        return {"success": True, "message": message}

    async def delete_connection(self, user_id: str, partner_id: str) -> bool:
        """Remove a mutual connection between two users and wipe all associated data."""
        res1 = await self.connections.delete_one({"user_id": user_id, "partner_id": partner_id})
        res2 = await self.connections.delete_one({"user_id": partner_id, "partner_id": user_id})
        
        if res1.deleted_count > 0 or res2.deleted_count > 0:
            # Wipe all data exactly like reset
            flags_coll = self.db["vibe_flags"]
            await flags_coll.delete_many({"user_id": user_id, "target_id": partner_id})
            await flags_coll.delete_many({"user_id": partner_id, "target_id": user_id})
            
            pulse_coll = self.db["vibe_pulse"]
            await pulse_coll.delete_many({"user_id": user_id, "partner_id": partner_id})
            await pulse_coll.delete_many({"user_id": partner_id, "partner_id": user_id})
            
            dates_coll = self.db["vibe_dates"]
            await dates_coll.delete_many({"$or": [
                {"proposer_id": user_id, "partner_id": partner_id},
                {"proposer_id": partner_id, "partner_id": user_id}
            ]})
            
            answers_coll = self.db["vibe_user_answers"]
            await answers_coll.delete_many({"user_id": user_id, "partner_id": partner_id})
            await answers_coll.delete_many({"user_id": partner_id, "partner_id": user_id})
            
            scores_coll = self.db["vibe_cumulative_scores"]
            await scores_coll.delete_many({"user_id": user_id, "partner_id": partner_id})
            await scores_coll.delete_many({"user_id": partner_id, "partner_id": user_id})
            
            # Send Notification to partner
            from app.services.notification import notification_service
            from app.schemas.notification import NotificationCreate, NotificationType
            from app.core.websocket import ws_manager
            
            initiator_profile = await self.get_profile(user_id)
            initiator_name = initiator_profile["name"] if initiator_profile else "Someone"
            
            await notification_service.schedule_notification(
                sender_id=user_id,
                payload=NotificationCreate(
                    recipient_id=partner_id,
                    title="Connection Broken",
                    message=f"{initiator_name} is breaking your vibe connection",
                    type=NotificationType.VIBE_SYSTEM,
                    metadata={"type": "vibe_check_connection_broken"}
                )
            )
            
            # Broadcast to both users to wipe local cache
            await ws_manager.broadcast_to_user(user_id, {"type": "VIBE_CONNECTION_UPDATED"})
            await ws_manager.broadcast_to_user(partner_id, {"type": "VIBE_CONNECTION_UPDATED"})
            
            return True
            
        return False

    async def request_reset_connection(self, user_id: str, partner_id: str) -> Dict[str, Any]:
        """Send a reset request to the partner."""
        conn = await self.connections.find_one({"user_id": user_id, "partner_id": partner_id})
        if not conn:
            raise ValueError("Connection not found.")
            
        initiator = await self.get_profile(user_id)
        
        req = {
            "$set": {
                "sender_name": initiator["name"],
                "type": "reset_connection",
                "created_at": datetime.now(timezone.utc)
            }
        }
        # Use upsert to handle potential race conditions from button mashing
        await self.requests.update_one(
            {
                "sender_id": user_id,
                "recipient_id": partner_id
            },
            req,
            upsert=True
        )
        
        from app.services.notification import notification_service
        from app.schemas.notification import NotificationCreate, NotificationType
        from app.core.websocket import ws_manager
        
        await notification_service.schedule_notification(
            sender_id=user_id,
            payload=NotificationCreate(
                recipient_id=partner_id,
                title="Connection Reset Request",
                message=f"{initiator['name']} wants to reset your Vibe journey to Day 1.",
                type=NotificationType.VIBE_SYSTEM,
                metadata={
                    "type": "vibe_check_reset_request",
                    "request_id": str(res.inserted_id)
                }
            )
        )
        
        await ws_manager.broadcast_to_user(partner_id, {"type": "NEW_NOTIFICATION"})
        
        return {"success": True, "message": "Reset request sent."}

    async def respond_reset_connection(self, user_id: str, request_id: str, accept: bool) -> Dict[str, Any]:
        req = await self.requests.find_one({"_id": ObjectId(request_id), "recipient_id": user_id, "type": "reset_connection"})
        if not req:
            raise ValueError("Reset request not found.")
            
        if accept:
            partner_id = req["sender_id"]
            now = datetime.now(timezone.utc)
            update = {"$set": {"current_journey_day": 1, "connected_at": now}}
            await self.connections.update_one({"user_id": user_id, "partner_id": partner_id}, update)
            await self.connections.update_one({"user_id": partner_id, "partner_id": user_id}, update)
            
            flags_coll = self.db["vibe_flags"]
            await flags_coll.delete_many({"user_id": user_id, "target_id": partner_id})
            await flags_coll.delete_many({"user_id": partner_id, "target_id": user_id})
            
            pulse_coll = self.db["vibe_pulse"]
            await pulse_coll.update_one(
                {"user_id": user_id, "partner_id": partner_id},
                {"$set": {"status": "TALKING", "updated_at": now}}
            )
            await pulse_coll.update_one(
                {"user_id": partner_id, "partner_id": user_id},
                {"$set": {"status": "TALKING", "updated_at": now}}
            )
            
            dates_coll = self.db["vibe_dates"]
            await dates_coll.delete_many({"$or": [
                {"proposer_id": user_id, "partner_id": partner_id},
                {"proposer_id": partner_id, "partner_id": user_id}
            ]})
            
            answers_coll = self.db["vibe_user_answers"]
            await answers_coll.delete_many({"user_id": user_id, "partner_id": partner_id})
            await answers_coll.delete_many({"user_id": partner_id, "partner_id": user_id})
            
            scores_coll = self.db["vibe_cumulative_scores"]
            await scores_coll.delete_many({"user_id": user_id, "partner_id": partner_id})
            await scores_coll.delete_many({"user_id": partner_id, "partner_id": user_id})
            
            message = "Connection reset successfully."
            
            from app.services.notification import notification_service
            from app.schemas.notification import NotificationCreate, NotificationType
            from app.core.websocket import ws_manager
            
            recipient_profile = await self.get_profile(user_id)
            await notification_service.schedule_notification(
                sender_id=user_id,
                payload=NotificationCreate(
                    recipient_id=partner_id,
                    title="Reset Accepted",
                    message=f"{recipient_profile['name']} accepted the reset. Welcome to Day 1!",
                    type=NotificationType.VIBE_SYSTEM,
                    metadata={"type": "vibe_check_reset_accepted", "partner_id": user_id}
                )
            )
            await ws_manager.broadcast_to_user(partner_id, {"type": "VIBE_CONNECTION_UPDATED"})
            
        else:
            message = "Reset request rejected."
            
        await self.requests.delete_one({"_id": ObjectId(request_id)})
        return {"success": True, "message": message}

    async def regenerate_vibe_key(self, user_id: str) -> str:
        """Generate a new unique vibe key for the user."""
        new_key = await self.generate_unique_vibe_key()
        result = await self.profiles.update_one(
            {"user_id": user_id},
            {"$set": {"vibe_key": new_key, "updated_at": datetime.now(timezone.utc)}}
        )
        if result.matched_count == 0:
            raise ValueError("VibeCheck profile not found.")
        return new_key

    # --- Invite System ---

    async def generate_invite(self, user_id: str) -> VibeInviteResponse:
        """Generates a secure unique invite code and link."""
        # Check if user has a profile
        profile = await self.get_profile(user_id)
        if not profile:
            raise ValueError("Your VibeCheck profile is not setup.")

        # Rate limiting: Check if user has generated too many invites recently (optional, but requested)
        # For simplicity, let's just limit to 10 active invites per user
        active_count = await self.invites.count_documents({
            "inviter_id": user_id, 
            "status": "pending", 
            "expires_at": {"$gt": datetime.now(timezone.utc)}
        })
        if active_count >= 10:
            raise ValueError("You have too many active invites. Please wait for them to expire or be used.")

        while True:
            invite_code = "".join(random.choices(string.ascii_uppercase + string.digits, k=10))
            existing = await self.invites.find_one({"invite_code": invite_code})
            if not existing:
                break
        
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=30)
        
        invite_doc = {
            "invite_code": invite_code,
            "inviter_id": user_id,
            "inviter_name": profile["name"],
            "created_at": now,
            "expires_at": expires_at,
            "status": "pending",
            "used_by": None,
            "used_at": None
        }
        await self.invites.insert_one(invite_doc)
        
        invite_link = f"{settings.FRONTEND_URL}/invite/{invite_code}"
        
        return VibeInviteResponse(invite_code=invite_code, invite_link=invite_link)

    async def validate_invite(self, invite_code: str) -> VibeInviteValidateResponse:
        """Verify invite exists and is not expired."""
        invite = await self.invites.find_one({"invite_code": invite_code})
        if not invite:
            return VibeInviteValidateResponse(valid=False, inviter_name="")
            
        now = datetime.now(timezone.utc)
        expires_at = invite["expires_at"]
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if invite["status"] != "pending" or expires_at < now:
            return VibeInviteValidateResponse(valid=False, inviter_name=invite["inviter_name"])
            
        return VibeInviteValidateResponse(
            valid=True, 
            inviter_name=invite["inviter_name"],
            inviter_profile_picture=invite.get("inviter_profile_picture")
        )

    async def accept_invite(self, user_id: str, invite_code: str) -> VibeInviteAcceptResponse:
        """Accept an invite and create connection."""
        invite = await self.invites.find_one({"invite_code": invite_code})
        if not invite:
            raise ValueError("Invalid invite code.")
            
        if invite["inviter_id"] == user_id:
            raise ValueError("You cannot accept your own invite.")
            
        now = datetime.now(timezone.utc)
        expires_at = invite["expires_at"]
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if invite["status"] != "pending" or expires_at < now:
            raise ValueError("Invite has expired or already been used.")
            
        # Ensure user has a profile
        me = await self.get_profile(user_id)
        if not me:
            raise ValueError("Your VibeCheck profile is not setup. Please setup your profile first.")

        # Ensure not already connected
        existing_conn = await self.connections.find_one({"user_id": user_id, "partner_id": invite["inviter_id"]})
        if existing_conn:
            # Mark invite as used anyway if they are already connected? 
            # Or just throw error. Usually better to throw error.
            raise ValueError("You are already connected with this user.")

        # Create mutual connections
        # Me -> Inviter
        await self.connections.update_one(
            {"user_id": user_id, "partner_id": invite["inviter_id"]},
            {"$setOnInsert": {
                "user_id": user_id, 
                "partner_id": invite["inviter_id"], 
                "connected_at": now,
                "current_journey_day": 1,
                "status": "active",
                "stalled_since": None,
                "silent_partner_id": None
            }},
            upsert=True
        )
        # Inviter -> Me
        await self.connections.update_one(
            {"user_id": invite["inviter_id"], "partner_id": user_id},
            {"$setOnInsert": {
                "user_id": invite["inviter_id"], 
                "partner_id": user_id, 
                "connected_at": now,
                "current_journey_day": 1,
                "status": "active",
                "stalled_since": None,
                "silent_partner_id": None
            }},
            upsert=True
        )
        
        # Mark invite as used
        await self.invites.update_one(
            {"invite_code": invite_code},
            {"$set": {
                "status": "used",
                "used_by": user_id,
                "used_at": now
            }}
        )
        
        return VibeInviteAcceptResponse(
            success=True, 
            message=f"You are now connected with {invite['inviter_name']}!",
            partner_id=invite["inviter_id"],
            partner_name=invite["inviter_name"]
        )

    # --- Profile Management ---

    async def update_profile(self, user_id: str, name: Optional[str] = None) -> Dict[str, Any]:
        """Update the user's VibeCheck profile name."""
        existing = await self.profiles.find_one({"user_id": user_id})
        if not existing:
            raise ValueError("VibeCheck profile not found.")
        
        update_data = {"updated_at": datetime.now(timezone.utc)}
        if name is not None and name.strip():
            update_data["name"] = name.strip()
        
        await self.profiles.update_one(
            {"user_id": user_id},
            {"$set": update_data}
        )
        return await self.get_profile(user_id)

    async def update_profile_picture(self, user_id: str, file_path: str) -> Dict[str, Any]:
        """Save or update profile picture path for the user."""
        existing = await self.profiles.find_one({"user_id": user_id})
        if not existing:
            raise ValueError("VibeCheck profile not found.")
        
        # Delete old file if exists
        old_path = existing.get("profile_picture")
        if old_path:
            import os
            if os.path.exists(old_path):
                os.remove(old_path)
        
        await self.profiles.update_one(
            {"user_id": user_id},
            {"$set": {"profile_picture": file_path, "updated_at": datetime.now(timezone.utc)}}
        )
        return await self.get_profile(user_id)

    async def delete_profile_picture(self, user_id: str) -> Dict[str, Any]:
        """Remove profile picture for the user."""
        existing = await self.profiles.find_one({"user_id": user_id})
        if not existing:
            raise ValueError("VibeCheck profile not found.")
        
        old_path = existing.get("profile_picture")
        if old_path:
            import os
            if os.path.exists(old_path):
                os.remove(old_path)
        
        await self.profiles.update_one(
            {"user_id": user_id},
            {"$set": {"profile_picture": None, "updated_at": datetime.now(timezone.utc)}}
        )
        return {"success": True, "message": "Profile picture removed."}

    async def delete_profile(self, user_id: str) -> Dict[str, Any]:
        """Delete the user's entire VibeCheck profile and all related data."""
        existing = await self.profiles.find_one({"user_id": user_id})
        if not existing:
            raise ValueError("VibeCheck profile not found.")
        
        # Delete profile picture file if exists
        old_path = existing.get("profile_picture")
        if old_path:
            import os
            if os.path.exists(old_path):
                os.remove(old_path)
        
        # Delete all connections (both directions)
        await self.connections.delete_many({"user_id": user_id})
        await self.connections.delete_many({"partner_id": user_id})
        
        # Delete all pending requests (both sent and received)
        await self.requests.delete_many({"sender_id": user_id})
        await self.requests.delete_many({"recipient_id": user_id})
        
        # Delete all invites
        await self.invites.delete_many({"inviter_id": user_id})
        
        # Delete cumulative scores
        await self.cumulative_scores.delete_many({"user_id": user_id})
        await self.cumulative_scores.delete_many({"partner_id": user_id})
        
        # Delete streaks
        await self.user_streaks.delete_many({"user_id": user_id})
        
        # Delete the profile itself
        await self.profiles.delete_one({"user_id": user_id})
        
        return {"success": True, "message": "VibeCheck profile and all related data deleted."}

    async def release_connection(self, user_id: str, partner_id: str) -> Dict[str, Any]:
        """Release a connection (e.g. after silent anchor wait)."""
        now = datetime.now(timezone.utc)
        await self.connections.update_many(
            {"$or": [
                {"user_id": user_id, "partner_id": partner_id},
                {"user_id": partner_id, "partner_id": user_id}
            ]},
            {"$set": {"status": "released", "released_at": now}}
        )
        return {"success": True, "message": "Connection released."}

    async def restore_connection(self, user_id: str, partner_id: str) -> Dict[str, Any]:
        """Restore a released connection within 30 days."""
        # Check if released_at is within 30 days
        conn = await self.connections.find_one({"user_id": user_id, "partner_id": partner_id})
        if not conn:
            raise ValueError("Connection not found.")
            
        if conn.get("status") == "active":
            return {"success": True, "message": "Connection is already active."}
            
        released_at = conn.get("released_at")
        if released_at:
            if released_at.tzinfo is None:
                released_at = released_at.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) - released_at > timedelta(days=30):
                raise ValueError("Cannot restore connection after 30 days of release.")
                
        await self.connections.update_many(
            {"$or": [
                {"user_id": user_id, "partner_id": partner_id},
                {"user_id": partner_id, "partner_id": user_id}
            ]},
            {"$set": {"status": "active", "stalled_since": None, "silent_partner_id": None}}
        )
        return {"success": True, "message": "Connection restored."}

    async def get_sync_summary(self, user_id: str, timezone_str: str = "UTC", partner_id: Optional[str] = None) -> Dict[str, Any]:
        """Calculates the combined Sync score for the user and their partner."""
        # 1. Find partner
        profile = await self.get_profile(user_id)
        if not profile:
            raise ValueError("VibeCheck profile not found.")
            
        if not partner_id:
            conn = await self.connections.find_one({"user_id": user_id})
            if conn:
                partner_id = conn["partner_id"]
            
        user_ids = [user_id]
        if partner_id:
            user_ids.append(partner_id)
            
        # Time range: Last 7 days
        import zoneinfo
        try:
            tz = zoneinfo.ZoneInfo(timezone_str)
        except Exception:
            tz = zoneinfo.ZoneInfo("UTC")
            
        now = datetime.now(timezone.utc)
        seven_days_ago = now - timedelta(days=7)
        
        # We need collections from other services, so we'll access db directly
        rituals_coll = self.db["ritual_completions"]
        checkins_coll = self.db["check_ins"]
        messages_coll = self.db["thread_messages"]
        
        # Dates for check_ins which uses string dates "YYYY-MM-DD"
        local_now = now.astimezone(tz)
        dates_to_check = [(local_now - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
        
        # 1. Rituals (in last 7 days)
        # Note: ritual_completions stores created_at as datetime
        rituals_count = await rituals_coll.count_documents({
            "user_id": {"$in": user_ids},
            "created_at": {"$gte": seven_days_ago}
        })
        
        # 2. Check-ins
        checkins_count = await checkins_coll.count_documents({
            "user_id": {"$in": user_ids},
            "date": {"$in": dates_to_check}
        })
        
        # 3. Appreciations (Thread messages with category Appreciation)
        appreciations_count = await messages_coll.count_documents({
            "creator_id": {"$in": user_ids},
            "category": "Appreciation",
            "created_at": {"$gte": seven_days_ago}
        })
        
        # 4. Threads (Any Thread message)
        threads_count = await messages_coll.count_documents({
            "creator_id": {"$in": user_ids},
            "created_at": {"$gte": seven_days_ago}
        })
        
        # Max targets
        target = 7
        
        r_perc = min(int((rituals_count / target) * 100), 100)
        c_perc = min(int((checkins_count / target) * 100), 100)
        a_perc = min(int((appreciations_count / target) * 100), 100)
        t_perc = min(int((threads_count / target) * 100), 100)
        
        # Weighted overall score
        # Rituals: 30%, Check-ins: 30%, Appreciations: 20%, Threads: 20%
        overall = int((r_perc * 0.30) + (c_perc * 0.30) + (a_perc * 0.20) + (t_perc * 0.20))
        
        return {
            "overall_score": overall,
            "rituals": {"count": rituals_count, "target": target, "percentage": r_perc},
            "checkins": {"count": checkins_count, "target": target, "percentage": c_perc},
            "appreciations": {"count": appreciations_count, "target": target, "percentage": a_perc},
            "threads": {"count": threads_count, "target": target, "percentage": t_perc}
        }

vibe_check_service = VibeCheckService()
