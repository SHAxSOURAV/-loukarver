from pydantic import BaseModel, Field
from typing import Optional

class LegalDocumentUpdate(BaseModel):
    content: str = Field(..., description="The HTML or Markdown content of the document")
    
class LegalDocumentResponse(BaseModel):
    id: str
    doc_type: str
    content: str
    updated_at: str
