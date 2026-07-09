from datetime import datetime, timezone
from typing import Dict, Any, List
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from app.core.config import settings
from app.schemas.proposals import ProposalCreate
from app.services.us import UsService


class ProposalService:
    def __init__(self) -> None:
        self.client = AsyncIOMotorClient(settings.MONGO_URL)
        self.db = self.client[settings.MONGO_DB_NAME]
        self.users_collection = self.db["users"]
        self.proposals_collection = self.db["proposals"]
        self.notifications_collection = self.db["notifications"]
        self.us_service = UsService()

    async def _get_partner_id(self, user_id: str) -> str:
        user = await self.users_collection.find_one({"_id": ObjectId(user_id)})
        if user and user.get("is_aligned") and user.get("partner"):
            return user["partner"].get("user_id")
        return None

    async def _get_user_name(self, user_id: str) -> str:
        user = await self.users_collection.find_one({"_id": ObjectId(user_id)})
        if user:
            return user.get("name", "Your partner")
        return "Your partner"

    async def _send_notification(self, recipient_id: str, sender_id: str, message: str, metadata: dict = None):
        """Create a notification document directly in the notifications collection."""
        now_utc = datetime.now(timezone.utc)
        doc = {
            "title": "Proposal",
            "message": message,
            "type": "Proposal",
            "timezone": "UTC",
            "scheduled_for": now_utc,
            "sender_id": sender_id,
            "recipient_id": recipient_id,
            "status": "Delivered",
            "created_at": now_utc,
            "delivered_at": now_utc,
            "is_hidden": False,
            "metadata": metadata or {},
        }
        await self.notifications_collection.insert_one(doc)

        # Try to send via WebSocket
        try:
            from app.core.websocket import ws_manager
            ws_payload = {
                "type": "NEW_NOTIFICATION",
                "notification": {
                    "type": "Proposal",
                    "title": "Proposal",
                    "message": message
                }
            }
            await ws_manager.broadcast_to_user(recipient_id, ws_payload)
        except Exception:
            pass

    async def create_proposal(self, user_id: str, proposal_data: ProposalCreate) -> Dict[str, Any]:
        partner_id = await self._get_partner_id(user_id)
        if not partner_id:
            raise ValueError("No aligned partner found.")

        # Cancel any existing pending proposals of the same type from this user
        await self.proposals_collection.update_many(
            {
                "proposer_id": user_id,
                "partner_id": partner_id,
                "type": proposal_data.type,
                "status": "pending",
            },
            {"$set": {"status": "cancelled", "updated_at": datetime.now(timezone.utc)}},
        )

        now = datetime.now(timezone.utc)
        doc = {
            "type": proposal_data.type,
            "payload": proposal_data.payload,
            "status": "pending",
            "proposer_id": user_id,
            "partner_id": partner_id,
            "created_at": now,
            "updated_at": now,
        }
        result = await self.proposals_collection.insert_one(doc)
        doc["id"] = str(result.inserted_id)

        # Build a human-readable notification
        proposer_name = await self._get_user_name(user_id)
        if proposal_data.type == "start_date":
            message = f"{proposer_name} wants to change the relationship start date. Please review."
        elif proposal_data.type == "reunion_date":
            message = f"{proposer_name} wants to change the reunion date. Please review."
        else:
            message = f"{proposer_name} has proposed a change. Please review."

        await self._send_notification(
            recipient_id=partner_id,
            sender_id=user_id,
            message=message,
            metadata={"proposal_id": doc["id"], "proposal_type": proposal_data.type},
        )

        # Clean up the mongo _id before returning
        doc.pop("_id", None)
        return doc

    async def get_pending_proposals(self, user_id: str) -> List[Dict[str, Any]]:
        partner_id = await self._get_partner_id(user_id)

        # Find proposals where the user is EITHER the proposer or the partner
        query_conditions = [{"proposer_id": user_id}]
        if partner_id:
            query_conditions.append({"partner_id": user_id})

        cursor = self.proposals_collection.find(
            {"$or": query_conditions, "status": "pending"}
        )

        proposals = []
        for doc in await cursor.to_list(length=None):
            doc["id"] = str(doc["_id"])
            del doc["_id"]
            proposals.append(doc)

        return proposals

    async def approve_proposal(self, user_id: str, proposal_id: str) -> bool:
        proposal = await self.proposals_collection.find_one(
            {"_id": ObjectId(proposal_id)}
        )
        if not proposal:
            raise ValueError("Proposal not found.")

        if proposal["partner_id"] != user_id:
            raise ValueError("Only the partner can approve this proposal.")

        if proposal["status"] != "pending":
            raise ValueError("Proposal is no longer pending.")

        # Execute the actual change
        proposer_id = proposal["proposer_id"]
        if proposal["type"] == "start_date":
            new_date = proposal["payload"].get("date")
            # Update for the approver (partner). The us_service.update_start_date
            # also syncs it for the partner internally.
            await self.us_service.update_start_date(user_id, new_date)
        elif proposal["type"] == "reunion_date":
            from app.schemas.us import NextMeetCreate
            payload = proposal["payload"]
            nm = NextMeetCreate(**payload)
            # Use the approver's user_id since set_next_meet uses user_id
            await self.us_service.set_next_meet(user_id, nm)

        # Mark as approved
        await self.proposals_collection.update_one(
            {"_id": ObjectId(proposal_id)},
            {"$set": {"status": "approved", "updated_at": datetime.now(timezone.utc)}},
        )

        # Notify the proposer
        approver_name = await self._get_user_name(user_id)
        type_label = proposal["type"].replace("_", " ").title()
        await self._send_notification(
            recipient_id=proposer_id,
            sender_id=user_id,
            message=f"{approver_name} approved your {type_label} change!",
            metadata={"proposal_id": proposal_id, "action": "approved"},
        )

        return True

    async def reject_proposal(self, user_id: str, proposal_id: str) -> bool:
        proposal = await self.proposals_collection.find_one(
            {"_id": ObjectId(proposal_id)}
        )
        if not proposal:
            raise ValueError("Proposal not found.")

        if proposal["partner_id"] != user_id:
            raise ValueError("Only the partner can reject this proposal.")

        if proposal["status"] != "pending":
            raise ValueError("Proposal is no longer pending.")

        # Mark as rejected
        await self.proposals_collection.update_one(
            {"_id": ObjectId(proposal_id)},
            {"$set": {"status": "rejected", "updated_at": datetime.now(timezone.utc)}},
        )

        # Notify the proposer
        rejecter_name = await self._get_user_name(user_id)
        type_label = proposal["type"].replace("_", " ").title()
        await self._send_notification(
            recipient_id=proposal["proposer_id"],
            sender_id=user_id,
            message=f"{rejecter_name} rejected your {type_label} change.",
            metadata={"proposal_id": proposal_id, "action": "rejected"},
        )

        return True


proposal_service = ProposalService()
