from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Optional

from app.routers.auth import get_current_user
from app.schemas.notification import (
    NotificationCreate, NotificationResponse, NotificationPaginatedResponse, GenericResponse, PresenceCreate
)
from app.services.notification import notification_service

router = APIRouter(prefix="/notifications", tags=["Notifications"])

@router.post("/presence", response_model=GenericResponse)
async def log_user_presence(payload: PresenceCreate, current_user: dict = Depends(get_current_user)):
    """Log user presence and trigger a notification for the partner."""
    try:
        result = await notification_service.log_presence(current_user["id"], payload)
        return GenericResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/schedule", response_model=NotificationResponse)
async def schedule_notification(payload: NotificationCreate, current_user: dict = Depends(get_current_user)):
    """Schedule a new notification for yourself or your partner."""
    return await notification_service.schedule_notification(current_user["id"], payload)

@router.get("/", response_model=NotificationPaginatedResponse)
async def list_my_notifications(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    timezone: str = Query("UTC"),
    types: Optional[str] = Query(None, description="Comma-separated list of notification types to filter"),
    is_hidden: Optional[bool] = Query(None, description="Filter by hidden status"),
    current_user: dict = Depends(get_current_user)
):
    """List notifications received by the current user."""
    type_list = [t.strip() for t in types.split(",")] if types else None
    data, total, unread_count = await notification_service.get_my_notifications(current_user["id"], page, size, timezone, type_list, is_hidden)
    return NotificationPaginatedResponse(success=True, data=data, total=total, unread_count=unread_count, page=page, size=size)

@router.patch("/{notification_id}/seen", response_model=GenericResponse)
async def mark_notification_seen(notification_id: str, current_user: dict = Depends(get_current_user)):
    """Mark a notification as seen."""
    success = await notification_service.mark_as_seen(notification_id, current_user["id"])
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found.")
    return GenericResponse(success=True, message="Notification marked as seen.")

@router.patch("/{notification_id}/unread", response_model=GenericResponse)
async def mark_notification_unread(notification_id: str, current_user: dict = Depends(get_current_user)):
    """Mark a notification as unread."""
    success = await notification_service.mark_as_unread(notification_id, current_user["id"])
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found or already unread.")
    return GenericResponse(success=True, message="Notification marked as unread.")

@router.patch("/{notification_id}/hide", response_model=GenericResponse)
async def hide_notification(notification_id: str, current_user: dict = Depends(get_current_user)):
    """Hide a notification."""
    success = await notification_service.hide_notification(notification_id, current_user["id"])
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found.")
    return GenericResponse(success=True, message="Notification hidden.")

@router.patch("/{notification_id}/unhide", response_model=GenericResponse)
async def unhide_notification(notification_id: str, current_user: dict = Depends(get_current_user)):
    """Unhide a notification."""
    success = await notification_service.unhide_notification(notification_id, current_user["id"])
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found.")
    return GenericResponse(success=True, message="Notification unhidden.")

@router.delete("/", response_model=GenericResponse)
async def clear_all_notifications(current_user: dict = Depends(get_current_user)):
    """Clear all notifications for the user."""
    count = await notification_service.clear_all_notifications(current_user["id"])
    return GenericResponse(success=True, message=f"Cleared {count} notifications.")

@router.delete("/{notification_id}", response_model=GenericResponse)
async def delete_notification(notification_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a specific notification."""
    success = await notification_service.delete_notification(notification_id, current_user["id"])
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found.")
    return GenericResponse(success=True, message="Notification deleted.")
