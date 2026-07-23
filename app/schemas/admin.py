from pydantic import BaseModel
from typing import List, Optional
from app.schemas.auth import UserMeResponse

class DashboardStatsResponse(BaseModel):
    total_users: int
    active_relationships: int
    total_earning: float
    active_subscriptions: int

class UserStatusUpdate(BaseModel):
    is_blocked: Optional[bool] = None
    is_hidden: Optional[bool] = None
    is_deleted: Optional[bool] = None
