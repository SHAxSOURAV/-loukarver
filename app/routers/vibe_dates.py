from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Optional
from app.routers.auth import get_current_user
from app.schemas.vibe_dates import (
    VibeDateCreate, VibeDateUpdate, VibeDateResponse, 
    VibeDateRespondRequest, VibeDateListResponse
)
from app.services.vibe_dates import vibe_date_service

router = APIRouter(prefix="/vibedates", tags=["Vibe Dates"])

@router.post("", response_model=VibeDateResponse, status_code=status.HTTP_201_CREATED)
async def propose_vibe_date(payload: VibeDateCreate, current_user: dict = Depends(get_current_user)):
    """Propose a new date to a Vibe partner."""
    try:
        return await vibe_date_service.propose_date(current_user["id"], payload)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("", response_model=VibeDateListResponse)
async def list_vibe_dates(
    partner_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    timezone: str = Query("UTC"),
    current_user: dict = Depends(get_current_user)
):
    """List all date proposals sent or received with pagination."""
    try:
        dates, total = await vibe_date_service.get_dates(current_user["id"], timezone, page, size, partner_id=partner_id)
        return {
            "success": True, 
            "data": dates, 
            "total": total,
            "page": page,
            "size": size,
            "timezone": timezone
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/hidden", response_model=VibeDateListResponse)
async def list_hidden_vibe_dates(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    timezone: str = Query("UTC"),
    current_user: dict = Depends(get_current_user)
):
    """List all hidden date proposals with pagination."""
    try:
        dates, total = await vibe_date_service.get_hidden_dates(current_user["id"], timezone, page, size)
        return {
            "success": True, 
            "data": dates, 
            "total": total,
            "page": page,
            "size": size,
            "timezone": timezone
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/pending-count")
async def get_pending_dates_count(
    partner_id: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """Get count of unread/pending dates received by current user."""
    try:
        count = await vibe_date_service.get_pending_dates_count(current_user["id"], partner_id)
        return {"success": True, "count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{date_id}", response_model=VibeDateResponse)
async def get_vibe_date_details(date_id: str, current_user: dict = Depends(get_current_user)):
    """Get details of a specific date proposal."""
    try:
        return await vibe_date_service.get_date_by_id(date_id, current_user["id"])
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/{date_id}", response_model=VibeDateResponse)
async def update_vibe_date(date_id: str, payload: VibeDateUpdate, current_user: dict = Depends(get_current_user)):
    """Update date details. If already accepted, status resets to pending and partner is notified."""
    try:
        return await vibe_date_service.update_date(current_user["id"], date_id, payload)
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{date_id}/respond", response_model=VibeDateResponse)
async def respond_to_vibe_date(date_id: str, payload: VibeDateRespondRequest, current_user: dict = Depends(get_current_user)):
    """Accept, reject, or propose changes to a date."""
    try:
        return await vibe_date_service.respond_to_date(current_user["id"], date_id, payload)
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{date_id}")
async def delete_vibe_date(date_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a date proposal."""
    try:
        success = await vibe_date_service.delete_date(current_user["id"], date_id)
        if not success:
             raise HTTPException(status_code=404, detail="Date proposal not found.")
        return {"success": True, "message": "Date proposal deleted successfully."}
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{date_id}/cancel")
async def cancel_vibe_date(date_id: str, current_user: dict = Depends(get_current_user)):
    """Cancel an accepted date proposal."""
    try:
        success = await vibe_date_service.cancel_date(current_user["id"], date_id)
        if not success:
             raise HTTPException(status_code=400, detail="Cannot cancel this date.")
        return {"success": True, "message": "Date cancelled."}
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/mark-seen")
async def mark_dates_seen(current_user: dict = Depends(get_current_user)):
    """Mark all pending dates as seen."""
    try:
        await vibe_date_service.mark_dates_seen(current_user["id"])
        return {"success": True, "message": "Dates marked as seen."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{date_id}/complete")
async def complete_vibe_date(date_id: str, current_user: dict = Depends(get_current_user)):
    """Mark an accepted date as completed."""
    try:
        success = await vibe_date_service.complete_date(current_user["id"], date_id)
        if not success:
             raise HTTPException(status_code=400, detail="Cannot complete this date.")
        return {"success": True, "message": "Date completed."}
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{date_id}/hide")
async def hide_vibe_date(date_id: str, current_user: dict = Depends(get_current_user)):
    """Hide a date proposal from the current user's history."""
    try:
        success = await vibe_date_service.hide_date(current_user["id"], date_id)
        if not success:
             raise HTTPException(status_code=400, detail="Cannot hide this date.")
        return {"success": True, "message": "Date hidden."}
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{date_id}/unhide")
async def unhide_vibe_date(date_id: str, current_user: dict = Depends(get_current_user)):
    """Unhide a date proposal to show it again in history."""
    try:
        success = await vibe_date_service.unhide_date(current_user["id"], date_id)
        if not success:
             raise HTTPException(status_code=400, detail="Cannot unhide this date.")
        return {"success": True, "message": "Date unhidden."}
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{date_id}/delete-for-me")
async def delete_vibe_date_for_me(date_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a date proposal from the current user's view permanently."""
    try:
        success = await vibe_date_service.delete_date_for_me(current_user["id"], date_id)
        if not success:
             raise HTTPException(status_code=400, detail="Cannot delete this date.")
        return {"success": True, "message": "Date deleted."}
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
