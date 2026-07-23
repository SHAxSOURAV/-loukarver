from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.db import get_db
from app.schemas.faq import FAQCreate, FAQUpdate
from bson import ObjectId
import datetime

class FAQService:
    def __init__(self):
        self._db = None

    @property
    def collection(self):
        if self._db is None:
            self._db = get_db()
        return self._db["faqs"]
        
    async def get_all(self):
        faqs = []
        cursor = self.collection.find({}).sort("created_at", -1)
        async for doc in cursor:
            doc["id"] = str(doc["_id"])
            faqs.append(doc)
        return faqs
        
    async def create(self, payload: FAQCreate):
        faq_doc = payload.model_dump()
        now = datetime.datetime.now(datetime.timezone.utc)
        faq_doc["created_at"] = now
        faq_doc["updated_at"] = now
        
        result = await self.collection.insert_one(faq_doc)
        faq_doc["id"] = str(result.inserted_id)
        return faq_doc
        
    async def update(self, faq_id: str, payload: FAQUpdate):
        update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
        if not update_data:
            return await self.get_by_id(faq_id)
            
        update_data["updated_at"] = datetime.datetime.now(datetime.timezone.utc)
        
        await self.collection.update_one(
            {"_id": ObjectId(faq_id)},
            {"$set": update_data}
        )
        return await self.get_by_id(faq_id)
        
    async def get_by_id(self, faq_id: str):
        doc = await self.collection.find_one({"_id": ObjectId(faq_id)})
        if doc:
            doc["id"] = str(doc["_id"])
        return doc
        
    async def delete(self, faq_id: str):
        result = await self.collection.delete_one({"_id": ObjectId(faq_id)})
        return result.deleted_count > 0

faq_service = FAQService()
