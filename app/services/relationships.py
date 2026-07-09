import random
import string
from typing import List, Dict, Any
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from app.schemas.relationships import RelationshipCreate

class RelationshipService:
    def __init__(self) -> None:
        self.client = AsyncIOMotorClient(settings.MONGO_URL)
        self.db = self.client[settings.MONGO_DB_NAME]
        self.collection = self.db["users"]

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
        await self.collection.update_one(
            {"_id": initiator["_id"]},
            {
                "$set": {
                    "is_aligned": True,
                    "secret_key": None, # Disable secret key
                    "partner": {
                        "user_id": str(partner["_id"]),
                        "name": partner["name"],
                        "city_name": partner["city_name"],
                        "relationship_start_date": partner["relationship_start_date"],
                        "is_long_distance": partner["is_long_distance"]
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
                    "secret_key": None, # Disable secret key
                    "partner": {
                        "user_id": str(initiator["_id"]),
                        "name": initiator["name"],
                        "city_name": initiator["city_name"],
                        "relationship_start_date": initiator["relationship_start_date"],
                        "is_long_distance": initiator["is_long_distance"]
                    }
                }
            }
        )
        
        # Fetch and return updated initiator data
        updated_initiator = await self.collection.find_one({"_id": initiator["_id"]})
        if updated_initiator and "_id" in updated_initiator:
            updated_initiator["id"] = str(updated_initiator["_id"])
            updated_initiator["_id"] = str(updated_initiator["_id"])
            
        return updated_initiator

    async def update_relationship_profile(self, user_id: str, relationship: RelationshipCreate) -> Dict[str, Any]:
        """Updates an existing user's profile with relationship details."""
        from bson import ObjectId
        
        # Verify user exists
        user = await self.collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise ValueError("User not found.")
            
        updates = {
            "name": relationship.name,
            "city_name": relationship.city_name,
            "relationship_start_date": relationship.relationship_start_date,
            "is_long_distance": relationship.is_long_distance
        }

        # If they don't have a secret key and are not aligned, generate one
        if not user.get("secret_key") and not user.get("is_aligned"):
            updates["secret_key"] = await self.generate_unique_secret_key()

        await self.collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": updates}
        )
        
        updated = await self.collection.find_one({"_id": ObjectId(user_id)})
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
            raise ValueError("You are not connected to anyone.")
            
        partner_id = initiator.get("partner", {}).get("user_id")
        
        # 2. Update initiator
        updates = {
            "$set": {
                "is_aligned": False,
                "partner": None
            }
        }
        
        # If secret_key doesn't exist (e.g. older user who had it deleted), generate a new one
        if not initiator.get("secret_key"):
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
                partner_updates = {
                    "$set": {
                        "is_aligned": False,
                        "partner": None
                    }
                }
                if not partner.get("secret_key"):
                    partner_secret = await self.generate_unique_secret_key()
                    partner_updates["$set"]["secret_key"] = partner_secret
                    
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
            
        # 4. Fetch and return updated initiator data
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
        await self.collection.update_one(
            {"_id": user["_id"]},
            {"$set": {
                "is_aligned": True,
                "secret_key": None,
                "partner": {
                    "user_id": str(partner["_id"]),
                    "name": partner["name"],
                    "city_name": partner["city_name"],
                    "relationship_start_date": partner["relationship_start_date"],
                    "is_long_distance": partner["is_long_distance"]
                }
            }}
        )
        await self.collection.update_one(
            {"_id": partner["_id"]},
            {"$set": {
                "is_aligned": True,
                "secret_key": None,
                "partner": {
                    "user_id": str(user["_id"]),
                    "name": user["name"],
                    "city_name": user["city_name"],
                    "relationship_start_date": user["relationship_start_date"],
                    "is_long_distance": user["is_long_distance"]
                }
            }}
        )
        return True

    async def get_relationship_profile(self, user_id: str) -> Dict[str, Any]:
        """Retrieves a user's relationship profile."""
        from bson import ObjectId
        user = await self.collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise ValueError("User not found.")
            
        if "_id" in user:
            user["id"] = str(user["_id"])
            user["_id"] = str(user["_id"])
            
        return user

    async def get_partner_details(self, user_id: str) -> Dict[str, Any]:
        """Retrieves the details of the aligned partner."""
        from bson import ObjectId
        user = await self.collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise ValueError("User not found.")
            
        if not user.get("is_aligned"):
            raise ValueError("You are not aligned with any partner.")
            
        partner_info = user.get("partner")
        if not partner_info or "user_id" not in partner_info:
            raise ValueError("Partner information not found.")
            
        partner_id = partner_info["user_id"]
        partner = await self.collection.find_one({"_id": ObjectId(partner_id)})
        
        if not partner:
            raise ValueError("Partner record not found.")
            
        if "_id" in partner:
            partner["id"] = str(partner["_id"])
            partner["_id"] = str(partner["_id"])
            
        timestamps = []
        if partner.get("last_active_at"):
            timestamps.append(partner["last_active_at"])
            
        # Check check_ins
        latest_checkin = await self.db["check_ins"].find_one({"user_id": partner_id}, sort=[("created_at", -1)])
        if latest_checkin and latest_checkin.get("created_at"):
            timestamps.append(latest_checkin["created_at"])
            
        # Check thread_messages
        latest_msg = await self.db["thread_messages"].find_one({"creator_id": partner_id}, sort=[("created_at", -1)])
        if latest_msg and latest_msg.get("created_at"):
            timestamps.append(latest_msg["created_at"])
            
        # Check ritual_completions
        latest_ritual = await self.db["ritual_completions"].find_one({"user_id": partner_id}, sort=[("created_at", -1)])
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
            
        return partner

    async def update_user(self, user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Updates specific fields of the user profile."""
        from bson import ObjectId
        await self.collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": updates}
        )
        updated = await self.collection.find_one({"_id": ObjectId(user_id)})
        if updated and "_id" in updated:
            updated["id"] = str(updated["_id"])
            updated["_id"] = str(updated["_id"])
        return updated

    async def update_profile_photo(self, user_id: str, file_path: str) -> Dict[str, Any]:
        """Updates the user's profile photo path."""
        from bson import ObjectId
        await self.collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"profile_photo_url": file_path}}
        )
        updated = await self.collection.find_one({"_id": ObjectId(user_id)})
        if updated and "_id" in updated:
            updated["id"] = str(updated["_id"])
            updated["_id"] = str(updated["_id"])
        return updated

    async def get_profile_photo_path(self, user_id: str) -> str:
        """Retrieves the user's profile photo path."""
        from bson import ObjectId
        user = await self.collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise ValueError("User not found.")
        return user.get("profile_photo_url")

    async def get_sync_summary(self, user_id: str, timezone_str: str = "UTC") -> Dict[str, Any]:
        """Calculates the combined Sync score for the user and their Aligned partner."""
        from bson import ObjectId
        from datetime import datetime, timezone, timedelta
        
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
        
        # Dates for check_ins which uses string dates "MM.DD.YYYY"
        local_now = now.astimezone(tz)
        dates_to_check = [(local_now - timedelta(days=i)).strftime("%m.%d.%Y") for i in range(7)]
        
        def calculate_metric_sync(user_count: int, partner_count: int, max_per_user: int = 7) -> tuple[int, int, int]:
            # Cap the counts at the weekly max
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

        # 1. Rituals
        user_rituals = await rituals_coll.count_documents({"user_id": user_id, "created_at": {"$gte": seven_days_ago}})
        partner_rituals = await rituals_coll.count_documents({"user_id": partner_id, "created_at": {"$gte": seven_days_ago}}) if partner_id else 0
        r_perc, r_count, r_target = calculate_metric_sync(user_rituals, partner_rituals)
        
        # 2. Check-ins
        user_checkin_dates = await checkins_coll.distinct("date", {"user_id": user_id, "date": {"$in": dates_to_check}})
        user_checkins = len(user_checkin_dates)
        
        partner_checkins = 0
        if partner_id:
            partner_checkin_dates = await checkins_coll.distinct("date", {"user_id": partner_id, "date": {"$in": dates_to_check}})
            partner_checkins = len(partner_checkin_dates)
            
        c_perc, c_count, c_target = calculate_metric_sync(user_checkins, partner_checkins)
        
        # 3. Appreciations (ritual_type="appreciation")
        user_appr = await rituals_coll.count_documents({"user_id": user_id, "ritual_type": "appreciation", "created_at": {"$gte": seven_days_ago}})
        partner_appr = await rituals_coll.count_documents({"user_id": partner_id, "ritual_type": "appreciation", "created_at": {"$gte": seven_days_ago}}) if partner_id else 0
        a_perc, a_count, a_target = calculate_metric_sync(user_appr, partner_appr)
        
        # 4. Threads (Any Thread message)
        user_threads = await messages_coll.count_documents({"creator_id": user_id, "created_at": {"$gte": seven_days_ago}})
        partner_threads = await messages_coll.count_documents({"creator_id": partner_id, "created_at": {"$gte": seven_days_ago}}) if partner_id else 0
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
