import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from bson import ObjectId
from app.core.db import get_client, get_db
from app.core.websocket import ws_manager

class ReportService:
    def __init__(self):
        self.client = get_client()
        self.db = get_db()
        self.reports = self.db["reports"]
        self.report_messages = self.db["report_messages"]

    async def init_indexes(self):
        """Ensure high-performance indexes for report lookups and chat history."""
        try:
            await self.reports.create_index([("user_id", 1), ("updated_at", -1)])
            await self.reports.create_index([("status", 1), ("updated_at", -1)])
            await self.reports.create_index("updated_at")
            await self.report_messages.create_index([("report_id", 1), ("created_at", 1)])
        except Exception as e:
            print(f"Error initializing report indexes: {e}")

    async def create_report(self, user_id: str, title: str, description: str, file_url: Optional[str] = None) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        report_id = ObjectId()
        report_id_str = str(report_id)

        report_doc = {
            "_id": report_id,
            "user_id": user_id,
            "title": title,
            "description": description,
            "status": "Pending",
            "file_url": file_url,
            "created_at": now,
            "updated_at": now
        }

        msg_doc = {
            "report_id": report_id_str,
            "sender_id": user_id,
            "sender_type": "user",
            "message": description,
            "file_url": file_url,
            "created_at": now
        }

        # Concurrently insert report and initial message in 1 roundtrip
        await asyncio.gather(
            self.reports.insert_one(report_doc),
            self.report_messages.insert_one(msg_doc)
        )

        report_doc["id"] = report_id_str
        report_doc.pop("_id", None)
        return report_doc

    async def get_user_reports(self, user_id: str) -> List[Dict[str, Any]]:
        docs = await self.reports.find({"user_id": user_id}).sort("updated_at", -1).to_list(length=200)
        for doc in docs:
            doc["id"] = str(doc.pop("_id"))
        return docs

    async def get_all_reports(self, status: str = "All", search: str = "") -> List[Dict[str, Any]]:
        query = {}
        if status != "All":
            query["status"] = status

        pipeline = [
            {"$match": query},
            {"$sort": {"updated_at": -1}},
            {
                "$lookup": {
                    "from": "users",
                    "let": {"uid": {"$toObjectId": "$user_id"}},
                    "pipeline": [
                        {"$match": {"$expr": {"$eq": ["$_id", "$$uid"]}}}
                    ],
                    "as": "user_info"
                }
            },
            {"$unwind": {"path": "$user_info", "preserveNullAndEmptyArrays": True}}
        ]

        if search:
            search_regex = {"$regex": search, "$options": "i"}
            pipeline.append({
                "$match": {
                    "$or": [
                        {"user_info.name": search_regex},
                        {"user_info.email": search_regex},
                        {"title": search_regex}
                    ]
                }
            })

        cursor = self.reports.aggregate(pipeline)
        docs = await cursor.to_list(length=200)
        results = []
        for doc in docs:
            doc["id"] = str(doc.pop("_id"))
            user_info = doc.pop("user_info", {})
            doc["user_name"] = user_info.get("name", "Unknown")
            doc["user_email"] = user_info.get("email", "Unknown")
            doc["user_image"] = user_info.get("profile_photo_url")
            results.append(doc)
        return results

    async def update_report_status(self, report_id: str, status: str) -> Optional[Dict[str, Any]]:
        res = await self.reports.find_one_and_update(
            {"_id": ObjectId(report_id)},
            {"$set": {"status": status, "updated_at": datetime.now(timezone.utc)}},
            return_document=True
        )
        if res:
            res["id"] = str(res.pop("_id"))

            # Broadcast to user non-blockingly
            asyncio.create_task(ws_manager.broadcast_to_user(res["user_id"], {
                "type": "REPORT_UPDATED",
                "report_id": res["id"],
                "status": status
            }))
            return res
        return None

    async def get_messages(self, report_id: str) -> List[Dict[str, Any]]:
        docs = await self.report_messages.find({"report_id": report_id}).sort("created_at", 1).to_list(length=500)
        for doc in docs:
            doc["id"] = str(doc.pop("_id"))
        return docs

    async def add_message(self, report_id: str, sender_id: str, sender_type: str, message: str, file_url: Optional[str] = None) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        msg_doc = {
            "report_id": report_id,
            "sender_id": sender_id,
            "sender_type": sender_type,
            "message": message,
            "file_url": file_url,
            "created_at": now
        }

        # Concurrently insert message and update report's updated_at
        res, report = await asyncio.gather(
            self.report_messages.insert_one(msg_doc),
            self.reports.find_one_and_update(
                {"_id": ObjectId(report_id)},
                {"$set": {"updated_at": now}},
                return_document=True
            )
        )
        msg_doc["id"] = str(res.inserted_id)
        msg_doc.pop("_id", None)

        # If admin replies, broadcast and send push in background
        if sender_type == "admin" and report:
            user_id = report.get("user_id")
            if user_id:
                asyncio.create_task(ws_manager.broadcast_to_user(user_id, {
                    "type": "NEW_REPORT_MESSAGE",
                    "report_id": report_id,
                    "message": msg_doc
                }))

                from app.services.notification import NotificationService
                notif_service = NotificationService()
                asyncio.create_task(notif_service.send_onesignal_push(
                    user_id=user_id,
                    title="Support Update",
                    message=f"Admin replied to your ticket: {report.get('title')}",
                    custom_data={"type": "report", "report_id": report_id}
                ))

        return msg_doc

report_service = ReportService()
