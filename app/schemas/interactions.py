from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class InteractionState(BaseModel):
    partner_name: str
    received_count: int
    received_last_activity: Optional[datetime] = None
    sent_count: int
    sent_last_activity: Optional[datetime] = None

class InteractionResponse(BaseModel):
    success: bool
    data: InteractionState

class GenericResponse(BaseModel):
    success: bool
    message: str

class PokeRequest(BaseModel):
    partner_id: Optional[str] = None
