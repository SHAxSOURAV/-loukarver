from typing import Optional
from datetime import datetime, timezone
from app.core.db import get_client, get_db
from app.schemas.legal import LegalDocumentUpdate

class LegalService:
    def __init__(self) -> None:
        self.db = get_db()
        self.collection = self.db["legal_docs"]

    async def get_document(self, doc_type: str) -> Optional[dict]:
        """Retrieves a legal document by its type (e.g., 'privacy', 'terms')."""
        doc = await self.collection.find_one({"doc_type": doc_type})
        if doc and "_id" in doc:
            doc["id"] = str(doc["_id"])
            doc["_id"] = str(doc["_id"])
        return doc

    async def update_document(self, doc_type: str, payload: LegalDocumentUpdate) -> dict:
        """Updates or creates a legal document."""
        now_str = datetime.now(timezone.utc).isoformat()
        
        updated_doc = await self.collection.find_one_and_update(
            {"doc_type": doc_type},
            {"$set": {
                "content": payload.content,
                "updated_at": now_str
            }},
            upsert=True,
            return_document=True
        )
        
        if updated_doc and "_id" in updated_doc:
            updated_doc["id"] = str(updated_doc["_id"])
            updated_doc["_id"] = str(updated_doc["_id"])
            
        return updated_doc

legal_service = LegalService()
