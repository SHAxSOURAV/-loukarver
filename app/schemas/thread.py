from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Union
from datetime import datetime
from enum import Enum

class ThreadCategory(str, Enum):
    LETTER = "Letter"
    VOICE = "Voice"
    PHOTO = "Photo"
    PROMPT = "Prompt"
    APPRECIATION = "Appreciation"
    CHECKIN = "Checkin"

class PromptType(str, Enum):
    ROMANTIC = "Romantic"
    DESIRED = "Desired"

class PromptQuestion(BaseModel):
    id: Optional[str] = None
    category: str  # e.g., "Emotional", "Desire", "Growth", "Depth", "Memory", "Future", "Adventure", "Intense", "Daring", "Vulnerable", "Intimate"
    rating: str    # e.g., "●●○○○"
    text: str
    type: PromptType
    creator_id: Optional[str] = None # None for default global questions

class PromptQuestionCreate(BaseModel):
    category: str
    rating: str
    text: str
    type: PromptType

class ThreadMessageBase(BaseModel):
    category: ThreadCategory
    timezone: str = "UTC"

class LetterCreate(ThreadMessageBase):
    text: str

    @field_validator('text')
    def validate_text(cls, v):
        if not v or not v.strip():
            raise ValueError('Letter text cannot be empty or whitespace.')
        return v.strip()

class VoiceCreate(ThreadMessageBase):
    pass # File handled via UploadFile

class PhotoCreate(ThreadMessageBase):
    caption: str

class VoiceBase64Create(ThreadMessageBase):
    file_base64: str
    filename: str
    content_type: str

class PhotoBase64Create(ThreadMessageBase):
    file_base64: str
    filename: str
    content_type: str
    caption: str

class PromptAskCreate(ThreadMessageBase):
    prompt_type: PromptType
    question_text: str
    type: str

    @field_validator('question_text')
    def validate_question(cls, v):
        if not v or not v.strip():
            raise ValueError('Question text cannot be empty or whitespace.')
        return v.strip()

class PromptReplyUpdate(BaseModel):
    answer: str
    timezone: str = "UTC"

    @field_validator('answer')
    def validate_answer(cls, v):
        if not v or not v.strip():
            raise ValueError('Reply answer cannot be empty or whitespace.')
        return v.strip()

class AppreciationCreate(ThreadMessageBase):
    text: str

    @field_validator('text')
    def validate_text(cls, v):
        if not v or not v.strip():
            raise ValueError('Appreciation text cannot be empty or whitespace.')
        return v.strip()

class CheckInThreadCreate(ThreadMessageBase):
    answer_1: str
    answer_2: str
    answer_3: str
    date: str # mm.dd.yyyy

    @field_validator('answer_1', 'answer_2', 'answer_3', mode='after')
    def clean_answers(cls, v):
        return v.strip() if v else ""

class LetterUpdate(BaseModel):
    text: Optional[str] = None
    timezone: str = "UTC"

class VoiceUpdate(BaseModel):
    timezone: str = "UTC"

class PhotoUpdate(BaseModel):
    caption: Optional[str] = None
    timezone: str = "UTC"

class PromptAskUpdate(BaseModel):
    prompt_type: Optional[PromptType] = None
    question_text: Optional[str] = None
    type: Optional[str] = None
    timezone: str = "UTC"

class AppreciationUpdate(BaseModel):
    text: Optional[str] = None
    timezone: str = "UTC"

class CheckInThreadUpdate(BaseModel):
    answer_1: Optional[str] = None
    answer_2: Optional[str] = None
    answer_3: Optional[str] = None
    date: Optional[str] = None
    timezone: str = "UTC"

class ThreadMessageResponse(BaseModel):
    id: str
    category: ThreadCategory
    sender_id: str
    sender_name: str
    user_name: str
    partner_name: str
    content: dict
    created_at: datetime
    is_sent: bool = True
    is_delivered: bool = False
    is_seen: bool = False
    
class ThreadCategoryResponse(BaseModel):
    success: bool
    data: List[str]

class GenericResponse(BaseModel):
    success: bool
    message: str
