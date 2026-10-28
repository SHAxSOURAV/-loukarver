import random
from app.services.relationship_photos import relationship_photo_service
from app.services.alignment_requests import alignment_request_service
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
            (self.collection, [("gender", 1), ("partner.user_id", 1)], {}),
            (self.collection, [("is_admin", 1), ("is_deleted", 1), ("is_hidden", 1)], {}),
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
        return await alignment_request_service.create_alignment_request(user_id, partner_secret_key)

    async def get_alignment_request_status(self, user_id: str, user: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return await alignment_request_service.get_alignment_request_status(user_id, user=user)

    async def respond_alignment_request(self, user_id: str, request_id: str, accept: bool) -> Dict[str, Any]:
        return await alignment_request_service.respond_alignment_request(user_id, request_id, accept)

    async def cancel_alignment_request(self, user_id: str, request_id: str) -> Dict[str, Any]:
        return await alignment_request_service.cancel_alignment_request(user_id, request_id)

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

        if not partner.get("location_city"):
            if partner.get("city_name"):
                partner["location_city"] = partner["city_name"]
            elif partner.get("timezone") and "/" in partner.get("timezone"):
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
        return await relationship_photo_service.add_profile_photo(user_id, file_url)

    async def get_profile_photos(self, user_id: str, user: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return await relationship_photo_service.get_profile_photos(user_id, user=user)

    async def select_profile_photo(self, user_id: str, photo_id: str) -> Dict[str, Any]:
        return await relationship_photo_service.select_profile_photo(user_id, photo_id)

    async def delete_profile_photo_item(self, user_id: str, photo_id: str) -> Dict[str, Any]:
        return await relationship_photo_service.delete_profile_photo_item(user_id, photo_id)

    async def update_profile_photo(self, user_id: str, file_path: str) -> Dict[str, Any]:
        return await relationship_photo_service.update_profile_photo(user_id, file_path)

    async def _notify_profile_photo_update(self, user_id: str) -> Dict[str, Any]:
        return await relationship_photo_service._notify_profile_photo_update(user_id)

    async def get_profile_photo_path(self, user_id: str) -> str:
        return await relationship_photo_service.get_profile_photo_path(user_id)

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
