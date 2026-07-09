from fastapi import APIRouter, Depends, HTTPException, Query, status, WebSocket, WebSocketDisconnect
from typing import List, Optional, Dict
import asyncio

from app.routers.auth import get_current_user
from app.schemas.vibe_card import (
    VibeCardDaily, VibeAnswerSubmit, VibeMatchResult, VibeMultiMatchResult,
    VibeStreakResponse, GenericResponse, VibeHistoryPaginatedResponse
)
from app.services.vibe_card import vibe_card_service

router = APIRouter(prefix="/vibecheck/cards", tags=["VibeCheck Cards"])

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        print(f"WS CONNECTED: {user_id}. Total active: {len(self.active_connections)}")

    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            print(f"WS DISCONNECTED: {user_id}")

    async def send_personal_message(self, message: dict, user_id: str):
        print(f"WS ATTEMPT SEND to {user_id}: {message}")
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_json(message)
                print(f"WS SUCCESS SEND to {user_id}")
            except Exception as e:
                print(f"Error sending ws message to {user_id}: {e}")
        else:
            print(f"WS FAILED: {user_id} not in active_connections (Keys: {list(self.active_connections.keys())})")

manager = ConnectionManager()

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(user_id)

@router.get("/history", response_model=VibeHistoryPaginatedResponse)
async def get_vibe_card_history(
    partner_id: Optional[str] = Query(None),
    category: str = Query("All"),
    search_term: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1),
    current_user: dict = Depends(get_current_user)
):
    """Fetch history of answers between user and partners. If partner_id is not provided, shows all partners."""
    try:
        data, total, total_matched, total_differed = await vibe_card_service.get_history(
            current_user["id"], partner_id, category, search_term, page, size
        )
        return VibeHistoryPaginatedResponse(
            success=True, 
            data=data, 
            total=total, 
            page=page, 
            size=size, 
            category=category,
            search_term=search_term,
            total_matched=total_matched,
            total_differed=total_differed
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/daily", response_model=VibeCardDaily)
async def get_daily_cards(
    partner_id: str = Query(..., description="The ID of the connected partner for this journey"),
    timezone: str = Query("UTC"),
    current_user: dict = Depends(get_current_user)
):
    """Fetch today's 3 'This or That' questions."""
    daily_data = await vibe_card_service.get_daily_questions(current_user["id"], partner_id, timezone)
    from datetime import datetime, timedelta
    import zoneinfo
    try:
        tz = zoneinfo.ZoneInfo(timezone)
    except:
        tz = zoneinfo.ZoneInfo("UTC")
    today_str = (datetime.now(tz) - timedelta(hours=4)).strftime("%m.%d.%Y")
    
    return {
        "date": today_str, 
        "questions": daily_data["questions"],
        "current_journey_day": daily_data["current_journey_day"]
    }

@router.post("/answer", response_model=GenericResponse)
async def submit_vibe_answers(
    payload: VibeAnswerSubmit,
    current_user: dict = Depends(get_current_user)
):
    """Submit your answers for today's Vibe Cards."""
    try:
        print(f"SUBMIT ANSWERS: user_id={current_user['id']}")
        res = await vibe_card_service.submit_answers(current_user["id"], payload)
        
        # Broadcast to partners
        cursor = vibe_card_service.vibe_connections.find({"user_id": current_user["id"]}, {"partner_id": 1})
        conn_docs = await cursor.to_list(length=None)
        partner_ids = [c["partner_id"] for c in conn_docs]
        print(f"BROADCASTING to partners: {partner_ids}")
        
        for p_id in partner_ids:
            await manager.send_personal_message(
                {"type": "PARTNER_ANSWERED", "partner_id": current_user["id"]}, 
                p_id
            )
            
        return res
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/results", response_model=VibeMultiMatchResult)
async def get_vibe_results(
    partner_id: Optional[str] = Query(None),
    timezone: str = Query("UTC"),
    current_user: dict = Depends(get_current_user)
):
    """Compare today's results with partners. If partner_id is not provided, shows all connected partners who answered today."""
    try:
        results = await vibe_card_service.get_match_results(current_user["id"], partner_id, timezone)
        return VibeMultiMatchResult(success=True, data=results)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/streak", response_model=VibeStreakResponse)
async def get_vibe_streak(
    partner_id: Optional[str] = Query(None),
    timezone: str = Query("UTC"),
    current_user: dict = Depends(get_current_user)
):
    """Get your current Vibe Card answering streak."""
    return await vibe_card_service.get_streak(current_user["id"], partner_id, timezone)
