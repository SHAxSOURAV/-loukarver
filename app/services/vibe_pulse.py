from typing import Dict, Any, List, Optional
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from datetime import datetime, timezone
from app.core.config import settings
from app.schemas.vibe_pulse import (
    VibePulseSetRequest, PulseStatus, VibePulseResponse, AlignedCheckResponse,
    VibeFlagCreate, VibeFlagUpdate, FlagType, FlagCategory
)
from app.services.vibe_check import vibe_check_service
from app.services.relationships import relationship_service

class VibePulseService:
    def __init__(self) -> None:
        self.client = AsyncIOMotorClient(settings.MONGO_URL)
        self.db = self.client[settings.MONGO_DB_NAME]
        self.pulses = self.db["vibe_pulses"]
        self.connections = self.db["vibe_check_connections"]
        self.profiles = self.db["vibe_check_profiles"]
        self.flags = self.db["vibe_flags"]

    async def init_indexes(self):
        await self.pulses.create_index([("user_id", 1), ("partner_id", 1)], unique=True)
        await self.pulses.create_index("user_id")
        await self.flags.create_index([("user_id", 1), ("partner_id", 1)])
        await self.flags.create_index("partner_id")

    # --- Flag Methods ---

    async def create_flag(self, user_id: str, payload: VibeFlagCreate) -> Dict[str, Any]:
        """Creates a relationship flag. Sends notification for public red flags."""

        now = datetime.now(timezone.utc)

        doc = {
            "user_id": user_id,
            "partner_id": payload.partner_id,
            "category": payload.category,
            "type": payload.type,
            "text": payload.text,
            "timezone": payload.timezone,
            "created_at": now,
            "updated_at": now
        }

        res = await self.flags.insert_one(doc)
        doc["id"] = str(res.inserted_id)

        # --- WebSocket: notify both users so their flag lists refresh instantly ---
        from app.core.websocket import ws_manager
        ws_event = {"type": "FLAG_CREATED", "flag_id": doc["id"], "category": str(payload.category.value), "visibility": str(payload.type.value)}
        await ws_manager.broadcast_to_user(user_id, ws_event)
        await ws_manager.broadcast_to_user(payload.partner_id, ws_event)

        # --- Notification: public flags alert the partner ---
        if payload.type == FlagType.PUBLIC:
            from app.services.notification import notification_service
            from app.schemas.notification import NotificationCreate, NotificationType

            # Look up the creator's name for a human-readable notification
            user = await self.db["users"].find_one({"_id": ObjectId(user_id)})
            sender_name = user.get("name", "Your partner") if user else "Your partner"

            title_map = {
                FlagCategory.RED: "🚩 Red Flag Raised",
                FlagCategory.YELLOW: "⚠️ Yellow Flag Raised",
                FlagCategory.GREEN: "💚 Green Flag Raised",
            }
            
            type_map = {
                FlagCategory.RED: NotificationType.RED_FLAG,
                FlagCategory.YELLOW: NotificationType.YELLOW_FLAG,
                FlagCategory.GREEN: NotificationType.GREEN_FLAG,
            }

            notif = NotificationCreate(
                recipient_id=payload.partner_id,
                title=title_map.get(payload.category, "Flag Raised"),
                message=f"{sender_name} raised a public {payload.category.value} flag: \"{payload.text}\"",
                type=type_map.get(payload.category, NotificationType.SYSTEM),
                timezone=payload.timezone,
            )
            await notification_service.schedule_notification(user_id, notif)

        return doc

    async def get_my_flags(self, user_id: str, partner_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieves flags created by the user."""
        query = {"user_id": user_id}
        if partner_id:
            query["partner_id"] = partner_id

        cursor = self.flags.find(query).sort("created_at", -1)
        docs = await cursor.to_list(length=None)
        for d in docs:
            d["id"] = str(d["_id"])
        return docs

    async def get_partner_flags(self, user_id: str, partner_id: str) -> List[Dict[str, Any]]:
        """Retrieves PUBLIC flags created by a partner ABOUT the user."""
        # My partner (partner_id) created a flag about me (user_id)
        query = {
            "user_id": partner_id,
            "partner_id": user_id,
            "type": FlagType.PUBLIC
        }
        cursor = self.flags.find(query).sort("created_at", -1)
        docs = await cursor.to_list(length=None)
        for d in docs:
            d["id"] = str(d["_id"])
        return docs

    async def update_flag(self, user_id: str, flag_id: str, payload: VibeFlagUpdate) -> Dict[str, Any]:
        """Updates an existing flag."""
        now = datetime.now(timezone.utc)
        update_data = payload.model_dump(exclude_none=True)
        update_data["updated_at"] = now

        res = await self.flags.find_one_and_update(
            {"_id": ObjectId(flag_id), "user_id": user_id},
            {"$set": update_data},
            return_document=True
        )
        if not res:
            raise ValueError("Flag not found or access denied.")

        res["id"] = str(res["_id"])
        return res

    async def delete_flag(self, user_id: str, flag_id: str) -> bool:
        """Deletes a flag."""
        res = await self.flags.delete_one({"_id": ObjectId(flag_id), "user_id": user_id})
        return res.deleted_count > 0

    # Canonical ladder order for sequential enforcement
    LADDER_ORDER = ["Talking", "Dating", "Seeing", "Working", "Exclusive", "FWB", "Serious", "Aligned"]

    async def set_pulse(self, user_id: str, payload: VibePulseSetRequest) -> Dict[str, Any]:
        # 1. Verify connection
        is_connected = await self.connections.find_one({"user_id": user_id, "partner_id": payload.partner_id})
        if not is_connected:
            raise ValueError("You can only set a Vibe Pulse for connected partners.")

        now = datetime.now(timezone.utc)

        # 2. Sequential step enforcement
        my_pulse = await self.pulses.find_one({"user_id": user_id, "partner_id": payload.partner_id})
        current_status = my_pulse["status"] if my_pulse else PulseStatus.NONE

        if current_status == PulseStatus.NONE:
            # First time — must start at Talking
            if payload.status != PulseStatus.TALKING:
                raise ValueError("You must start at Talking before moving up the ladder.")
        else:
            # Enforce +1 or -1 step movement
            try:
                current_idx = self.LADDER_ORDER.index(current_status)
            except ValueError:
                current_idx = 0  # fallback
            try:
                target_idx = self.LADDER_ORDER.index(payload.status.value)
            except ValueError:
                raise ValueError(f"Invalid ladder step: {payload.status.value}")

            diff = target_idx - current_idx
            if diff not in (1, -1):
                raise ValueError("You can only move one step at a time on the ladder.")

        # 3. Special Logic for Aligned
        if payload.status == PulseStatus.ALIGNED:
            # A. Check main relationship profile
            user_profile = await self.db["users"].find_one({"_id": ObjectId(user_id)})
            if user_profile and user_profile.get("is_aligned"):
                main_partner_id = user_profile.get("partner", {}).get("user_id")
                if main_partner_id != payload.partner_id:
                    raise ValueError("You are already Aligned with another person in your main relationship.")

            # B. Check if user is already Aligned with someone else in ladder
            existing_aligned = await self.pulses.find_one({
                "user_id": user_id,
                "partner_id": {"$ne": payload.partner_id},
                "status": PulseStatus.ALIGNED
            })
            if existing_aligned:
                raise ValueError("You are already Aligned with another person in the Vibe Ladder. Please reset that status first.")

            # C. Require partner to be at Serious or higher before Aligned
            their_pulse = await self.pulses.find_one({"user_id": payload.partner_id, "partner_id": user_id})
            their_status = their_pulse["status"] if their_pulse else PulseStatus.NONE
            try:
                their_idx = self.LADDER_ORDER.index(their_status)
            except ValueError:
                their_idx = -1
            serious_idx = self.LADDER_ORDER.index("Serious")
            if their_idx < serious_idx:
                raise ValueError("Your partner must be at Serious or higher before you can select Aligned.")

        # 4. Update status
        await self.pulses.update_one(
            {"user_id": user_id, "partner_id": payload.partner_id},
            {"$set": {
                "status": payload.status,
                "updated_at": now
            }},
            upsert=True
        )

        # 5. Handle Demotion & Alignment Breaking
        try:
            new_idx = self.LADDER_ORDER.index(payload.status.value)
            serious_idx = self.LADDER_ORDER.index("Serious")
            
            # A. Prevent stepping down from Aligned directly without password ONLY if officially aligned
            if current_status == PulseStatus.ALIGNED and payload.status != PulseStatus.ALIGNED:
                user_profile = await self.db["users"].find_one({"_id": ObjectId(user_id)})
                if user_profile and user_profile.get("is_aligned"):
                    raise ValueError("To break alignment and step down, please use the Break Alignment button and confirm your password.")

            # B. If I am dropping below Serious, auto-demote partner if they are at Aligned
            elif new_idx < serious_idx:
                await self.pulses.update_one(
                    {"user_id": payload.partner_id, "partner_id": user_id, "status": PulseStatus.ALIGNED.value},
                    {"$set": {
                        "status": PulseStatus.SERIOUS.value,
                        "updated_at": now
                    }}
                )
        except ValueError as e:
            if str(e).startswith("To break"):
                raise e
            pass


        status = await self.get_pulse_status(user_id, payload.partner_id)

        # 6. Trigger Main Relationship Alignment if mutual Aligned
        if status.get("is_aligned_matched"):
            user_profile = await self.db["users"].find_one({"_id": ObjectId(user_id)})
            was_already_aligned = user_profile.get("is_aligned", False) if user_profile else False

            await relationship_service.align_users_mutually(user_id, payload.partner_id)

            if not was_already_aligned:
                from app.services.notification import notification_service
                from app.schemas.notification import NotificationCreate, NotificationType
                
                initiator_name = user_profile.get("name", "Your partner") if user_profile else "Your partner"

                try:
                    await notification_service.schedule_notification(
                        sender_id=user_id,
                        payload=NotificationCreate(
                            recipient_id=payload.partner_id,
                            title="Alignment Complete! 🎉",
                            message=f"{initiator_name} has just aligned with you on the ladder. You are now officially a couple!",
                            type=NotificationType.SYSTEM,
                            scheduled_for=now,
                            timezone="UTC"
                        )
                    )
                except Exception as e:
                    print(f"Failed to send alignment notification: {e}")

        # Broadcast pulse updated event to partner
        try:
            from app.core.websocket import ws_manager
            await ws_manager.broadcast_to_user(payload.partner_id, {"type": "PULSE_UPDATED"})
        except Exception as e:
            print(f"Failed to broadcast PULSE_UPDATED: {e}")

        return status

    async def get_pulse_status(self, user_id: str, partner_id: str) -> Dict[str, Any]:
        # Get my status for them — auto-start at Talking if no record exists
        my_pulse = await self.pulses.find_one({"user_id": user_id, "partner_id": partner_id})
        if not my_pulse:
            # Auto-create a Talking pulse for this user+partner pair
            now = datetime.now(timezone.utc)
            await self.pulses.update_one(
                {"user_id": user_id, "partner_id": partner_id},
                {"$set": {"status": PulseStatus.TALKING, "updated_at": now}},
                upsert=True
            )
            my_pulse = await self.pulses.find_one({"user_id": user_id, "partner_id": partner_id})

        my_status = my_pulse["status"] if my_pulse else PulseStatus.NONE

        # Get their status for me
        their_pulse = await self.pulses.find_one({"user_id": partner_id, "partner_id": user_id})
        their_status = their_pulse["status"] if their_pulse else PulseStatus.NONE

        partner_profile = await vibe_check_service.get_profile(partner_id)
        
        is_aligned_matched = (my_status == PulseStatus.ALIGNED and their_status == PulseStatus.ALIGNED)

        return {
            "partner_id": partner_id,
            "partner_name": partner_profile["name"] if partner_profile else "Unknown",
            "my_status": my_status,
            "partner_status": their_status,
            "is_aligned_matched": is_aligned_matched,
            "updated_at": my_pulse["updated_at"] if my_pulse else datetime.now(timezone.utc)
        }

    async def get_all_pulses(self, user_id: str) -> List[Dict[str, Any]]:
        # Fetch all my pulses
        cursor = self.pulses.find({"user_id": user_id})
        my_pulses = await cursor.to_list(length=None)
        
        results = []
        for p in my_pulses:
            results.append(await self.get_pulse_status(user_id, p["partner_id"]))
        return results

    async def check_aligned_connection(self, user_id: str, partner_id: str) -> Dict[str, Any]:
        """
        Specific API to check if both set 'Aligned' previously.
        If yes, and neither is aligned with anyone else, confirm connection.
        """
        status = await self.get_pulse_status(user_id, partner_id)
        
        if status["is_aligned_matched"]:
            return {
                "success": True,
                "is_aligned": True,
                "partner_id": partner_id,
                "partner_name": status["partner_name"],
                "message": f"You and {status['partner_name']} are mutually Aligned!"
            }
        
        return {
            "success": True,
            "is_aligned": False,
            "message": "You are not mutually Aligned with this partner yet."
        }

    async def delete_pulse(self, user_id: str, partner_id: str) -> bool:
        result = await self.pulses.delete_one({"user_id": user_id, "partner_id": partner_id})
        return result.deleted_count > 0

vibe_pulse_service = VibePulseService()
