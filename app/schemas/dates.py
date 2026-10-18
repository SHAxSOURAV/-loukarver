from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum

class DateMood(str, Enum):
    ROMANTIC = "Romantic"
    PLAYFUL = "Playful"
    ADVENTUROUS = "Adventurous"
    RELAXED = "Relaxed"
    INTIMATE = "Intimate"
    SPONTANEOUS = "Spontaneous"
    SOPHISTICATED = "Sophisticated"
    CREATIVE = "Creative"

class DateVibe(str, Enum):
    OUTDOORSY = "Outdoorsy"
    FOODIE = "Foodie"
    CULTURAL = "Cultural"
    NIGHTLIFE = "Nightlife"
    COZY = "Cozy"
    ACTIVE = "Active"
    ARTISTIC = "Artistic"
    CHILL = "Chill"
    GLAMOROUS = "Glamorous"

class DateStatus(str, Enum):
    PROPOSED = "Proposed"
    ACCEPTED = "Accepted"
    REJECTED = "Rejected"
    COMPLETED = "Completed"
    CANCEL_REQUESTED = "CancelRequested"
    CANCELLED = "Cancelled"

class DateReview(BaseModel):
    user_id: str
    user_name: Optional[str] = None
    rating: int = Field(..., ge=1, le=5)
    text: str
    photos: List[str] = []

class DateReviewRead(BaseModel):
    user_id: str
    user_name: str
    rating: int
    text: str
    photos: List[str] = []

class DateReviewsResponse(BaseModel):
    success: bool
    data: List[DateReviewRead]

class VenueSuggestRequest(BaseModel):
    city: str
    mood: Optional[str] = "Romantic"
    vibe: Optional[str] = "Cozy"

class VenueSuggestResponse(BaseModel):
    success: bool = True
    venue: str
    location: str
    title: str
    note: str
    city: str

class DateBase(BaseModel):
    title: Optional[str] = None
    where: str = Field(..., description="Location name or place")
    date: str = Field(..., description="Date of the date, e.g. '12.25.2023'")
    time: str = Field(..., description="Time of the date, e.g. '09:00 PM'")
    how_we_meet: str
    note: Optional[str] = None
    timezone: str = Field(..., description="IANA Timezone, e.g., Asia/Dhaka")
    # Optional fields from previous implementation
    city_name: Optional[str] = None
    mood: Optional[DateMood] = None
    vibe: Optional[DateVibe] = None

class DateCreate(DateBase):
    pass

class DateUpdate(BaseModel):
    title: Optional[str] = None
    where: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    how_we_meet: Optional[str] = None
    note: Optional[str] = None
    timezone: Optional[str] = None
    city_name: Optional[str] = None
    mood: Optional[DateMood] = None
    vibe: Optional[DateVibe] = None

class DateResponse(DateBase):
    id: str
    creator_id: str
    partner_id: str
    proposed_by: str
    status: DateStatus
    utc_timestamp: datetime
    created_at: datetime
    updated_at: datetime
    reviews: List[DateReview] = []
    notification_fired: bool = False
    deleted_by: List[str] = []
    photo_delete_requests: List[str] = []
    completed_by: List[str] = []

class DatePaginatedResponse(BaseModel):
    success: bool
    data: List[DateResponse]
    total: int
    page: int
    size: int

class DateRespond(BaseModel):
    action: str = Field(..., description="Action to take: 'accept' or 'reject'")

class DateReviewCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    text: str
    photos: List[str] = []

class PhotoPayload(BaseModel):
    photo_url: str

class GenericResponse(BaseModel):
    success: bool
    message: str
