from pydantic import BaseModel, Field, AliasChoices
from typing import Optional
from datetime import datetime

class FAQBase(BaseModel):
    question: str = Field(..., description="The FAQ question")
    answer: str = Field(..., description="The FAQ answer")

class FAQCreate(FAQBase):
    pass

class FAQUpdate(BaseModel):
    question: Optional[str] = None
    answer: Optional[str] = None

class FAQResponse(FAQBase):
    id: str = Field(..., validation_alias=AliasChoices("id", "_id"))
    created_at: datetime
    updated_at: datetime
    
    model_config = {
        "populate_by_name": True
    }
