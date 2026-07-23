from fastapi import APIRouter, Depends, HTTPException, Body
from typing import List, Dict, Any, Optional
from app.routers.auth import get_current_user
from app.services.reports import report_service

router = APIRouter(prefix="/reports", tags=["reports"])

@router.post("")
async def create_report(
    title: str = Body(...),
    description: str = Body(...),
    file_url: Optional[str] = Body(None),
    current_user: dict = Depends(get_current_user)
):
    """Create a new report/support ticket."""
    return await report_service.create_report(current_user["id"], title, description, file_url)

@router.get("")
async def get_my_reports(current_user: dict = Depends(get_current_user)):
    """Get all reports created by the current user."""
    return await report_service.get_user_reports(current_user["id"])

@router.get("/{report_id}/messages")
async def get_report_messages(
    report_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get chat messages for a specific report."""
    # Verify ownership (optional extra security: check if report belongs to user)
    return await report_service.get_messages(report_id)

@router.post("/{report_id}/messages")
async def add_report_message(
    report_id: str,
    message: str = Body(...),
    file_url: Optional[str] = Body(None),
    current_user: dict = Depends(get_current_user)
):
    """Add a new message to the report chat from the user."""
    return await report_service.add_message(
        report_id=report_id,
        sender_id=current_user["id"],
        sender_type="user",
        message=message,
        file_url=file_url
    )
