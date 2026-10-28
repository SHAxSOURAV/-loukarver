import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from bson import ObjectId

from app.core.db import get_client, get_db
from app.core.websocket import ws_manager
from app.services.notification import notification_service
from app.schemas.notification import NotificationCreate, NotificationType

class AlignmentRequestService:
    def __init__(self) -> None:
        self.client = get_client()
        self.db = get_db()
        self.collection = self.db["users"]
        self.requests_collection = self.db["alignment_requests"]

    async def init_indexes(self):
        try:
            await self.requests_collection.create_index([("sender_id", 1), ("status", 1)])
            await self.requests_collection.create_index([("receiver_id", 1), ("status", 1)])
            await self.requests_collection.create_index([("sender_id", 1), ("receiver_id", 1), ("status", 1)])
        except Exception as e:
            print(f"Index initialization note in alignment_requests: {e}")

    async def create_alignment_request(self, user_id: str, partner_secret_key: str) -> Dict[str, Any]:
        """Creates a pending alignment connection request to the partner identified by secret key."""
        initiator = await self.collection.find_one({"_id": ObjectId(user_id)})
        if not initiator:
            raise ValueError("User not found.")
            
        if initiator.get("is_aligned"):
            raise ValueError("You are already connected to a partner.")

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
                return await self.respond_alignment_request(user_id=user_id, request_id=str(existing_active["_id"]), accept=True)
            elif existing_active.get("sender_id") == user_id:
                await self.requests_collection.update_many(
                    {"sender_id": user_id, "status": "pending"},
                    {"$set": {"status": "cancelled", "updated_at": datetime.now(timezone.utc)}}
                )

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
        if not user:
            user = await self.collection.find_one({"_id": ObjectId(user_id)})
        if not user or user.get("is_aligned"):
            await self.requests_collection.update_many(
                {
                    "status": "pending",
                    "$or": [{"sender_id": user_id}, {"receiver_id": user_id}]
                },
                {"$set": {"status": "cancelled", "updated_at": datetime.now(timezone.utc)}}
            )
            return {"is_aligned": True, "incoming": None, "incoming_list": [], "outgoing": None}

        now = datetime.now(timezone.utc)

        incoming_task = self.requests_collection.find({
            "receiver_id": user_id,
            "status": "pending"
        }).sort("created_at", -1).to_list(length=50)

        outgoing_task = self.requests_collection.find_one({
            "sender_id": user_id,
            "status": "pending"
        })

        raw_incoming, outgoing = await asyncio.gather(incoming_task, outgoing_task)

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
            sender = await self.collection.find_one({"_id": ObjectId(sender_id)})
            receiver = await self.collection.find_one({"_id": ObjectId(user_id)})

            if not sender or not receiver:
                raise ValueError("User accounts not found.")
                
            if sender.get("is_aligned"):
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

            await self.requests_collection.update_one(
                {"_id": ObjectId(request_id)},
                {"$set": {"status": "accepted", "updated_at": now}}
            )

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
            await self.requests_collection.update_one(
                {"_id": ObjectId(request_id)},
                {"$set": {"status": "rejected", "updated_at": now}}
            )

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

        try:
            await ws_manager.broadcast_to_user(
                user_id=req["receiver_id"],
                message={"type": "ALIGNMENT_REQUEST_CANCELLED", "request_id": request_id}
            )
        except Exception as e:
            print("Error broadcasting cancel ws event:", e)

        return {"status": "cancelled"}

alignment_request_service = AlignmentRequestService()

