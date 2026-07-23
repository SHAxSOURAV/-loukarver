from app.core.db import get_db
from bson import ObjectId
from typing import List, Dict, Any, Optional

class AdminService:
    def __init__(self):
        self._db = None

    @property
    def db(self):
        if self._db is None:
            self._db = get_db()
        return self._db

    async def get_dashboard_stats(self) -> Dict[str, Any]:
        users_col = self.db["users"]
        
        # Total Users (excluding deleted, hidden, and admins)
        total_users = await users_col.count_documents({
            "is_deleted": {"$ne": True},
            "is_hidden": {"$ne": True},
            "is_admin": {"$ne": True}
        })
        
        # Active Relationships (is_aligned=True or partner is not null)
        active_relationships = await users_col.count_documents({
            "is_deleted": {"$ne": True},
            "is_hidden": {"$ne": True},
            "is_admin": {"$ne": True},
            "$or": [
                {"is_aligned": True},
                {"partner": {"$ne": None}}
            ]
        })
        
        return {
            "total_users": total_users,
            "active_relationships": active_relationships,
            "total_earning": float("nan"),
            "active_subscriptions": 0
        }

    async def get_users(self, status_filter: str = "All") -> List[Dict[str, Any]]:
        users_col = self.db["users"]
        query = {"is_admin": {"$ne": True}}
        
        if status_filter == "Blocked":
            query["is_blocked"] = True
            query["is_deleted"] = {"$ne": True}
        elif status_filter == "Hidden":
            query["is_hidden"] = True
            query["is_deleted"] = {"$ne": True}
        elif status_filter == "Deleted":
            query["is_deleted"] = True
        else: # All active (not deleted, not hidden)
            query["is_deleted"] = {"$ne": True}
            query["is_hidden"] = {"$ne": True}

        cursor = users_col.find(query).sort("_id", -1)
        users = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            users.append(doc)
        return users

    async def update_user_status(self, user_id: str, is_blocked: Optional[bool] = None, is_hidden: Optional[bool] = None, is_deleted: Optional[bool] = None) -> Dict[str, Any]:
        users_col = self.db["users"]
        update_fields = {}
        if is_blocked is not None:
            update_fields["is_blocked"] = is_blocked
        if is_hidden is not None:
            update_fields["is_hidden"] = is_hidden
        if is_deleted is not None:
            update_fields["is_deleted"] = is_deleted
            
        if not update_fields:
            doc = await users_col.find_one({"_id": ObjectId(user_id)})
            if doc:
                doc["id"] = str(doc.pop("_id"))
            return doc
            
        await users_col.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_fields}
        )
        
        doc = await users_col.find_one({"_id": ObjectId(user_id)})
        if doc:
            doc["id"] = str(doc.pop("_id"))
        return doc

    async def get_user_growth(self, year: int) -> Dict[str, Any]:
        users_col = self.db["users"]
        # Initialize 12 months with 0
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        growth_data = {month: 0 for month in months}
        
        cursor = users_col.find({
            "is_deleted": {"$ne": True},
            "is_hidden": {"$ne": True},
            "is_admin": {"$ne": True}
        })
        async for doc in cursor:
            created_at = doc["_id"].generation_time
            if created_at.year == year:
                month_idx = created_at.month - 1
                month_name = months[month_idx]
                growth_data[month_name] += 1
                
        # Format for Recharts: [{name: "Jan", totalUser: 10}, ...]
        formatted_data = [{"name": month, "totalUser": growth_data[month]} for month in months]
        return formatted_data

    async def get_earnings_growth(self, year: int) -> Dict[str, Any]:
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        # Return zeros for now as requested
        formatted_data = [{"month": month, "value": 0} for month in months]
        return formatted_data

    async def get_recent_collaborations(self) -> List[Dict[str, Any]]:
        users_col = self.db["users"]
        # Users who are aligned or have a partner (excluding admins and hidden)
        cursor = users_col.find({
            "is_deleted": {"$ne": True},
            "is_hidden": {"$ne": True},
            "is_admin": {"$ne": True},
            "$or": [
                {"is_aligned": True},
                {"partner": {"$ne": None}}
            ]
        }).sort("_id", -1).limit(10)
        
        users = []
        async for doc in cursor:
            _id_obj = doc.pop("_id")
            doc["id"] = str(_id_obj)
            
            # Calculate duration since join
            import datetime
            now = datetime.datetime.now(datetime.timezone.utc)
            created_at = _id_obj.generation_time
            diff_days = (now - created_at).days
            
            if diff_days < 30:
                duration = f"{diff_days} Days"
            elif diff_days < 365:
                duration = f"{diff_days // 30} Months"
            else:
                duration = f"{diff_days // 365} Years"
                
            doc["join_duration"] = duration
            users.append(doc)
            
        return users

    async def get_feature_analytics(self, year: int, feature: str) -> List[Dict[str, Any]]:
        import datetime
        start_date = datetime.datetime(year, 1, 1, tzinfo=datetime.timezone.utc)
        end_date = datetime.datetime(year + 1, 1, 1, tzinfo=datetime.timezone.utc)
        
        # Determine collection and query based on feature
        if feature == "CheckIn":
            collection = self.db["checkins"]
            match_query = {"created_at": {"$gte": start_date, "$lt": end_date}}
        elif feature == "DatePlanning":
            collection = self.db["dates"]
            match_query = {"created_at": {"$gte": start_date, "$lt": end_date}}
        elif feature == "Appreciation":
            collection = self.db["thread_messages"]
            match_query = {
                "created_at": {"$gte": start_date, "$lt": end_date},
                "category": "Appreciation"
            }
        elif feature == "FutureGoal":
            collection = self.db["milestone_goals"]
            match_query = {"created_at": {"$gte": start_date, "$lt": end_date}}
        elif feature == "MapFeature":
            collection = self.db["map_places"]
            match_query = {"created_at": {"$gte": start_date, "$lt": end_date}}
        else:
            raise ValueError(f"Unknown feature: {feature}")

        pipeline = [
            {"$match": match_query},
            {"$addFields": {
                "user_id_obj": {
                    "$convert": {
                        "input": "$user_id",
                        "to": "objectId",
                        "onError": None,
                        "onNull": None
                    }
                }
            }},
            {"$lookup": {
                "from": "users",
                "localField": "user_id_obj",
                "foreignField": "_id",
                "as": "user_info"
            }},
            {"$unwind": {"path": "$user_info", "preserveNullAndEmptyArrays": True}},
            {"$addFields": {
                "month": {"$month": "$created_at"},
                "gender": {"$ifNull": ["$user_info.gender", "Unknown"]}
            }},
            {"$group": {
                "_id": {
                    "month": "$month",
                    "gender": "$gender"
                },
                "count": {"$sum": 1}
            }}
        ]
        
        cursor = collection.aggregate(pipeline)
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        results = {m: {"name": m, "Men": 0, "Women": 0} for m in months}
        
        async for doc in cursor:
            month_idx = doc["_id"].get("month")
            if not month_idx:
                continue
            
            month_name = months[month_idx - 1]
            gender_val = doc["_id"].get("gender", "Unknown")
            
            gender_lower = gender_val.lower()
            if gender_lower in ["female", "women", "w", "girl"]:
                results[month_name]["Women"] += doc["count"]
            elif gender_lower in ["male", "men", "m", "boy"]:
                results[month_name]["Men"] += doc["count"]
            # Otherwise omit from chart
                
        return list(results.values())

    async def get_collaborations(self, status: str, search: str = "") -> Dict[str, Any]:
        users_col = self.db["users"]
        
        # Base query: must have partner or be aligned, not admin, not deleted
        base_query = {
            "is_deleted": {"$ne": True},
            "is_admin": {"$ne": True},
            "$or": [
                {"is_aligned": True},
                {"partner": {"$ne": None}}
            ]
        }
        
        # Calculate total couples (all active relationships, including blocked/hidden)
        total_couples = await users_col.count_documents(base_query)
        
        # Calculate active couples (excluding blocked, hidden, deleted)
        active_query = base_query.copy()
        active_query["is_blocked"] = {"$ne": True}
        active_query["is_hidden"] = {"$ne": True}
        active_couples = await users_col.count_documents(active_query)
        
        # Filter by status
        query = base_query.copy()
        if status == "Active":
            query["is_blocked"] = {"$ne": True}
        elif status == "Blocked":
            query["is_blocked"] = True
            
        # Search by name/email
        if search:
            query["$or"] = [
                {"name": {"$regex": search, "$options": "i"}},
                {"email": {"$regex": search, "$options": "i"}}
            ]
            
        cursor = users_col.find(query).sort("_id", -1)
        users = []
        async for doc in cursor:
            _id_obj = doc.pop("_id")
            doc["id"] = str(_id_obj)
            
            # Format UI fields needed for Collaboration page
            doc["image"] = doc.get("profile_photo_url") or f"https://ui-avatars.com/api/?name={doc.get('name') or doc.get('email')}"
            
            # Get connected date
            import datetime
            connected_date = doc.get("relationship_start_date") or doc.get("created_at") or _id_obj.generation_time
            if isinstance(connected_date, str):
                try:
                    connected_date = datetime.datetime.fromisoformat(connected_date.replace("Z", "+00:00"))
                except:
                    connected_date = _id_obj.generation_time
            doc["connectedDate"] = connected_date.strftime("%Y-%m-%d")
            
            now = datetime.datetime.now(datetime.timezone.utc)
            if connected_date.tzinfo is None:
                connected_date = connected_date.replace(tzinfo=datetime.timezone.utc)
            diff_days = max(0, (now - connected_date).days)
            
            if diff_days < 30:
                doc["duration"] = f"{diff_days} Days"
            elif diff_days < 365:
                doc["duration"] = f"{diff_days // 30} Months"
            else:
                doc["duration"] = f"{diff_days // 365} Years"
                
            doc["subscription"] = doc.get("subscription_plan") or "Free"
            doc["relationship"] = "Couple" if doc.get("partner") else "Single"
            
            users.append(doc)
            
        return {
            "total_couples": total_couples,
            "active_couples": active_couples,
            "collaborators": users
        }

admin_service = AdminService()
