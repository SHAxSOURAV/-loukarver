from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class VibeQuestion(BaseModel):
    id: str
    text: str
    option_a: str
    option_b: str
    category: Optional[str] = "General"
    is_anchor: bool = False

class VibeAnswer(BaseModel):
    question_id: str
    selected_option: str # "A" or "B"

class VibeCardDaily(BaseModel):
    date: str # mm.dd.yyyy
    questions: List[VibeQuestion]
    current_journey_day: int = 1

class VibeAnswerSubmit(BaseModel):
    partner_id: str
    answers: List[VibeAnswer]
    timezone: str = "UTC"

    model_config = {
        "json_schema_extra": {
            "example": {
                "answers": [
                    {"question_id": "q1_id", "selected_option": "A"},
                    {"question_id": "q2_id", "selected_option": "B"},
                    {"question_id": "q3_id", "selected_option": "A"}
                ],
                "timezone": "Asia/Dhaka"
            }
        }
    }

class VibeMatchedAnswer(BaseModel):
    question_id: str
    question: str
    option_a: str
    option_b: str
    my_selected_option: str  # "A" or "B"
    partner_selected_option: Optional[str] = None  # "A" or "B"
    my_answer: str
    partner_answer: Optional[str] = None
    is_match: bool

class VibeMatchResult(BaseModel):
    user_name: str
    partner_name: str
    daily_match_percent: float
    cumulative_match_percent: float
    matched_answers: List[VibeMatchedAnswer]
    both_finished: bool = False

class VibeMultiMatchResult(BaseModel):
    success: bool
    data: List[VibeMatchResult]

class VibeStreakResponse(BaseModel):
    current_streak: int
    last_answered: Optional[datetime] = None
    cards_answered_today: int = 0

class GenericResponse(BaseModel):
    success: bool
    message: str

# --- History System ---

class VibeHistoryEntry(BaseModel):
    date: str
    question: str
    category: Optional[str] = "General"
    option_a: str
    option_b: str
    user_name: str
    user_answer: str
    partner_name: str
    partner_answer: str
    is_match: bool

# --- Analytics / Pulse Insights ---

class CategoryMatch(BaseModel):
    category: str
    match_percentage: float
    total_questions: int
    matched_questions: int

class TimelineEntry(BaseModel):
    day: int
    match_percentage: float
    matches: int
    total: int

class DepthMatch(BaseModel):
    depth: str
    match_percentage: float
    matches: int
    total: int

class PulseAnalytics(BaseModel):
    partner_id: str
    partner_name: str
    overall_match_percentage: float
    total_cards_played: int
    total_matches: int
    timeline: List[TimelineEntry]
    by_depth: List[DepthMatch]
    by_category: List[CategoryMatch]
    key_agreements: List[VibeHistoryEntry]
    key_disagreements: List[VibeHistoryEntry]
    strongest_category: Optional[CategoryMatch] = None
    divergent_category: Optional[CategoryMatch] = None

class PulseAnalyticsResponse(BaseModel):
    success: bool
    data: PulseAnalytics

class VibeHistoryPaginatedResponse(BaseModel):
    success: bool
    data: List[VibeHistoryEntry]
    total: int
    page: int
    size: int
    category: str
    search_term: Optional[str] = None
    total_matched: int = 0
    total_differed: int = 0
