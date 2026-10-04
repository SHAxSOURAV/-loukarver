import random
import string
from typing import List, Dict, Any
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.db import get_client, get_db

from app.core.config import settings
from app.schemas.relationships import RelationshipCreate
from app.services.notification import notification_service
from app.schemas.notification import NotificationCreate, NotificationType, PresenceCreate
from app.core.websocket import ws_manager

class RelationshipService:
    def __init__(self) -> None:
        self.client = get_client()
        self.db = get_db()
        self.collection = self.db["users"]
        self.requests_collection = self.db["alignment_requests"]

    async def init_indexes(self):
        """Initializes database indexes for high-speed queries on users, requests, checkins, rituals, and threads."""
        index_specs = [
            (self.collection, "email", {}),
            (self.collection, "secret_key", {}),
            (self.collection, "partner.user_id", {"sparse": True}),
            (self.requests_collection, [("receiver_id", 1), ("status", 1)], {}),
            (self.requests_collection, [("sender_id", 1), ("status", 1)], {}),
            (self.requests_collection, [("created_at", -1)], {}),
            (self.db["check_ins"], [("user_id", 1), ("created_at", -1)], {}),
            (self.db["check_ins"], [("user_id", 1), ("date", 1)], {}),
            (self.db["ritual_completions"], [("user_id", 1), ("created_at", -1)], {}),
            (self.db["ritual_completions"], [("user_id", 1), ("ritual_type", 1), ("created_at", -1)], {}),
            (self.db["thread_messages"], [("creator_id", 1), ("created_at", -1)], {}),
            (self.db["thread_messages"], [("creator_id", 1), ("category", 1), ("created_at", -1)], {})
        ]
        for coll, spec, kwargs in index_specs:
            try:
                await coll.create_index(spec, **kwargs)
            except Exception as e:
                print(f"[Index Note] Could not create index on {coll.name} {spec}: {e}")

    async def get_all_relationships(self) -> List[Dict[str, Any]]:
        """Retrieves all registered relationships from the MongoDB collection."""
        try:
            cursor = self.collection.find({})
            results = await cursor.to_list(length=None)
            # Convert ObjectId _id to string for JSON serialization compatibility
            for result in results:
                if "_id" in result:
                    result["id"] = str(result["_id"])
                    result["_id"] = str(result["_id"])
            return results
        except Exception as e:
            raise e

    async def generate_unique_secret_key(self) -> str:
        """Generates a unique 16-character secret key like ALIGNED-Y8BSV1AB."""
        while True:
            random_part = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
            secret_key = f"ALIGNED-{random_part}"
            
            # Check uniqueness in MongoDB
            existing = await self.collection.find_one({"secret_key": secret_key})
            if not existing:
                return secret_key

    async def save_relationship(self, relationship: RelationshipCreate) -> Dict[str, Any]:
        """Saves a new relationship to MongoDB with a unique secret key."""
        secret_key = await self.generate_unique_secret_key()
        
        new_data = {
            "name": relationship.name,
            "city_name": relationship.city_name,
            "relationship_start_date": relationship.relationship_start_date,
            "is_long_distance": relationship.is_long_distance,
            "gender": getattr(relationship, "gender", "Not to say"),
            "secret_key": secret_key,
            "is_aligned": False,
            "partner": None
        }
        
        await self.collection.insert_one(new_data)
        
        # Convert ObjectId _id to string for serializability
        if "_id" in new_data:
            new_data["id"] = str(new_data["_id"])
            new_data["_id"] = str(new_data["_id"])
            
        return new_data

    async def create_alignment_request(self, user_id: str, partner_secret_key: str) -> Dict[str, Any]:
        """Creates a pending alignment connection request to the partner identified by secret key."""
        from bson import ObjectId
        
        # 1. Fetch initiator
        initiator = await self.collection.find_one({"_id": ObjectId(user_id)})
        if not initiator:
            raise ValueError("User not found.")
            
        if initiator.get("is_aligned"):
            raise ValueError("You are already connected to a partner.")

        # 2. Fetch partner by secret key
        clean_key = partner_secret_key.strip().upper()
        partner = await self.collection.find_one({"secret_key": clean_key})
        if not partner:
            raise ValueError("Partner with specified secret key not found.")
            
        if partner.get("is_aligned"):
            raise ValueError("The partner is already connected to another user.")
            
        if partner.get("secret_key_enabled") is False:
            raise ValueError("Partner's secret key is currently disabled.")
            
        if str(initiator["_id"]) == str(partner["_id"]):
            raise ValueError("Cannot connect to your own secret key.")

        # 3. Check existing active pending requests
        existing_to_partner = await self.requests_collection.find_one({
            "sender_id": user_id,
            "receiver_id": str(partner["_id"]),
            "status": "pending"
        })
        if existing_to_partner:
            existing_to_partner["id"] = str(existing_to_partner["_id"])
            existing_to_partner["_id"] = str(existing_to_partner["_id"])
            return existing_to_partner

        existing_active = await self.requests_collection.find_one({
            "$or": [
                {"sender_id": user_id, "status": "pending"},
                {"receiver_id": user_id, "status": "pending"},
                {"sender_id": str(partner["_id"]), "status": "pending"},
                {"receiver_id": str(partner["_id"]), "status": "pending"},
            ]
        })
        
        if existing_active:
            if existing_active.get("sender_id") == user_id and existing_active.get("receiver_id") == str(partner["_id"]):
                existing_active["id"] = str(existing_active["_id"])
                existing_active["_id"] = str(existing_active["_id"])
                return existing_active
            elif existing_active.get("sender_id") == str(partner["_id"]) and existing_active.get("receiver_id") == user_id:
                # Partner had already sent a request to this user! Auto-accept mutually!
                return await self.respond_alignment_request(user_id=user_id, request_id=str(existing_active["_id"]), accept=True)
            elif existing_active.get("sender_id") == user_id:
                # Cancel previous outgoing request to other user and create new
                await self.requests_collection.update_many(
                    {"sender_id": user_id, "status": "pending"},
                    {"$set": {"status": "cancelled", "updated_at": datetime.now(timezone.utc)}}
                )

        # 4. Create new request doc
        now = datetime.now(timezone.utc)
        req_doc = {
            "sender_id": user_id,
            "sender_name": initiator.get("name", "Partner"),
            "sender_city": initiator.get("city_name", ""),
            "sender_profile_photo": initiator.get("profile_photo_url"),
            "receiver_id": str(partner["_id"]),
            "receiver_name": partner.get("name", "Partner"),
            "status": "pending",
            "created_at": now,
            "updated_at": now
        }
        res = await self.requests_collection.insert_one(req_doc)
        req_doc["_id"] = str(res.inserted_id)
        req_doc["id"] = str(res.inserted_id)

        # 5. Send notification to partner
        try:
            await notification_service.create_notification(
                NotificationCreate(
                    recipient_id=str(partner["_id"]),
                    type=NotificationType.RELATIONSHIP_REQUEST,
                    title="Alignment Request",
                    message=f"{initiator.get('name', 'Someone')} sent you an alignment request to connect.",
                    metadata={"request_id": req_doc["id"], "sender_name": initiator.get("name")}
                )
            )
        except Exception as e:
            print("Failed to send alignment request push notification:", e)

        # 6. Broadcast real-time WebSocket events
        try:
            await ws_manager.broadcast_to_user(
                user_id=str(partner["_id"]),
                message={
                    "type": "ALIGNMENT_REQUEST_RECEIVED",
                    "request_id": req_doc["id"],
                    "sender_name": initiator.get("name", "Partner"),
                    "sender_city": initiator.get("city_name", ""),
                    "sender_profile_photo": initiator.get("profile_photo_url")
                }
            )
            await ws_manager.broadcast_to_user(
                user_id=user_id,
                message={
                    "type": "ALIGNMENT_REQUEST_SENT",
                    "request_id": req_doc["id"],
                    "receiver_name": partner.get("name", "Partner")
                }
            )
        except Exception as e:
            print("Failed to broadcast ws event:", e)

        return req_doc

    async def get_alignment_request_status(self, user_id: str, user: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Gets active incoming and outgoing alignment requests for a user with comprehensive state cleanup."""
        from bson import ObjectId
        import asyncio

        # 1. Check if user is already aligned
        if not user:
            user = await self.collection.find_one({"_id": ObjectId(user_id)})
        if not user or user.get("is_aligned"):
            # If user is already aligned, clean up any lingering pending requests in the background
            await self.requests_collection.update_many(
                {
                    "status": "pending",
                    "$or": [{"sender_id": user_id}, {"receiver_id": user_id}]
                },
                {"$set": {"status": "cancelled", "updated_at": datetime.now(timezone.utc)}}
            )
            return {"is_aligned": True, "incoming": None, "incoming_list": [], "outgoing": None}

        now = datetime.now(timezone.utc)

        # 2 & 3. Concurrently fetch incoming and outgoing pending requests
        incoming_task = self.requests_collection.find({
            "receiver_id": user_id,
            "status": "pending"
        }).sort("created_at", -1).to_list(length=50)

        outgoing_task = self.requests_collection.find_one({
            "sender_id": user_id,
            "status": "pending"
        })

        raw_incoming, outgoing = await asyncio.gather(incoming_task, outgoing_task)

        # Batch lookup all related user records (senders of incoming requests + receiver of outgoing request)
        related_ids = set()
        for inc in (raw_incoming or []):
            s_id = inc.get("sender_id")
            if s_id and ObjectId.is_valid(s_id):
                related_ids.add(ObjectId(s_id))
        if outgoing:
            r_id = outgoing.get("receiver_id")
            if r_id and ObjectId.is_valid(r_id):
                related_ids.add(ObjectId(r_id))

        users_map = {}
        if related_ids:
            docs = await self.collection.find({"_id": {"$in": list(related_ids)}}).to_list(length=len(related_ids))
            users_map = {str(d["_id"]): d for d in docs}

        valid_incoming = []
        seen_senders = set()
        stale_request_ids = []

        for inc in (raw_incoming or []):
            inc["id"] = str(inc["_id"])
            inc["_id"] = str(inc["_id"])
            s_id = str(inc.get("sender_id"))

            if s_id in seen_senders:
                stale_request_ids.append(ObjectId(inc["id"]))
                continue

            s = users_map.get(s_id)
            if s:
                if s.get("is_aligned"):
                    stale_request_ids.append(ObjectId(inc["id"]))
                    continue
                inc["sender_name"] = s.get("name", inc.get("sender_name"))
                inc["sender_profile_photo"] = s.get("profile_photo_url")
                inc["sender_city"] = s.get("city_name")
                if "created_at" in inc and hasattr(inc["created_at"], "isoformat"):
                    inc["created_at"] = inc["created_at"].isoformat()
                seen_senders.add(s_id)
                valid_incoming.append(inc)

        if outgoing:
            outgoing["id"] = str(outgoing["_id"])
            outgoing["_id"] = str(outgoing["_id"])
            r_id = str(outgoing.get("receiver_id"))
            r = users_map.get(r_id)
            if r:
                if r.get("is_aligned"):
                    stale_request_ids.append(ObjectId(outgoing["id"]))
                    outgoing = None
                else:
                    outgoing["receiver_name"] = r.get("name", outgoing.get("receiver_name"))
                    outgoing["receiver_profile_photo"] = r.get("profile_photo_url")

        # Cleanup any stale requests in one go
        if stale_request_ids:
            await self.requests_collection.update_many(
                {"_id": {"$in": stale_request_ids}},
                {"$set": {"status": "cancelled", "updated_at": now}}
            )

        return {
            "is_aligned": False,
            "incoming": valid_incoming[0] if valid_incoming else None,
            "incoming_list": valid_incoming,
            "outgoing": outgoing
        }

    async def respond_alignment_request(self, user_id: str, request_id: str, accept: bool) -> Dict[str, Any]:
        """Approves or declines an incoming alignment request with strict concurrency and multi-request cleanup."""
        from bson import ObjectId
        
        req = await self.requests_collection.find_one({"_id": ObjectId(request_id)})
        if not req:
            raise ValueError("Alignment request not found.")
            
        if req.get("receiver_id") != user_id:
            raise ValueError("You are not authorized to respond to this request.")
            
        if req.get("status") != "pending":
            raise ValueError(f"This request is no longer active (status: {req.get('status')}).")

        now = datetime.now(timezone.utc)
        sender_id = req["sender_id"]

        if accept:
            # 1. Fetch initiator and receiver
            sender = await self.collection.find_one({"_id": ObjectId(sender_id)})
            receiver = await self.collection.find_one({"_id": ObjectId(user_id)})

            if not sender or not receiver:
                raise ValueError("User accounts not found.")
                
            if sender.get("is_aligned"):
                # Mark request cancelled
                await self.requests_collection.update_one(
                    {"_id": ObjectId(request_id)},
                    {"$set": {"status": "cancelled", "updated_at": now}}
                )
                raise ValueError(f"{sender.get('name', 'This user')} is already aligned with another partner.")
                
            if receiver.get("is_aligned"):
                await self.requests_collection.update_many(
                    {"receiver_id": user_id, "status": "pending"},
                    {"$set": {"status": "cancelled", "updated_at": now}}
                )
                raise ValueError("You are already connected to a partner.")

            # 2. Mutually bond both users
            today_str = now.strftime("%m.%d.%Y")

            await self.collection.update_one(
                {"_id": sender["_id"]},
                {
                    "$set": {
                        "is_aligned": True,
                        "aligned_at": now,
                        "relationship_start_date": today_str,
                        "secret_key": None,
                        "partner": {
                            "user_id": str(receiver["_id"]),
                            "name": receiver["name"],
                            "city_name": receiver.get("city_name", ""),
                            "relationship_start_date": today_str,
                            "is_long_distance": receiver.get("is_long_distance", False),
                            "gender": receiver.get("gender", "Not to say"),
                            "profile_photo_url": receiver.get("profile_photo_url")
                        }
                    }
                }
            )

            await self.collection.update_one(
                {"_id": receiver["_id"]},
                {
                    "$set": {
                        "is_aligned": True,
                        "aligned_at": now,
                        "relationship_start_date": today_str,
                        "secret_key": None,
                        "partner": {
                            "user_id": str(sender["_id"]),
                            "name": sender["name"],
                            "city_name": sender.get("city_name", ""),
                            "relationship_start_date": today_str,
                            "is_long_distance": sender.get("is_long_distance", False),
                            "gender": sender.get("gender", "Not to say"),
                            "profile_photo_url": sender.get("profile_photo_url")
                        }
                    }
                }
            )

            # 3. Mark this request as accepted
            await self.requests_collection.update_one(
                {"_id": ObjectId(request_id)},
                {"$set": {"status": "accepted", "updated_at": now}}
            )

            # 4. Find all OTHER pending requests involving either user to notify other users and hide all requests!
            other_requests_cursor = self.requests_collection.find({
                "_id": {"$ne": ObjectId(request_id)},
                "status": "pending",
                "$or": [
                    {"sender_id": sender_id},
                    {"receiver_id": sender_id},
                    {"sender_id": user_id},
                    {"receiver_id": user_id},
                ]
            })
            other_requests = await other_requests_cursor.to_list(length=100)

            # Cancel all other pending requests in database
            await self.requests_collection.update_many(
                {
                    "_id": {"$ne": ObjectId(request_id)},
                    "status": "pending",
                    "$or": [
                        {"sender_id": sender_id},
                        {"receiver_id": sender_id},
                        {"sender_id": user_id},
                        {"receiver_id": user_id},
                    ]
                },
                {"$set": {"status": "cancelled", "updated_at": now}}
            )

            # 5. Broadcast cancellation to any third parties who had sent or were waiting on requests
            for other_req in other_requests:
                other_req_id = str(other_req["_id"])
                parties = [other_req.get("sender_id"), other_req.get("receiver_id")]
                for p in parties:
                    if p and p not in [sender_id, user_id]:
                        try:
                            await ws_manager.broadcast_to_user(
                                user_id=p,
                                message={"type": "ALIGNMENT_REQUEST_CANCELLED", "request_id": other_req_id}
                            )
                        except Exception:
                            pass

            # 6. Notify sender with high-priority push notification
            try:
                await notification_service.create_notification(
                    NotificationCreate(
                        recipient_id=sender_id,
                        type=NotificationType.RELATIONSHIP_ACCEPT,
                        title="Alignment Connected!",
                        message=f"{receiver.get('name', 'Your partner')} approved your alignment request. You are now bonded!",
                        metadata={"partner_id": user_id, "partner_name": receiver.get("name")}
                    )
                )
            except Exception as e:
                print("Error sending accept notification:", e)

            # 7. Broadcast real-time WebSocket events to BOTH users
            try:
                await ws_manager.broadcast_to_user(
                    user_id=sender_id,
                    message={"type": "ALIGNMENT_BONDED", "partner_name": receiver.get("name", "Partner")}
                )
                await ws_manager.broadcast_to_user(
                    user_id=user_id,
                    message={"type": "ALIGNMENT_BONDED", "partner_name": sender.get("name", "Partner")}
                )
            except Exception as e:
                print("Error broadcasting bonded ws event:", e)

            return {
                "status": "accepted",
                "partner_name": sender.get("name", "Partner"),
                "partner_id": sender_id
            }

        else:
            # Reject request
            await self.requests_collection.update_one(
                {"_id": ObjectId(request_id)},
                {"$set": {"status": "rejected", "updated_at": now}}
            )

            # Send push notification to sender
            try:
                receiver = await self.collection.find_one({"_id": ObjectId(user_id)})
                receiver_name = receiver.get("name", "Your partner") if receiver else "Your partner"
                await notification_service.create_notification(
                    NotificationCreate(
                        recipient_id=sender_id,
                        type=NotificationType.RELATIONSHIP_REQUEST,
                        title="Alignment Request Declined",
                        message=f"{receiver_name} declined your alignment request.",
                        metadata={"request_id": request_id, "partner_id": user_id, "partner_name": receiver_name}
                    )
                )
            except Exception as notif_err:
                print("Failed to send alignment decline notification:", notif_err)

            # Broadcast WebSocket event to sender
            try:
                await ws_manager.broadcast_to_user(
                    user_id=sender_id,
                    message={"type": "ALIGNMENT_REJECTED", "request_id": request_id}
                )
            except Exception as e:
                print("Error broadcasting reject ws event:", e)

            return {"status": "rejected"}

    async def cancel_alignment_request(self, user_id: str, request_id: str) -> Dict[str, Any]:
        """Cancels an outgoing alignment request."""
        from bson import ObjectId
        
        req = await self.requests_collection.find_one({"_id": ObjectId(request_id)})
        if not req:
            raise ValueError("Alignment request not found.")
            
        if req.get("sender_id") != user_id:
            raise ValueError("You are not authorized to cancel this request.")
            
        now = datetime.now(timezone.utc)
        await self.requests_collection.update_one(
            {"_id": ObjectId(request_id)},
            {"$set": {"status": "cancelled", "updated_at": now}}
        )

        # Broadcast WebSocket event to receiver
        try:
            await ws_manager.broadcast_to_user(
                user_id=req["receiver_id"],
                message={"type": "ALIGNMENT_REQUEST_CANCELLED", "request_id": request_id}
            )
        except Exception as e:
            print("Error broadcasting cancel ws event:", e)

        return {"status": "cancelled"}

    async def regenerate_aligned_key(self, user_id: str, user: Optional[Dict[str, Any]] = None) -> str:
        """Generates a new unique Aligned secret key for the unaligned user."""
        from bson import ObjectId
        if not user:
            user = await self.collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise ValueError("User not found.")
        if user.get("is_aligned") or user.get("partner"):
            raise ValueError("Cannot regenerate key while actively aligned with a partner.")

        new_key = await self.generate_unique_secret_key()
        await self.collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"secret_key": new_key, "secret_key_enabled": True, "updated_at": datetime.now(timezone.utc)}}
        )
        return new_key

    async def align_users(self, user_id: str, partner_secret_key: str) -> Dict[str, Any]:
        """Connects the initiating user with another user using the partner's secret key."""
        from bson import ObjectId
        
        # 1. Fetch initiator
        initiator = await self.collection.find_one({"_id": ObjectId(user_id)})
        if not initiator:
            raise ValueError("User not found.")
            
        # 2. Fetch partner using secret key
        partner = await self.collection.find_one({"secret_key": partner_secret_key})
        if not partner:
            raise ValueError("Partner with specified secret key not found.")
            
        # 3. Check already aligned state
        if initiator.get("is_aligned"):
            raise ValueError("You are already connected to a partner.")
        if partner.get("is_aligned"):
            raise ValueError("The partner is already connected to another user.")
            
        # 4. Check if self-connect attempt
        if str(initiator["_id"]) == str(partner["_id"]):
            raise ValueError("Cannot connect to your own secret key.")
            
        # 5. Connect initiator to partner
        now = datetime.now(timezone.utc)
        today_str = now.strftime("%m.%d.%Y")

        await self.collection.update_one(
            {"_id": initiator["_id"]},
            {
                "$set": {
                    "is_aligned": True,
                    "aligned_at": now,
                    "relationship_start_date": today_str,
                    "secret_key": None, # Disable secret key
                    "partner": {
                        "user_id": str(partner["_id"]),
                        "name": partner["name"],
                        "city_name": partner.get("city_name", ""),
                        "relationship_start_date": today_str,
                        "is_long_distance": partner.get("is_long_distance", False),
                        "gender": partner.get("gender", "Not to say"),
                        "profile_photo_url": partner.get("profile_photo_url")
                    }
                }
            }
        )
        
        # 6. Connect partner to initiator
        await self.collection.update_one(
            {"_id": partner["_id"]},
            {
                "$set": {
                    "is_aligned": True,
                    "aligned_at": now,
                    "relationship_start_date": today_str,
                    "secret_key": None, # Disable secret key
                    "partner": {
                        "user_id": str(initiator["_id"]),
                        "name": initiator["name"],
                        "city_name": initiator.get("city_name", ""),
                        "relationship_start_date": today_str,
                        "is_long_distance": initiator.get("is_long_distance", False),
                        "gender": initiator.get("gender", "Not to say"),
                        "profile_photo_url": initiator.get("profile_photo_url")
                    }
                }
            }
        )
        
        # Broadcast real-time WebSocket event to BOTH users
        try:
            from app.core.websocket import ws_manager
            await ws_manager.broadcast_to_user(
                user_id=str(initiator["_id"]),
                message={"type": "ALIGNMENT_BONDED", "partner_name": partner.get("name", "Partner")}
            )
            await ws_manager.broadcast_to_user(
                user_id=str(partner["_id"]),
                message={"type": "ALIGNMENT_BONDED", "partner_name": initiator.get("name", "Partner")}
            )
        except Exception as e:
            print("Failed to send alignment ws:", e)

        # Send push notification to partner
        try:
            from app.services.notification import notification_service
            from app.schemas.notification import NotificationCreate, NotificationType
            await notification_service.schedule_notification(
                sender_id=user_id,
                payload=NotificationCreate(
                    recipient_id=str(partner["_id"]),
                    title="Connected!",
                    message=f"You are now aligned with {initiator.get('name', 'your partner')}!",
                    type=NotificationType.STATE_UPDATE,
                    scheduled_for=datetime.now(timezone.utc),
                    timezone="UTC"
                )
            )
        except Exception as e:
            print("Failed to send alignment push notification:", e)

        # Fetch and return updated initiator data
        updated_initiator = await self.collection.find_one({"_id": initiator["_id"]})
        if updated_initiator and "_id" in updated_initiator:
            updated_initiator["id"] = str(updated_initiator["_id"])
            updated_initiator["_id"] = str(updated_initiator["_id"])
            
        return updated_initiator

    async def update_relationship_profile(self, user_id: str, relationship: RelationshipCreate, user: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Updates an existing user's profile with relationship details."""
        from bson import ObjectId
        from pymongo import ReturnDocument
        
        # Verify user exists or use provided user
        if not user:
            user = await self.collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise ValueError("User not found.")
            
        updates = {
            "name": relationship.name,
            "city_name": relationship.city_name,
            "relationship_start_date": relationship.relationship_start_date,
            "is_long_distance": relationship.is_long_distance,
            "gender": getattr(relationship, "gender", "Not to say")
        }

        # If they don't have a secret key and are not aligned, generate one
        if not user.get("secret_key") and not user.get("is_aligned"):
            updates["secret_key"] = await self.generate_unique_secret_key()

        updated = await self.collection.find_one_and_update(
            {"_id": ObjectId(user_id)},
            {"$set": updates},
            return_document=ReturnDocument.AFTER
        )
        if updated and "_id" in updated:
            updated["id"] = str(updated["_id"])
            updated["_id"] = str(updated["_id"])
            
        return updated

    async def break_alignment(self, user_id: str) -> Dict[str, Any]:
        """Breaks the connection for the user and their partner."""
        from bson import ObjectId
        from app.services.notification import notification_service
        from app.schemas.notification import NotificationCreate, NotificationType
        from datetime import datetime, timezone
        
        # 1. Fetch initiator
        initiator = await self.collection.find_one({"_id": ObjectId(user_id)})
        if not initiator:
            raise ValueError("User not found.")
            
        if not initiator.get("is_aligned"):
            # Idempotently return initiator if already not aligned
            if not initiator.get("secret_key"):
                secret_key = await self.generate_unique_secret_key()
                await self.collection.update_one(
                    {"_id": initiator["_id"]},
                    {"$set": {"secret_key": secret_key, "is_aligned": False, "partner": None}}
                )
                initiator["secret_key"] = secret_key
            initiator["id"] = str(initiator["_id"])
            return initiator
            
        partner_id = initiator.get("partner", {}).get("user_id")
        
        # 2. Update initiator
        updates = {
            "$set": {
                "is_aligned": False,
                "partner": None
            }
        }
        
        # Always generate a fresh secret key on break alignment for initiator
        secret_key = await self.generate_unique_secret_key()
        updates["$set"]["secret_key"] = secret_key
            
        await self.collection.update_one(
            {"_id": initiator["_id"]},
            updates
        )
        
        # 3. Update partner if exists
        if partner_id:
            partner = await self.collection.find_one({"_id": ObjectId(partner_id)})
            if partner:
                partner_secret = await self.generate_unique_secret_key()
                partner_updates = {
                    "$set": {
                        "is_aligned": False,
                        "partner": None,
                        "secret_key": partner_secret
                    }
                }
                    
                await self.collection.update_one(
                    {"_id": partner["_id"]},
                    partner_updates
                )
                
                # Notify partner
                try:
                    await notification_service.schedule_notification(
                        sender_id=user_id,
                        payload=NotificationCreate(
                            recipient_id=partner_id,
                            title="Alignment Broken",
                            message="Your partner has broken the alignment.",
                            type=NotificationType.SYSTEM,
                            scheduled_for=datetime.now(timezone.utc),
                            timezone="UTC"
                        )
                    )
                except Exception as e:
                    print(f"Failed to send break alignment notification: {e}")

                # Broadcast WebSocket to partner
                try:
                    await ws_manager.broadcast_to_user(
                        user_id=partner_id,
                        message={"type": "ALIGNMENT_BROKEN"}
                    )
                except Exception:
                    pass

        # Broadcast WebSocket to initiator
        try:
            await ws_manager.broadcast_to_user(
                user_id=user_id,
                message={"type": "ALIGNMENT_BROKEN"}
            )
        except Exception:
            pass

        # 4. Clean up any lingering pending alignment requests in database
        try:
            await self.requests_collection.update_many(
                {
                    "status": "pending",
                    "$or": [
                        {"sender_id": user_id},
                        {"receiver_id": user_id},
                        {"sender_id": partner_id} if partner_id else {"sender_id": ""},
                        {"receiver_id": partner_id} if partner_id else {"receiver_id": ""},
                    ]
                },
                {"$set": {"status": "cancelled", "updated_at": datetime.now(timezone.utc)}}
            )
        except Exception:
            pass

        # 5. Clean Slate: Purge all past shared couple data between user_id and partner_id
        if partner_id:
            try:
                pair_ids = [user_id, partner_id]
                # Delete Thread Messages & Letters
                await self.db["thread_messages"].delete_many({
                    "$or": [
                        {"creator_id": user_id, "partner_id": partner_id},
                        {"creator_id": partner_id, "partner_id": user_id},
                        {"creator_id": {"$in": pair_ids}}
                    ]
                })
                # Delete Dates & Itineraries
                await self.db["dates"].delete_many({
                    "$or": [
                        {"creator_id": user_id, "partner_id": partner_id},
                        {"creator_id": partner_id, "partner_id": user_id},
                        {"creator_id": {"$in": pair_ids}}
                    ]
                })
                # Delete Map Places
                await self.db["map_places"].delete_many({
                    "$or": [
                        {"creator_id": user_id, "partner_id": partner_id},
                        {"creator_id": partner_id, "partner_id": user_id},
                        {"creator_id": {"$in": pair_ids}}
                    ]
                })
                # Delete US Milestones, Next Meets, and Proposals
                await self.db["milestones"].delete_many({
                    "$or": [
                        {"user_id": user_id, "partner_id": partner_id},
                        {"user_id": partner_id, "partner_id": user_id},
                        {"user_id": {"$in": pair_ids}}
                    ]
                })
                await self.db["next_meets"].delete_many({"user_id": {"$in": pair_ids}})
                await self.db["proposals"].delete_many({
                    "$or": [
                        {"sender_id": user_id, "receiver_id": partner_id},
                        {"sender_id": partner_id, "receiver_id": user_id},
                        {"user_id": {"$in": pair_ids}}
                    ]
                })
                # Delete Secrets
                await self.db["secrets"].delete_many({
                    "$or": [
                        {"sender_id": user_id, "receiver_id": partner_id},
                        {"sender_id": partner_id, "receiver_id": user_id},
                        {"user_id": {"$in": pair_ids}}
                    ]
                })
                # Delete Ritual Completions & Daily Check-ins
                await self.db["ritual_completions"].delete_many({"user_id": {"$in": pair_ids}})
                await self.db["check_ins"].delete_many({"user_id": {"$in": pair_ids}})
            except Exception as purge_err:
                print(f"Error purging couple data on break alignment: {purge_err}")
            
        # 5. Fetch and return updated initiator data
        updated_initiator = await self.collection.find_one({"_id": initiator["_id"]})
        if updated_initiator and "_id" in updated_initiator:
            updated_initiator["id"] = str(updated_initiator["_id"])
            updated_initiator["_id"] = str(updated_initiator["_id"])
            
        return updated_initiator

    async def align_users_mutually(self, user_id: str, partner_id: str) -> bool:
        """Directly aligns two users (mutually). Clears secret keys for both."""
        from bson import ObjectId
        
        user = await self.collection.find_one({"_id": ObjectId(user_id)})
        partner = await self.collection.find_one({"_id": ObjectId(partner_id)})
        
        if not user or not partner:
            return False
            
        if user.get("is_aligned") or partner.get("is_aligned"):
            # If already aligned with the SAME partner, it's fine (idempotent)
            if user.get("partner", {}).get("user_id") == partner_id:
                return True
            return False

        # Connect both
        today_str = datetime.now().strftime("%m.%d.%Y")

        await self.collection.update_one(
            {"_id": user["_id"]},
            {"$set": {
                "is_aligned": True,
                "secret_key": None,
                "relationship_start_date": today_str,
                "partner": {
                    "user_id": str(partner["_id"]),
                    "name": partner["name"],
                    "city_name": partner["city_name"],
                    "relationship_start_date": today_str,
                    "is_long_distance": partner.get("is_long_distance", False)
                }
            }}
        )
        await self.collection.update_one(
            {"_id": partner["_id"]},
            {"$set": {
                "is_aligned": True,
                "secret_key": None,
                "relationship_start_date": today_str,
                "partner": {
                    "user_id": str(user["_id"]),
                    "name": user["name"],
                    "city_name": user["city_name"],
                    "relationship_start_date": today_str,
                    "is_long_distance": user.get("is_long_distance", False)
                }
            }}
        )
        return True

    async def get_relationship_profile(self, user_id: str, user: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Retrieves a user's relationship profile."""
        from bson import ObjectId
        if not user:
            user = await self.collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise ValueError("User not found.")
            
        if "_id" in user:
            user["id"] = str(user["_id"])
            user["_id"] = str(user["_id"])
            
        return user

    async def get_partner_details(self, user_id: str, user: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Retrieves the details of the aligned partner."""
        from bson import ObjectId
        from datetime import timezone
        import asyncio
        
        if not user:
            user = await self.collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise ValueError("User not found.")
            
        if not user.get("is_aligned"):
            raise ValueError("You are not aligned with any partner.")
            
        partner_info = user.get("partner")
        if not partner_info or "user_id" not in partner_info:
            raise ValueError("Partner information not found.")
            
        partner_id = partner_info["user_id"]
        
        # Concurrently fetch partner record, latest check-in, latest thread message, and latest ritual completion
        partner_task = self.collection.find_one({"_id": ObjectId(partner_id)})
        checkin_task = self.db["check_ins"].find_one({"user_id": partner_id}, sort=[("created_at", -1)])
        msg_task = self.db["thread_messages"].find_one({"creator_id": partner_id}, sort=[("created_at", -1)])
        ritual_task = self.db["ritual_completions"].find_one({"user_id": partner_id}, sort=[("created_at", -1)])
        
        partner, latest_checkin, latest_msg, latest_ritual = await asyncio.gather(
            partner_task, checkin_task, msg_task, ritual_task
        )
        
        if not partner:
            raise ValueError("Partner record not found.")
            
        if "_id" in partner:
            partner["id"] = str(partner["_id"])
            partner["_id"] = str(partner["_id"])
            
        timestamps = []
        if partner.get("last_active_at"):
            timestamps.append(partner["last_active_at"])
            
        if latest_checkin and latest_checkin.get("created_at"):
            timestamps.append(latest_checkin["created_at"])
            
        if latest_msg and latest_msg.get("created_at"):
            timestamps.append(latest_msg["created_at"])
            
        if latest_ritual:
            if latest_ritual.get("created_at"):
                timestamps.append(latest_ritual["created_at"])
            # Format _id and created_at to strings for the frontend
            latest_ritual["_id"] = str(latest_ritual["_id"])
            if latest_ritual.get("created_at"):
                ritual_dt = latest_ritual["created_at"]
                if ritual_dt.tzinfo is None:
                    ritual_dt = ritual_dt.replace(tzinfo=timezone.utc)
                latest_ritual["created_at"] = ritual_dt.isoformat()
            partner["latest_ritual"] = latest_ritual
            
        if timestamps:
            max_ts = max(timestamps)
            if max_ts.tzinfo is None:
                max_ts = max_ts.replace(tzinfo=timezone.utc)
            partner["last_active_at"] = max_ts

        if not partner.get("location_city") and partner.get("timezone") and "/" in partner.get("timezone"):
            partner["location_city"] = partner["timezone"].split("/")[-1].replace("_", " ")

        return partner

    async def update_user(self, user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Updates specific fields of the user profile."""
        from bson import ObjectId
        from pymongo import ReturnDocument
        
        updated = await self.collection.find_one_and_update(
            {"_id": ObjectId(user_id)},
            {"$set": updates},
            return_document=ReturnDocument.AFTER
        )
        if not updated:
            raise ValueError("User not found.")
        
        # If gender was updated, sync to partner's record
        if "gender" in updates:
            partner = updated.get("partner")
            partner_id = partner.get("user_id") if partner else None
            if partner_id:
                await self.collection.update_one(
                    {"_id": ObjectId(partner_id)},
                    {"$set": {"partner.gender": updates["gender"]}}
                )
        
        if "_id" in updated:
            updated["id"] = str(updated["_id"])
            updated["_id"] = str(updated["_id"])
        return updated

    async def add_profile_photo(self, user_id: str, file_url: str) -> Dict[str, Any]:
        """Adds a new profile photo to history and sets it as the active photo."""
        from bson import ObjectId
        import uuid
        from datetime import datetime, timezone
        
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
        from bson import ObjectId
        import uuid
        from datetime import datetime, timezone
        
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
        from bson import ObjectId
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
        from bson import ObjectId
        from app.services.s3_utils import s3_service
        import os
        
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
            if "amazonaws.com" in file_url:
                await s3_service.delete_file(file_url)
            elif os.path.exists(file_url.lstrip("/")):
                os.remove(file_url.lstrip("/"))
                
        remaining_photos = [p for p in photos if str(p.get("id")) != str(photo_id) and p.get("url") != target.get("url")]
        
        # If the deleted photo was the active one, fallback to the first remaining photo or None
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
            from bson import ObjectId
            await self.collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"profile_photo_url": None}}
            )
            return await self._notify_profile_photo_update(user_id)

    async def _notify_profile_photo_update(self, user_id: str) -> Dict[str, Any]:
        """Internal helper to broadcast photo updates and return updated user object."""
        from bson import ObjectId
        from datetime import datetime, timezone
        
        updated = await self.collection.find_one({"_id": ObjectId(user_id)})
        if updated and "_id" in updated:
            updated["id"] = str(updated["_id"])
            updated["_id"] = str(updated["_id"])
            
            if updated.get("partner") and updated["partner"].get("user_id"):
                partner_id = updated["partner"]["user_id"]
                user_name = updated.get("name", "Your partner")
                
                # Websocket
                await ws_manager.broadcast_to_user(
                    partner_id, 
                    {"type": "PROFILE_PHOTO_UPDATED"}
                )
                
                # Push notification
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

                # Presence
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
        from bson import ObjectId
        user = await self.collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise ValueError("User not found.")
        return user.get("profile_photo_url")

    async def get_sync_summary(self, user_id: str, timezone_str: str = "UTC", user: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Calculates the combined Sync score for the user and their Aligned partner.
        Enforces a max 1-count-per-day per person cap for Rituals, Check-ins, Appreciations, and Threads.
        """
        from bson import ObjectId
        from datetime import datetime, timezone, timedelta
        from typing import Optional
        import asyncio
        
        if not user:
            user = await self.collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise ValueError("User not found.")
            
        partner_id = None
        if user.get("is_aligned") and user.get("partner"):
            partner_id = user["partner"].get("user_id")
            
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
        
        # Collections
        rituals_coll = self.db["ritual_completions"]
        checkins_coll = self.db["check_ins"]
        messages_coll = self.db["thread_messages"]
        
        # Dates for check_ins which uses string dates (supporting both "MM.DD.YYYY" and "YYYY-MM-DD")
        local_now = now.astimezone(tz)
        dates_to_check_dot = [(local_now - timedelta(days=i)).strftime("%m.%d.%Y") for i in range(7)]
        dates_to_check_dash = [(local_now - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
        all_dates_to_check = list(set(dates_to_check_dot + dates_to_check_dash))
        
        async def count_unique_active_days(collection, query: dict, date_field: str = "created_at") -> int:
            """Counts unique calendar days (in user's timezone) where the query matched (max 1 per day)."""
            docs = await collection.find(query, {date_field: 1, "completed_date": 1}).to_list(length=200)
            unique_days = set()
            for doc in docs:
                dt = doc.get(date_field)
                if isinstance(dt, datetime):
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    local_day = dt.astimezone(tz).strftime("%Y-%m-%d")
                    unique_days.add(local_day)
                elif doc.get("completed_date"):
                    unique_days.add(doc["completed_date"])
            return len(unique_days)

        async def count_unique_appreciation_days(uid: Optional[str]) -> int:
            if not uid:
                return 0
            # Fetch both ritual_completions and thread_messages concurrently
            t1 = rituals_coll.find(
                {"user_id": uid, "ritual_type": "appreciation", "created_at": {"$gte": seven_days_ago}},
                {"created_at": 1, "completed_date": 1}
            ).to_list(length=100)
            t2 = messages_coll.find(
                {"creator_id": uid, "category": {"$in": ["Appreciation", "appreciation"]}, "created_at": {"$gte": seven_days_ago}},
                {"created_at": 1}
            ).to_list(length=100)
            res1, res2 = await asyncio.gather(t1, t2)

            unique_days = set()
            for doc in res1:
                dt = doc.get("created_at")
                if isinstance(dt, datetime):
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    unique_days.add(dt.astimezone(tz).strftime("%Y-%m-%d"))
                elif doc.get("completed_date"):
                    unique_days.add(doc["completed_date"])
            for doc in res2:
                dt = doc.get("created_at")
                if isinstance(dt, datetime):
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    unique_days.add(dt.astimezone(tz).strftime("%Y-%m-%d"))
            return len(unique_days)

        def calculate_metric_sync(user_count: int, partner_count: int, max_per_user: int = 7) -> tuple[int, int, int]:
            # Cap the counts at the weekly max (7 per user)
            u = min(user_count, max_per_user)
            p = min(partner_count, max_per_user)
            
            total = u + p
            max_total = max_per_user * 2 # 14
            
            if total == 0:
                return 0, 0, max_total
                
            volume_score = total / max_total
            diff = abs(u - p)
            # max difference is max_per_user. penalize up to 50%
            diff_penalty = diff / max_per_user
            sync_multiplier = 1.0 - (diff_penalty * 0.5)
            
            perc = min(int((volume_score * sync_multiplier) * 100), 100)
            return perc, total, max_total

        def normalize_checkin_date(d_str: str) -> Optional[str]:
            for fmt in ("%m.%d.%Y", "%Y-%m-%d", "%m/%d/%Y"):
                try:
                    return datetime.strptime(d_str, fmt).strftime("%Y-%m-%d")
                except ValueError:
                    pass
            return d_str

        async def empty_int() -> int:
            return 0

        async def empty_list() -> list:
            return []

        # Run all metrics for user and partner concurrently in parallel
        user_rituals_task = count_unique_active_days(
            rituals_coll, 
            {"user_id": user_id, "created_at": {"$gte": seven_days_ago}}
        )
        partner_rituals_task = count_unique_active_days(
            rituals_coll, 
            {"user_id": partner_id, "created_at": {"$gte": seven_days_ago}}
        ) if partner_id else empty_int()

        user_checkins_task = checkins_coll.distinct("date", {"user_id": user_id, "date": {"$in": all_dates_to_check}})
        partner_checkins_task = checkins_coll.distinct("date", {"user_id": partner_id, "date": {"$in": all_dates_to_check}}) if partner_id else empty_list()

        user_appr_task = count_unique_appreciation_days(user_id)
        partner_appr_task = count_unique_appreciation_days(partner_id) if partner_id else empty_int()

        user_threads_task = count_unique_active_days(
            messages_coll, 
            {"creator_id": user_id, "created_at": {"$gte": seven_days_ago}}
        )
        partner_threads_task = count_unique_active_days(
            messages_coll, 
            {"creator_id": partner_id, "created_at": {"$gte": seven_days_ago}}
        ) if partner_id else empty_int()

        (
            user_rituals,
            partner_rituals,
            user_checkin_raw,
            partner_checkin_raw,
            user_appr,
            partner_appr,
            user_threads,
            partner_threads
        ) = await asyncio.gather(
            user_rituals_task,
            partner_rituals_task,
            user_checkins_task,
            partner_checkins_task,
            user_appr_task,
            partner_appr_task,
            user_threads_task,
            partner_threads_task
        )

        r_perc, r_count, r_target = calculate_metric_sync(user_rituals, partner_rituals)
        user_checkins = len(set(normalize_checkin_date(d) for d in (user_checkin_raw or []) if d))
        partner_checkins = len(set(normalize_checkin_date(d) for d in (partner_checkin_raw or []) if d))
        c_perc, c_count, c_target = calculate_metric_sync(user_checkins, partner_checkins)
        a_perc, a_count, a_target = calculate_metric_sync(user_appr, partner_appr)
        t_perc, t_count, t_target = calculate_metric_sync(user_threads, partner_threads)
        
        # Weighted overall score
        # Rituals: 30%, Check-ins: 30%, Appreciations: 20%, Threads: 20%
        overall = int((r_perc * 0.30) + (c_perc * 0.30) + (a_perc * 0.20) + (t_perc * 0.20))
        
        return {
            "overall_score": overall,
            "rituals": {"count": r_count, "target": r_target, "percentage": r_perc},
            "checkins": {"count": c_count, "target": c_target, "percentage": c_perc},
            "appreciations": {"count": a_count, "target": a_target, "percentage": a_perc},
            "threads": {"count": t_count, "target": t_target, "percentage": t_perc}
        }

relationship_service = RelationshipService()
