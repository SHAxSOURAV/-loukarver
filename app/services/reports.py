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

    async def create_report(self, user_id: str, title: str, description: str, file_url: Optional[str] = None) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        report_doc = {
            "user_id": user_id,
            "title": title,
            "description": description,
            "status": "Pending",
            "file_url": file_url,
            "created_at": now,
            "updated_at": now
        }
        res = await self.reports.insert_one(report_doc)
        report_doc["id"] = str(res.inserted_id)
        report_doc.pop("_id", None)
        
        # Initial message
        await self.add_message(report_doc["id"], user_id, "user", description, file_url)
        
        return report_doc

    async def get_user_reports(self, user_id: str) -> List[Dict[str, Any]]:
        cursor = self.reports.find({"user_id": user_id}).sort("updated_at", -1)
        results = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            results.append(doc)
        return results

    async def get_all_reports(self, status: str = "All", search: str = "") -> List[Dict[str, Any]]:
        query = {}
        if status != "All":
            query["status"] = status
            
        # We need to manually join with users to search by name/email, 
        # but for simplicity we can just fetch reports and join in python since there shouldn't be millions of active reports.
        
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
        results = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            user_info = doc.pop("user_info", {})
            doc["user_name"] = user_info.get("name", "Unknown")
            doc["user_email"] = user_info.get("email", "Unknown")
            doc["user_image"] = user_info.get("profile_photo_url")
            results.append(doc)
        return results

    async def update_report_status(self, report_id: str, status: str) -> Dict[str, Any]:
        res = await self.reports.find_one_and_update(
            {"_id": ObjectId(report_id)},
            {"$set": {"status": status, "updated_at": datetime.now(timezone.utc)}},
            return_document=True
        )
        if res:
            res["id"] = str(res.pop("_id"))
            
            # Broadcast to user
            await ws_manager.broadcast_to_user(res["user_id"], {
                "type": "REPORT_UPDATED",
                "report_id": res["id"],
                "status": status
            })
            return res
        return None

    async def get_messages(self, report_id: str) -> List[Dict[str, Any]]:
        cursor = self.report_messages.find({"report_id": report_id}).sort("created_at", 1)
        results = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            results.append(doc)
        return results

    async def add_message(self, report_id: str, sender_id: str, sender_type: str, message: str, file_url: Optional[str] = None) -> Dict[str, Any]:
        msg_doc = {
            "report_id": report_id,
            "sender_id": sender_id,
            "sender_type": sender_type,
            "message": message,
            "file_url": file_url,
            "created_at": datetime.now(timezone.utc)
        }
        res = await self.report_messages.insert_one(msg_doc)
        msg_doc["id"] = str(res.inserted_id)
        msg_doc.pop("_id", None)
        
        # Update report's updated_at
        report = await self.reports.find_one_and_update(
            {"_id": ObjectId(report_id)},
            {"$set": {"updated_at": datetime.now(timezone.utc)}},
            return_document=True
        )
        
        # If admin replies, broadcast to user
        if sender_type == "admin" and report:
            user_id = report.get("user_id")
            await ws_manager.broadcast_to_user(user_id, {
                "type": "NEW_REPORT_MESSAGE",
                "report_id": report_id,
                "message": msg_doc
            })
            
        # We can also trigger a push notification here if we want, using NotificationService.
        if sender_type == "admin" and report:
            user_id = report.get("user_id")
            from app.services.notification import NotificationService
            notif_service = NotificationService()
            import asyncio
            asyncio.create_task(notif_service.send_onesignal_push(
                user_id=user_id,
                title="Support Update",
                message=f"Admin replied to your ticket: {report.get('title')}",
                custom_data={"type": "report", "report_id": report_id}
            ))

        return msg_doc

report_service = ReportService()
