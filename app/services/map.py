import os
import uuid
import zoneinfo
import httpx
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.db import get_client, get_db

from bson import ObjectId
from datetime import datetime, timezone
from fastapi import UploadFile

from app.core.config import settings
from app.services.s3_utils import s3_service
from app.schemas.map import (
    PlaceCreate, PlaceUpdate, PlaceCategory, MomentCreate, MomentType
)
from pymongo import ReturnDocument

class MapService:
    def __init__(self) -> None:
        self.client = get_client()
        self.db = get_db()
        self.places_collection = self.db["map_places"]
        self.users = self.db["users"]

    async def init_indexes(self):
        try:
            await self.places_collection.create_index([("creator_id", 1), ("created_at", -1)])
            await self.places_collection.create_index([("partner_id", 1), ("created_at", -1)])
            await self.places_collection.create_index([("creator_id", 1), ("partner_id", 1)])
            await self.places_collection.create_index("category")
            await self.places_collection.create_index("city")
        except Exception as e:
            print(f"Index initialization note in map: {e}")

    async def _get_partner_id(self, user_id: str) -> Optional[str]:
        user = await self.users.find_one({"_id": ObjectId(user_id)}, {"partner.user_id": 1, "is_aligned": 1})
        if user and user.get("is_aligned") and user.get("partner"):
            return user["partner"]["user_id"]
        return None

    async def _get_names(self, user_id: str, partner_id: str) -> Dict[str, str]:
        names = {user_id: "User", partner_id: "Partner"}
        ids = [ObjectId(user_id)]
        if partner_id:
            try:
                ids.append(ObjectId(partner_id))
            except Exception:
                pass
        cursor = self.users.find({"_id": {"$in": ids}}, {"name": 1})
        async for user in cursor:
            names[str(user["_id"])] = user.get("name", "User")
        return names

    async def _geocode(self, city: str, country: str) -> Tuple[float, float]:
        """Resilient geocoding with multiple providers and fast fallback."""
        if not city or not country:
            return 0.0, 0.0

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AlignedTracker/1.0",
            "Accept-Language": "en"
        }

        providers = [
            # Provider 1: Nominatim (Primary)
            {
                "url": "https://nominatim.openstreetmap.org/search",
                "params": {"q": f"{city}, {country}", "format": "json", "limit": 1}
            },
            # Provider 2: geocode.maps.co (Secondary Fallback)
            {
                "url": "https://geocode.maps.co/search",
                "params": {"q": f"{city} {country}"}
            }
        ]

        async with httpx.AsyncClient(timeout=4.0, verify=False) as client:
            for provider in providers:
                try:
                    response = await client.get(provider["url"], params=provider["params"], headers=headers)
                    if response.status_code == 200:
                        data = response.json()
                        if data and isinstance(data, list) and len(data) > 0:
                            return float(data[0]["lat"]), float(data[0]["lon"])
                except Exception:
                    continue
        
        return 0.0, 0.0

    async def _async_repair_geocode(self, place_id: str, city: str, country: str):
        """Asynchronously geocodes a place in the background without blocking GET requests."""
        try:
            new_lat, new_lng = await self._geocode(city, country)
            if new_lat != 0.0 or new_lng != 0.0:
                await self.places_collection.update_one(
                    {"_id": ObjectId(place_id)},
                    {"$set": {"lat": new_lat, "lng": new_lng}}
                )
        except Exception:
            pass

    async def create_place(self, user_id: str, payload: PlaceCreate) -> Dict[str, Any]:
        partner_id = await self._get_partner_id(user_id)
        if not partner_id:
            raise ValueError("Partner alignment required.")

        lat, lng = await self._geocode(payload.city, payload.country)
        
        new_doc = payload.model_dump()
        new_doc["creator_id"] = user_id
        new_doc["partner_id"] = partner_id
        new_doc["lat"] = lat
        new_doc["lng"] = lng
        new_doc["moments"] = []
        new_doc["created_at"] = datetime.now(timezone.utc)
        new_doc["updated_at"] = datetime.now(timezone.utc)

        result = await self.places_collection.insert_one(new_doc)
        new_doc["id"] = str(result.inserted_id)

        if partner_id:
            from app.core.websocket import ws_manager
            await ws_manager.broadcast_to_user(partner_id, {"type": "MAP_UPDATED"})

        return await self._map_place(new_doc, payload.timezone, user_id)

    async def get_places(self, user_id: str, category: Optional[PlaceCategory] = None, search: Optional[str] = None, page: int = 1, size: int = 20, user_timezone: str = "UTC", partner_id: Optional[str] = None) -> Tuple[List[Dict[str, Any]], int]:
        if not partner_id:
            partner_id = await self._get_partner_id(user_id)
            
        user_ids = [user_id]
        if partner_id:
            user_ids.append(partner_id)

        user_filter = {"$or": [{"creator_id": {"$in": user_ids}}, {"partner_id": {"$in": user_ids}}]}
        conditions = [user_filter]
        
        if category:
            conditions.append({"category": category})
        if search:
            search_regex = {"$regex": search, "$options": "i"}
            conditions.append({
                "$or": [
                    {"city": search_regex},
                    {"country": search_regex},
                    {"description": search_regex}
                ]
            })

        query = {"$and": conditions} if len(conditions) > 1 else user_filter

        skip = (page - 1) * size
        cursor = self.places_collection.find(query).sort("created_at", -1).skip(skip).limit(size)
        
        docs_task = cursor.to_list(length=size)
        total_task = self.places_collection.count_documents(query)
        names_task = self._get_names(user_id, partner_id or "")
        
        docs, total, names = await asyncio.gather(docs_task, total_task, names_task)

        results = [await self._map_place(d, user_timezone, user_id, names=names) for d in docs]
        return results, total

    async def get_place_by_id(self, place_id: str, user_id: str, user_timezone: str = "UTC") -> Optional[Dict[str, Any]]:
        partner_id = await self._get_partner_id(user_id)
        user_ids = [user_id]
        if partner_id: user_ids.append(partner_id)
        
        doc = await self.places_collection.find_one({
            "_id": ObjectId(place_id),
            "$or": [{"creator_id": {"$in": user_ids}}, {"partner_id": {"$in": user_ids}}]
        })
        if doc:
            names = await self._get_names(user_id, partner_id or "")
            return await self._map_place(doc, user_timezone, user_id, names=names)
        return None

    async def update_place(self, place_id: str, user_id: str, payload: PlaceUpdate) -> Dict[str, Any]:
        doc = await self.places_collection.find_one({
            "_id": ObjectId(place_id),
            "$or": [{"creator_id": user_id}, {"partner_id": user_id}]
        })
        if not doc:
            raise ValueError("Place not found or permission denied.")

        updates = payload.model_dump(exclude_unset=True)
        if not updates:
            return await self._map_place(doc, payload.timezone, user_id)

        if "city" in updates or "country" in updates:
            city = updates.get("city", doc["city"])
            country = updates.get("country", doc["country"])
            lat, lng = await self._geocode(city, country)
            updates["lat"] = lat
            updates["lng"] = lng

        updates["updated_at"] = datetime.now(timezone.utc)
        
        result = await self.places_collection.find_one_and_update(
            {"_id": ObjectId(place_id)},
            {"$set": updates},
            return_document=ReturnDocument.AFTER
        )

        partner_id = await self._get_partner_id(user_id)
        if partner_id:
            from app.core.websocket import ws_manager
            await ws_manager.broadcast_to_user(partner_id, {"type": "MAP_UPDATED"})

        return await self._map_place(result, payload.timezone, user_id)

    async def delete_place(self, place_id: str, user_id: str) -> bool:
        doc = await self.places_collection.find_one({
            "_id": ObjectId(place_id),
            "$or": [{"creator_id": user_id}, {"partner_id": user_id}]
        })
        if not doc:
            return False
            
        result = await self.places_collection.delete_one({"_id": ObjectId(place_id)})
        
        if result.deleted_count > 0:
            partner_id = await self._get_partner_id(user_id)
            if partner_id:
                from app.core.websocket import ws_manager
                await ws_manager.broadcast_to_user(partner_id, {"type": "MAP_UPDATED"})
            return True
        return False

    async def request_delete_place(self, place_id: str, user_id: str, user_timezone: str = "UTC") -> Dict[str, Any]:
        doc = await self.places_collection.find_one({
            "_id": ObjectId(place_id),
            "$or": [{"creator_id": user_id}, {"partner_id": user_id}]
        })
        if not doc:
            raise ValueError("Place not found or permission denied.")

        partner_id = await self._get_partner_id(user_id)
        
        # Check if partner has contributed any moments
        has_partner_contribution = False
        if partner_id:
            for m in doc.get("moments", []):
                if str(m.get("creator_id")) == str(partner_id):
                    has_partner_contribution = True
                    break

        if not has_partner_contribution:
            # Delete immediately
            await self.places_collection.delete_one({"_id": ObjectId(place_id)})
            if partner_id:
                from app.core.websocket import ws_manager
                await ws_manager.broadcast_to_user(partner_id, {"type": "MAP_UPDATED"})
            return {"id": place_id, "deleted": True}

        # Otherwise, initiate approval request
        names = await self._get_names(user_id, partner_id or "")
        user_name = names.get(user_id, "User")
        
        deletion_request = {
            "requested_by": user_id,
            "requested_by_name": user_name,
            "created_at": datetime.now(timezone.utc)
        }

        result = await self.places_collection.find_one_and_update(
            {"_id": ObjectId(place_id)},
            {"$set": {"deletion_request": deletion_request}},
            return_document=ReturnDocument.AFTER
        )

        if partner_id:
            from app.core.websocket import ws_manager
            await ws_manager.broadcast_to_user(partner_id, {"type": "MAP_UPDATED"})

        return await self._map_place(result, user_timezone, user_id)

    async def approve_delete_place(self, place_id: str, user_id: str) -> bool:
        doc = await self.places_collection.find_one({
            "_id": ObjectId(place_id),
            "$or": [{"creator_id": user_id}, {"partner_id": user_id}]
        })
        if not doc or not doc.get("deletion_request"):
            return False

        await self.places_collection.delete_one({"_id": ObjectId(place_id)})
        
        partner_id = await self._get_partner_id(user_id)
        if partner_id:
            from app.core.websocket import ws_manager
            await ws_manager.broadcast_to_user(partner_id, {"type": "MAP_UPDATED"})
        return True

    async def reject_delete_place(self, place_id: str, user_id: str, user_timezone: str = "UTC") -> Dict[str, Any]:
        doc = await self.places_collection.find_one({
            "_id": ObjectId(place_id),
            "$or": [{"creator_id": user_id}, {"partner_id": user_id}]
        })
        if not doc or not doc.get("deletion_request"):
            raise ValueError("No pending deletion request found.")

        result = await self.places_collection.find_one_and_update(
            {"_id": ObjectId(place_id)},
            {"$unset": {"deletion_request": ""}},
            return_document=ReturnDocument.AFTER
        )

        partner_id = await self._get_partner_id(user_id)
        if partner_id:
            from app.core.websocket import ws_manager
            await ws_manager.broadcast_to_user(partner_id, {"type": "MAP_UPDATED"})

        return await self._map_place(result, user_timezone, user_id)

    # --- Moment Management ---

    async def add_moment(self, place_id: str, user_id: str, payload: MomentCreate, file: Optional[UploadFile] = None) -> Dict[str, Any]:
        doc = await self.places_collection.find_one({
            "_id": ObjectId(place_id),
            "$or": [{"creator_id": user_id}, {"partner_id": user_id}]
        })
        if not doc:
            raise ValueError("Place not found.")

        content = payload.content
        if payload.type == MomentType.PHOTO and file:
            content = await s3_service.upload_file(file, folder="map_moments")
        
        new_moment = {
            "id": str(uuid.uuid4()),
            "type": payload.type,
            "content": content,
            "caption": payload.caption,
            "creator_id": user_id,
            "created_at": datetime.now(timezone.utc)
        }

        result = await self.places_collection.find_one_and_update(
            {"_id": ObjectId(place_id)},
            {"$push": {"moments": new_moment}, "$set": {"updated_at": datetime.now(timezone.utc)}},
            return_document=ReturnDocument.AFTER
        )

        partner_id = await self._get_partner_id(user_id)
        if partner_id:
            from app.core.websocket import ws_manager
            await ws_manager.broadcast_to_user(partner_id, {"type": "MAP_UPDATED"})

        return await self._map_place(result, payload.timezone, user_id)


    # --- Stats & Overview ---

    async def get_stats(self, user_id: str, partner_id: Optional[str] = None, user_doc: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not partner_id:
            partner_id = user_doc.get("partner", {}).get("user_id") if user_doc and user_doc.get("is_aligned") and user_doc.get("partner") else None
            if partner_id is None and not user_doc:
                partner_id = await self._get_partner_id(user_id)
        user_ids = [user_id]
        if partner_id: user_ids.append(partner_id)
        
        query = {"creator_id": {"$in": user_ids}}
        projection = {"country": 1, "city": 1, "category": 1, "_id": 0}
        places = await self.places_collection.find(query, projection).to_list(length=None)
        
        countries = set(p.get("country", "") for p in places if p.get("country"))
        cities = set(p.get("city", "") for p in places if p.get("city"))
        
        together_count = sum(1 for p in places if p.get("category") == PlaceCategory.TOGETHER)
        bucket_count = sum(1 for p in places if p.get("category") == PlaceCategory.BUCKET)
        upcoming_count = sum(1 for p in places if p.get("category") == PlaceCategory.UPCOMING)
        home_count = sum(1 for p in places if p.get("category") == PlaceCategory.HOME)

        return {
            "total_countries": len(countries),
            "total_cities": len(cities),
            "together_count": together_count,
            "bucket_count": bucket_count,
            "upcoming_count": upcoming_count,
            "home_count": home_count
        }

    async def get_overview(self, user_id: str, user_timezone: str = "UTC", partner_id: Optional[str] = None) -> Dict[str, Any]:
        if not partner_id:
            partner_id = await self._get_partner_id(user_id)
        user_ids = [user_id]
        if partner_id: user_ids.append(partner_id)
        
        query = {"creator_id": {"$in": user_ids}}
        
        places_task = self.places_collection.find(query).sort("created_at", 1).to_list(length=None)
        names_task = self._get_names(user_id, partner_id or "")
        places_docs, names = await asyncio.gather(places_task, names_task)
        
        places = []
        for d in places_docs:
            places.append(await self._map_place(d, user_timezone, user_id, names=names))
        
        # Calculate Routes: chronological connection of "Together" places
        together_places = [p for p in places if p["category"] == PlaceCategory.TOGETHER]
        def sort_key(p):
            if p.get("visit_date"):
                try:
                    return datetime.strptime(p["visit_date"], "%m.%d.%Y")
                except: pass
            return p["created_at"]
        
        together_places.sort(key=sort_key)
        
        routes = []
        if len(together_places) > 1:
            points = []
            for p in together_places:
                points.append({"lat": p["lat"], "lng": p["lng"], "city": p["city"]})
            
            routes.append({
                "name": "Our Journey Together",
                "points": points
            })
            
        # Compute stats directly from places_docs without duplicate DB scan
        countries = set(p.get("country", "") for p in places_docs if p.get("country"))
        cities = set(p.get("city", "") for p in places_docs if p.get("city"))
        
        together_count = sum(1 for p in places_docs if p.get("category") == PlaceCategory.TOGETHER)
        bucket_count = sum(1 for p in places_docs if p.get("category") == PlaceCategory.BUCKET)
        upcoming_count = sum(1 for p in places_docs if p.get("category") == PlaceCategory.UPCOMING)
        home_count = sum(1 for p in places_docs if p.get("category") == PlaceCategory.HOME)

        stats = {
            "total_countries": len(countries),
            "total_cities": len(cities),
            "together_count": together_count,
            "bucket_count": bucket_count,
            "upcoming_count": upcoming_count,
            "home_count": home_count
        }
        
        return {
            "places": places,
            "routes": routes,
            "stats": stats
        }

    async def _map_place(self, d: Dict[str, Any], user_timezone: str, current_user_id: str, names: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        place_id = str(d["_id"]) if "_id" in d else d.get("id")
        d["id"] = place_id
        if "_id" in d: del d["_id"]
        
        # --- NON-BLOCKING AUTO-REPAIR ---
        # If coordinates are missing (0,0), trigger background geocoding without stalling the GET response
        if d.get("lat") == 0.0 and d.get("lng") == 0.0 and d.get("city") and d.get("country"):
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._async_repair_geocode(place_id, d["city"], d["country"]))
            except Exception:
                pass
        
        if names is None:
            partner_id = await self._get_partner_id(current_user_id)
            names = await self._get_names(current_user_id, partner_id or "")

        # Personalization: Add creator name
        d["creator_name"] = names.get(str(d.get("creator_id")), "User")

        try:
            tz = zoneinfo.ZoneInfo(user_timezone)
        except Exception:
            tz = zoneinfo.ZoneInfo("UTC")

        # Convert timestamps
        for field in ["created_at", "updated_at"]:
            dt = d.get(field)
            if isinstance(dt, datetime):
                if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
                d[field] = dt.astimezone(tz)

        # Map deletion_request
        if "deletion_request" in d and d["deletion_request"]:
            req = d["deletion_request"]
            dt = req.get("created_at")
            if isinstance(dt, datetime):
                if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
                req["created_at"] = dt.astimezone(tz)

        # Map moments
        for m in d.get("moments", []):
            m["creator_name"] = names.get(str(m["creator_id"]), "User")
            dt = m.get("created_at")
            if isinstance(dt, datetime):
                if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
                m["created_at"] = dt.astimezone(tz)

        return d

map_service = MapService()
