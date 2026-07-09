from pydantic import BaseModel, Field
from typing import Optional, Any, Dict
from datetime import datetime

class ProposalCreate(BaseModel):
    type: str = Field(..., description="Type of proposal (start_date, reunion_date)", examples=["start_date"])
    payload: Dict[str, Any] = Field(..., description="The data being proposed")

class ProposalResponse(BaseModel):
    id: str
    type: str
    payload: Dict[str, Any]
    status: str
    proposer_id: str
    partner_id: str
    created_at: datetime
    updated_at: datetime

class GenericProposalResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None
