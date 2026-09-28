from fastapi import APIRouter, Depends, HTTPException, status
from app.routers.auth import get_current_user
from app.schemas.interactions import InteractionResponse, GenericResponse
from app.services.interactions import interaction_service

router = APIRouter(prefix="/interactions", tags=["Interactions"])

@router.post("/poke", response_model=GenericResponse)
async def poke_partner(current_user: dict = Depends(get_current_user)):
    """Increment the interaction count for your partner."""
    success = await interaction_service.increment_count(current_user["id"], user_doc=current_user)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not poke partner. Ensure you are aligned with a partner."
        )
    return GenericResponse(success=True, message="Partner poked!")

@router.get("", response_model=InteractionResponse)
async def get_interactions(current_user: dict = Depends(get_current_user)):
    """Get the count of interactions received from your partner today."""
    stats = await interaction_service.get_interaction_stats(current_user["id"], user_doc=current_user)
    if stats is None:
        stats = {
            "partner_name": "Partner",
            "received_count": 0,
            "received_last_activity": None,
            "sent_count": 0,
            "sent_last_activity": None
        }
    return InteractionResponse(success=True, data=stats)
