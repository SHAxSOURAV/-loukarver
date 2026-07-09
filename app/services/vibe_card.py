import os
import zoneinfo
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from datetime import datetime, timezone, timedelta

from app.core.config import settings
from app.schemas.vibe_card import VibeAnswerSubmit, VibeQuestion

class VibeCardService:
    def __init__(self) -> None:
        self.client = AsyncIOMotorClient(settings.MONGO_URL)
        self.db = self.client[settings.MONGO_DB_NAME]
        self.vibe_90day_cards = self.db["vibe_90day_cards"]
        self.user_answers = self.db["vibe_user_answers"]
        self.cumulative_scores = self.db["vibe_cumulative_scores"]
        self.vibe_profiles = self.db["vibe_check_profiles"]
        self.vibe_connections = self.db["vibe_check_connections"]
        self.user_streaks = self.db["vibe_user_streaks"]

    async def init_indexes(self):
        await self.user_answers.create_index([("user_id", 1), ("partner_id", 1), ("journey_day", 1)], unique=True)
        await self.cumulative_scores.create_index([("user_id", 1), ("partner_id", 1)], unique=True)
        await self.user_streaks.create_index("user_id", unique=True)

    async def _ensure_current_journey_day(self, user_id: str, partner_id: str, tz_str: str) -> Optional[Dict]:
        conn = await self.vibe_connections.find_one({"user_id": user_id, "partner_id": partner_id})
        if not conn or conn.get("status") != "active": return None

        from datetime import datetime, timezone
        import zoneinfo
        try:
            tz = zoneinfo.ZoneInfo(tz_str)
        except Exception:
            tz = zoneinfo.ZoneInfo("UTC")
            
        now_utc = datetime.now(timezone.utc)
        now_local = now_utc.astimezone(tz)
        
        # 1. Midnight Rollover (00:00 local time)
        logical_today = now_local.date()
        logical_today_str = logical_today.isoformat()

        if conn.get("current_journey_day", 1) >= 90: return conn
        
        current_day = conn.get("current_journey_day", 1)
        
        # 2. Calculate true calendar day (target_day)
        connected_at = conn.get("connected_at", now_utc)
        if connected_at.tzinfo is None:
            connected_at = connected_at.replace(tzinfo=timezone.utc)
        start_date = connected_at.astimezone(tz).date()
        
        target_day = (logical_today - start_date).days + 1
        
        # 3. Catch-up Logic: Advance day by day if unblocked
        while current_day < target_day:
            # If explicitly stalled by submit_answers
            if conn.get("stalled_since"):
                break
                
            # Check if current_day has an anchor
            cursor = self.vibe_90day_cards.find({"day": current_day})
            cards = await cursor.to_list(length=None)
            has_anchor = any(c.get("is_anchor", False) for c in cards)
            
            if has_anchor:
                # BOTH users must have submitted answers for this anchor day
                my_ans = await self.user_answers.find_one({"user_id": user_id, "partner_id": partner_id, "journey_day": current_day})
                pa_ans = await self.user_answers.find_one({"user_id": partner_id, "partner_id": user_id, "journey_day": current_day})
                
                if not my_ans or not pa_ans:
                    break # Cannot advance past an uncompleted anchor
                    
            # Unblocked! Advance to next day
            current_day += 1

        # 4. Save progress if advanced
        if current_day != conn.get("current_journey_day"):
            await self.vibe_connections.update_many(
                {"$or": [
                    {"user_id": user_id, "partner_id": partner_id},
                    {"user_id": partner_id, "partner_id": user_id}
                ]},
                {"$set": {
                    "current_journey_day": current_day,
                    "last_journey_day_update_date": logical_today_str
                }}
            )
            conn["current_journey_day"] = current_day
            conn["last_journey_day_update_date"] = logical_today_str
            
        return conn

    async def get_daily_questions(self, user_id: str, partner_id: str, tz_str: str) -> Dict[str, Any]:
        """Get the 3 questions for the current journey day of this connection."""
        conn = await self._ensure_current_journey_day(user_id, partner_id, tz_str)
        if not conn:
            return {"questions": [], "current_journey_day": 1}
            
        current_day = conn.get("current_journey_day", 1)
        
        cursor = self.vibe_90day_cards.find({"day": current_day}).sort("slot", 1)
        cards = await cursor.to_list(length=None)
        
        qs = [
            {
                "id": c["card_id"],
                "text": f"Day {c['day']} - {c['category']}",
                "option_a": c["option_a"],
                "option_b": c["option_b"],
                "category": c["category"],
                "is_anchor": c.get("is_anchor", False)
            } for c in cards
        ]
        return {"questions": qs, "current_journey_day": current_day}

    async def submit_answers(self, user_id: str, payload: VibeAnswerSubmit) -> Dict[str, Any]:
        """Submit answers for the specific partner's journey."""
        partner_id = getattr(payload, "partner_id", None)
        if not partner_id:
            raise ValueError("partner_id is now required to submit answers.")
            
        conn = await self.vibe_connections.find_one({"user_id": user_id, "partner_id": partner_id})
        if not conn or conn.get("status") != "active":
            raise ValueError("Active connection not found.")
            
        current_day = conn.get("current_journey_day", 1)
        now = datetime.now(timezone.utc)
        
        new_answers = [a.model_dump() for a in payload.answers]
        
        existing_doc = await self.user_answers.find_one({"user_id": user_id, "partner_id": partner_id, "journey_day": current_day})
        existing_answers = existing_doc.get("answers", []) if existing_doc else []
        
        ans_map = {a["question_id"]: a for a in existing_answers}
        for a in new_answers:
            ans_map[a["question_id"]] = a
            
        merged_answers = list(ans_map.values())
        
        # Save answers for this journey day
        await self.user_answers.update_one(
            {"user_id": user_id, "partner_id": partner_id, "journey_day": current_day},
            {
                "$setOnInsert": {"created_at": now},
                "$set": {"answers": merged_answers}
            },
            upsert=True
        )
        
        # Handle Anchor Logic
        cards_data = await self.get_daily_questions(user_id, partner_id, payload.timezone)
        cards = cards_data["questions"]
        has_anchor = any(c["is_anchor"] for c in cards)
        
        if has_anchor:
            # Check if partner has answered
            pa_ans = await self.user_answers.find_one({
                "user_id": partner_id, 
                "partner_id": user_id, 
                "journey_day": current_day
            })
            
            if not pa_ans:
                # Partner hasn't answered, so we stall
                await self.vibe_connections.update_many(
                    {"$or": [
                        {"user_id": user_id, "partner_id": partner_id},
                        {"user_id": partner_id, "partner_id": user_id}
                    ]},
                    {"$set": {
                        "stalled_since": now,
                        "silent_partner_id": partner_id
                    }}
                )
            else:
                # Both answered, un-stall
                await self.vibe_connections.update_many(
                    {"$or": [
                        {"user_id": user_id, "partner_id": partner_id},
                        {"user_id": partner_id, "partner_id": user_id}
                    ]},
                    {"$set": {
                        "stalled_since": None,
                        "silent_partner_id": None
                    }}
                )
        
        return {"success": True, "message": "Answers submitted!"}

    async def get_match_results(self, user_id: str, partner_id: Optional[str] = None, tz_str: str = "UTC") -> List[Dict[str, Any]]:
        if not partner_id:
            return []
            
        user_profile = await self.vibe_profiles.find_one({"user_id": user_id})
        partner_profile = await self.vibe_profiles.find_one({"user_id": partner_id})
        
        conn = await self.vibe_connections.find_one({"user_id": user_id, "partner_id": partner_id})
        if not conn: return []
        
        current_day = conn.get("current_journey_day", 1)
        
        my_ans = await self.user_answers.find_one({"user_id": user_id, "partner_id": partner_id, "journey_day": current_day})
        pa_ans = await self.user_answers.find_one({"user_id": partner_id, "partner_id": user_id, "journey_day": current_day})
        
        cards_data = await self.get_daily_questions(user_id, partner_id, tz_str)
        questions = cards_data["questions"]
        q_map = {q["id"]: q for q in questions}
        
        my_map = {a["question_id"]: a["selected_option"] for a in my_ans.get("answers", [])} if my_ans else {}
        pa_map = {a["question_id"]: a["selected_option"] for a in pa_ans.get("answers", [])} if pa_ans else {}
        
        my_ans_time = my_ans.get("created_at").isoformat() if my_ans and "created_at" in my_ans else None
        pa_ans_time = pa_ans.get("created_at").isoformat() if pa_ans and "created_at" in pa_ans else None
        
        matches = 0
        total_q = len(questions)
        matched_details = []
        
        for qid, q in q_map.items():
            my_choice = my_map.get(qid)
            pa_choice = pa_map.get(qid)
            
            # If I haven't answered, skip it
            if not my_choice: continue
            
            is_match = (my_choice == pa_choice) if pa_choice else False
            if is_match: matches += 1
            
            matched_details.append({
                "question_id": qid,
                "question": q["text"],
                "option_a": q["option_a"],
                "option_b": q["option_b"],
                "my_selected_option": my_choice,
                "partner_selected_option": pa_choice,
                "my_answer": q["option_a"] if my_choice == "A" else q["option_b"],
                "partner_answer": (q["option_a"] if pa_choice == "A" else q["option_b"]) if pa_choice else None,
                "my_answer_time": my_ans_time,
                "partner_answer_time": pa_ans_time if pa_choice else None,
                "is_match": is_match
            })
            
        daily_match_percent = (matches / total_q * 100) if total_q > 0 else 0.0
        both_finished = (len(my_map) >= total_q and len(pa_map) >= total_q)
        
        # Calculate cumulative matches
        all_my_ans = await self.user_answers.find({"user_id": user_id, "partner_id": partner_id}).to_list(length=None)
        all_pa_ans = await self.user_answers.find({"user_id": partner_id, "partner_id": user_id}).to_list(length=None)
        
        conn = await self.vibe_connections.find_one({"$or": [{"user_id": user_id, "partner_id": partner_id}, {"user_id": partner_id, "partner_id": user_id}]})
        current_journey_day = conn.get("current_journey_day", 1) if conn else 1
        total_past_questions = max(0, (current_journey_day - 1) * 3)
        
        pa_ans_map_all = {}
        for doc in all_pa_ans:
            for ans in doc.get("answers", []):
                pa_ans_map_all[ans["question_id"]] = ans["selected_option"]
                
        total_matched = 0
        total_differed = 0
        past_answered_by_both = 0
        
        for doc in all_my_ans:
            doc_journey_day = doc.get("journey_day", 1)
            for ans in doc.get("answers", []):
                my_choice = ans["selected_option"]
                pa_choice = pa_ans_map_all.get(ans["question_id"])
                if pa_choice:
                    if my_choice == pa_choice:
                        total_matched += 1
                    else:
                        total_differed += 1
                        
                    if doc_journey_day < current_journey_day:
                        past_answered_by_both += 1
                        
        u_past = max(0, total_past_questions - past_answered_by_both)
        
        weight = 50.0 / 270.0
        cumulative_match_percent = 50.0 + (total_matched * weight) - (total_differed * weight) - (u_past * weight)
        cumulative_match_percent = max(0.0, min(100.0, cumulative_match_percent))
        
        return [{
            "user_name": user_profile["name"],
            "partner_name": partner_profile["name"],
            "daily_match_percent": round(daily_match_percent, 1),
            "cumulative_match_percent": round(cumulative_match_percent, 1),
            "matched_answers": matched_details,
            "both_finished": both_finished
        }]

    async def get_streak(self, user_id: str, partner_id: Optional[str] = None, user_timezone: str = "UTC") -> Dict[str, Any]:
        # Find active connection
        query = {
            "$or": [{"user_id": user_id}, {"partner_id": user_id}],
            "status": "active"
        }
        if partner_id:
            query["$and"] = [{"$or": [{"user_id": partner_id}, {"partner_id": partner_id}]}]
            
        conn = await self.vibe_connections.find_one(query)
        
        if not conn:
            return {"current_streak": 0, "last_answered": None, "cards_answered_today": 0}
            
        partner_id = conn["partner_id"] if conn["user_id"] == user_id else conn["user_id"]
        
        # Ensure current_journey_day is up to date
        conn = await self._ensure_current_journey_day(user_id, partner_id, user_timezone)
        if not conn:
            return {"current_streak": 0, "last_answered": None, "cards_answered_today": 0}
            
        current_day = conn.get("current_journey_day", 1)
        
        # Get answers for both users
        my_ans_cursor = self.user_answers.find({"user_id": user_id, "partner_id": partner_id})
        pa_ans_cursor = self.user_answers.find({"user_id": partner_id, "partner_id": user_id})
        
        my_ans = await my_ans_cursor.to_list(length=None)
        pa_ans = await pa_ans_cursor.to_list(length=None)
        
        # Find journey_days where BOTH answered
        my_days = {doc["journey_day"] for doc in my_ans if "journey_day" in doc}
        pa_days = {doc["journey_day"] for doc in pa_ans if "journey_day" in doc}
        both_days = my_days.intersection(pa_days)
        
        current_streak = 0
        for day in range(current_day, 0, -1):
            if day in both_days:
                current_streak += 1
            elif day == current_day:
                # Today hasn't expired yet, so not answering yet doesn't break the streak
                continue
            else:
                # An expired day wasn't answered by both, streak breaks
                break
                
        # Cards answered today
        my_today_doc = next((doc for doc in my_ans if doc.get("journey_day") == current_day), None)
        cards_today = len(my_today_doc.get("answers", [])) if my_today_doc else 0
        
        # Last answered time
        last_answered = None
        if my_ans:
            sorted_ans = sorted([d for d in my_ans if "created_at" in d], key=lambda x: x["created_at"], reverse=True)
            if sorted_ans:
                last_answered = sorted_ans[0]["created_at"].isoformat()
                
        return {
            "current_streak": current_streak,
            "last_answered": last_answered,
            "cards_answered_today": cards_today
        }

    async def get_history(self, user_id: str, partner_id: Optional[str] = None, category: str = "All", search_term: Optional[str] = None, page: int = 1, size: int = 20) -> Tuple[List[Dict[str, Any]], int, int, int]:
        if not partner_id:
            return [], 0, 0, 0
            
        user_profile = await self.vibe_profiles.find_one({"user_id": user_id})
        partner_profile = await self.vibe_profiles.find_one({"user_id": partner_id})
        
        my_name = user_profile["name"] if user_profile else "You"
        pa_name = partner_profile["name"] if partner_profile else "Partner"

        # Fetch all questions to map text
        questions = await self.vibe_90day_cards.find().to_list(length=None)
        q_map = {q["card_id"]: q for q in questions}

        # Fetch all answers for both users in this connection
        my_ans = await self.user_answers.find({"user_id": user_id, "partner_id": partner_id}).to_list(length=None)
        pa_ans = await self.user_answers.find({"user_id": partner_id, "partner_id": user_id}).to_list(length=None)
        
        pa_ans_map_all = {}
        for doc in pa_ans:
            for ans in doc.get("answers", []):
                pa_ans_map_all[ans["question_id"]] = ans["selected_option"]

        history_items = []
        total_matched = 0
        total_differed = 0
        
        # Sort docs by journey_day desc (newest days first)
        my_ans.sort(key=lambda x: x.get("journey_day", 1), reverse=True)

        for doc in my_ans:
            journey_day = doc.get("journey_day", 1)
            date_str = f"Day {journey_day}"
            
            # Keep original answers order (or reverse it if we want newest cards within the day first)
            # We'll just iterate in order they were saved, which is usually order of cards.
            ans_list = doc.get("answers", [])
            
            for ans in reversed(ans_list): # Reverse to put latest cards in a day at the top
                qid = ans["question_id"]
                my_choice = ans["selected_option"]
                pa_choice = pa_ans_map_all.get(qid)
                
                if pa_choice:
                    q = q_map.get(qid)
                    if not q: continue
                    
                    is_match = (my_choice == pa_choice)
                    if is_match:
                        total_matched += 1
                    else:
                        total_differed += 1
                        
                    my_ans_text = q["option_a"] if my_choice == "A" else q["option_b"]
                    pa_ans_text = q["option_a"] if pa_choice == "A" else q["option_b"]
                    
                    item = {
                        "date": date_str,
                        "question": f"Day {q['day']} - {q['category']}",
                        "category": q.get("category", "General"),
                        "option_a": q["option_a"],
                        "option_b": q["option_b"],
                        "user_name": my_name,
                        "user_answer": my_ans_text,
                        "partner_name": pa_name,
                        "partner_answer": pa_ans_text,
                        "is_match": is_match
                    }
                    history_items.append(item)
                    
        # Apply filters
        if category == "Matched":
            history_items = [h for h in history_items if h["is_match"]]
        elif category == "Differed":
            history_items = [h for h in history_items if not h["is_match"]]
            
        if search_term:
            term = search_term.lower()
            history_items = [
                h for h in history_items 
                if term in h["question"].lower() or 
                   term in h["user_answer"].lower() or 
                   term in h["partner_answer"].lower() or 
                   term in h["date"].lower() or
                   term in h["option_a"].lower() or
                   term in h["option_b"].lower()
            ]

        total = len(history_items)
        
        # Pagination
        start = (page - 1) * size
        end = start + size
        paginated_items = history_items[start:end]

        return paginated_items, total, total_matched, total_differed

    async def get_pulse_analytics(self, user_id: str, partner_id: Optional[str] = None) -> Dict[str, Any]:
        if not partner_id:
            return {
                "partner_id": "", "partner_name": "", "overall_match_percentage": 0.0,
                "total_cards_played": 0, "total_matches": 0, "timeline": [], "by_depth": [],
                "by_category": [], "key_agreements": [], "key_disagreements": [],
                "strongest_category": None, "divergent_category": None
            }

        user_profile = await self.vibe_profiles.find_one({"user_id": user_id})
        partner_profile = await self.vibe_profiles.find_one({"user_id": partner_id})
        
        my_name = user_profile["name"] if user_profile else "You"
        pa_name = partner_profile["name"] if partner_profile else "Partner"

        # Fetch all questions
        questions = await self.vibe_90day_cards.find().to_list(length=None)
        q_map = {q["card_id"]: q for q in questions}

        # Fetch answers
        my_ans = await self.user_answers.find({"user_id": user_id, "partner_id": partner_id}).to_list(length=None)
        pa_ans = await self.user_answers.find({"user_id": partner_id, "partner_id": user_id}).to_list(length=None)
        
        pa_ans_map_all = {}
        for doc in pa_ans:
            for ans in doc.get("answers", []):
                pa_ans_map_all[ans["question_id"]] = ans["selected_option"]

        total_cards = 0
        total_matches = 0
        
        timeline_data = {}
        cat_data = {}
        depth_data = {}

        history_items = []

        for doc in my_ans:
            journey_day = doc.get("journey_day", 1)
            date_str = f"Day {journey_day}"
            
            for ans in doc.get("answers", []):
                qid = ans["question_id"]
                my_choice = ans["selected_option"]
                pa_choice = pa_ans_map_all.get(qid)
                
                if pa_choice:
                    q = q_map.get(qid)
                    if not q: continue
                    
                    is_match = (my_choice == pa_choice)
                    total_cards += 1
                    if is_match:
                        total_matches += 1
                        
                    # Timeline
                    if journey_day not in timeline_data:
                        timeline_data[journey_day] = {"matches": 0, "total": 0}
                    timeline_data[journey_day]["total"] += 1
                    if is_match: timeline_data[journey_day]["matches"] += 1
                    
                    # Category
                    cat = q.get("category", "General")
                    if cat not in cat_data:
                        cat_data[cat] = {"matches": 0, "total": 0}
                    cat_data[cat]["total"] += 1
                    if is_match: cat_data[cat]["matches"] += 1
                    
                    # Depth
                    depth = q.get("depth", "Surface")
                    depth = depth.title() if depth else "Surface"
                    if depth not in depth_data:
                        depth_data[depth] = {"matches": 0, "total": 0}
                    depth_data[depth]["total"] += 1
                    if is_match: depth_data[depth]["matches"] += 1

                    my_ans_text = q["option_a"] if my_choice == "A" else q["option_b"]
                    pa_ans_text = q["option_a"] if pa_choice == "A" else q["option_b"]
                    
                    history_items.append({
                        "date": date_str,
                        "question": f"Day {q['day']} - {q['category']}",
                        "category": cat,
                        "option_a": q["option_a"],
                        "option_b": q["option_b"],
                        "user_name": my_name,
                        "user_answer": my_ans_text,
                        "partner_name": pa_name,
                        "partner_answer": pa_ans_text,
                        "is_match": is_match,
                        "journey_day": journey_day
                    })

        overall_match_percentage = round((total_matches / total_cards * 100) if total_cards > 0 else 0, 1)

        # Timeline entries
        timeline = []
        for day in sorted(timeline_data.keys()):
            d = timeline_data[day]
            timeline.append({
                "day": day,
                "matches": d["matches"],
                "total": d["total"],
                "match_percentage": round((d["matches"] / d["total"] * 100), 1)
            })

        # By Category
        by_category = []
        for cat, d in cat_data.items():
            by_category.append({
                "category": cat,
                "match_percentage": round((d["matches"] / d["total"] * 100), 1),
                "matched_questions": d["matches"],
                "total_questions": d["total"]
            })
        by_category.sort(key=lambda x: x["total_questions"], reverse=True)
        
        strongest_category = None
        divergent_category = None
        if by_category:
            valid_cats = [c for c in by_category if c["total_questions"] >= 1]
            if valid_cats:
                strongest_category = max(valid_cats, key=lambda x: x["match_percentage"])
                divergent_category = min(valid_cats, key=lambda x: x["match_percentage"])

        # By Depth
        by_depth = []
        for dpt, d in depth_data.items():
            by_depth.append({
                "depth": dpt,
                "matches": d["matches"],
                "total": d["total"],
                "match_percentage": round((d["matches"] / d["total"] * 100), 1)
            })
        
        depth_order = {"Surface": 1, "Medium": 2, "Deep": 3}
        by_depth.sort(key=lambda x: depth_order.get(x["depth"], 99))

        # Key Agreements and Disagreements
        history_items.sort(key=lambda x: x["journey_day"], reverse=True)
        
        agreements = [h for h in history_items if h["is_match"]]
        disagreements = [h for h in history_items if not h["is_match"]]
        
        key_agreements = agreements[:3]
        key_disagreements = disagreements[:3]

        for item in key_agreements + key_disagreements:
            item.pop("journey_day", None)

        return {
            "partner_id": partner_id,
            "partner_name": pa_name,
            "overall_match_percentage": overall_match_percentage,
            "total_cards_played": total_cards,
            "total_matches": total_matches,
            "timeline": timeline,
            "by_depth": by_depth,
            "by_category": by_category,
            "key_agreements": key_agreements,
            "key_disagreements": key_disagreements,
            "strongest_category": strongest_category,
            "divergent_category": divergent_category
        }

vibe_card_service = VibeCardService()
