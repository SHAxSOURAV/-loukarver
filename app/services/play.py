import asyncio
from typing import Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.db import get_client, get_db
from app.core.config import settings
from app.services.vibe_check import vibe_check_service
from app.services.vibe_card import vibe_card_service

class PlayService:
    def __init__(self) -> None:
        self.client = get_client()
        self.db = get_db()
        self.vibe_connections = self.db["vibe_check_connections"]
        self.cumulative_scores = self.db["vibe_cumulative_scores"]
        self.user_streaks = self.db["vibe_user_streaks"]

    async def init_indexes(self):
        try:
            await self.vibe_connections.create_index([("user_id", 1), ("status", 1)])
            await self.vibe_connections.create_index([("partner_id", 1), ("status", 1)])
            await self.vibe_connections.create_index([("user_id", 1), ("partner_id", 1)])
            await self.db["vibe_check_profiles"].create_index("user_id")
        except Exception as e:
            print(f"Error initializing play indexes: {e}")

    async def get_play_stats(self, user_id: str, user_doc: Optional[dict] = None) -> Dict[str, Any]:
        # Step 1: Concurrently fetch user profile name and active connection
        profile_doc, connection = await asyncio.gather(
            self.db["vibe_check_profiles"].find_one({"user_id": user_id}, {"name": 1}),
            self.vibe_connections.find_one({
                "$or": [{"user_id": user_id}, {"partner_id": user_id}],
                "status": "active"
            })
        )

        viber_name = profile_doc.get("name") if profile_doc else (user_doc.get("name") if user_doc else "Unknown")
        if not viber_name:
            viber_name = "Unknown"
            
        streak_days = 0
        match_percentage = 0.0
        vibe_partner = "No Partner"

        if connection:
            partner_id = connection["partner_id"] if connection["user_id"] == user_id else connection["user_id"]
            if partner_id:
                # Step 2: Concurrently fetch partner's name, cumulative score, and streak
                partner_doc, score_doc, streak_info = await asyncio.gather(
                    self.db["vibe_check_profiles"].find_one({"user_id": partner_id}, {"name": 1}),
                    self.cumulative_scores.find_one({"user_id": user_id, "partner_id": partner_id}),
                    vibe_card_service.get_streak(user_id, partner_id=partner_id, connection=connection)
                )
                if partner_doc:
                    vibe_partner = partner_doc.get("name", "Partner")
                if score_doc:
                    match_percentage = round(score_doc.get("score", 0.0), 1)
                if streak_info:
                    streak_days = streak_info.get("current_streak", 0)

        return {
            "viber_name": viber_name,
            "vibe_partner": vibe_partner,
            "streak_days": streak_days,
            "cumulated_match_percentage": match_percentage
        }

play_service = PlayService()
