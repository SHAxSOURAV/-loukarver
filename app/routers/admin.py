from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any, Optional
from app.services.admin import admin_service
from app.services.reports import report_service
from app.schemas.admin import DashboardStatsResponse, UserStatusUpdate
from app.routers.auth import get_current_user

router = APIRouter(prefix="/admin", tags=["admin"])

def require_admin(current_user: dict = Depends(get_current_user)):
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can perform this action.")
    return current_user

@router.get("/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(admin: dict = Depends(require_admin)):
    """Get dashboard overview statistics."""
    return await admin_service.get_dashboard_stats()

@router.get("/stats/user-growth")
async def get_user_growth(year: int, admin: dict = Depends(require_admin)):
    """Get user growth chart data for a specific year."""
    return await admin_service.get_user_growth(year)

@router.get("/stats/earnings")
async def get_earnings_growth(year: int, admin: dict = Depends(require_admin)):
    """Get earnings growth chart data for a specific year (currently returns zero)."""
    return await admin_service.get_earnings_growth(year)

@router.get("/recent-collaborations")
async def get_recent_collaborations(admin: dict = Depends(require_admin)):
    """Get recent users with active partner connections."""
    return await admin_service.get_recent_collaborations()

@router.get("/collaborations")
async def get_collaborations(status: str = "All", search: str = "", admin: dict = Depends(require_admin)):
    """Get all collaborations with filtering."""
    return await admin_service.get_collaborations(status, search)

@router.get("/analytics")
async def get_feature_analytics(year: int, feature: str = "CheckIn", admin: dict = Depends(require_admin)):
    """Get analytics data grouped by month and gender for a specific feature."""
    return await admin_service.get_feature_analytics(year, feature)

@router.get("/users", response_model=List[Dict[str, Any]])
async def get_all_users(status_filter: str = "All", admin: dict = Depends(require_admin)):
    """Get all users with filtering by status (All, Blocked, Hidden, Deleted)."""
    return await admin_service.get_users(status_filter)

@router.patch("/users/{user_id}/status", response_model=Dict[str, Any])
async def update_user_status(user_id: str, payload: UserStatusUpdate, admin: dict = Depends(require_admin)):
    """Update user flags: is_blocked, is_hidden, is_deleted."""
    updated_user = await admin_service.update_user_status(
        user_id, 
        is_blocked=payload.is_blocked, 
        is_hidden=payload.is_hidden, 
        is_deleted=payload.is_deleted
    )
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    return updated_user

@router.get("/reports")
async def get_all_reports(status: str = "All", search: str = "", admin: dict = Depends(require_admin)):
    """Get all reports."""
    return await report_service.get_all_reports(status, search)

@router.patch("/reports/{report_id}/status")
async def update_report_status(report_id: str, payload: dict, admin: dict = Depends(require_admin)):
    """Update report status."""
    return await report_service.update_report_status(report_id, payload.get("status"))

@router.get("/reports/{report_id}/messages")
async def get_report_messages(report_id: str, admin: dict = Depends(require_admin)):
    """Get chat messages for a specific report."""
    return await report_service.get_messages(report_id)

@router.post("/reports/{report_id}/messages")
async def add_report_message(report_id: str, payload: dict, admin: dict = Depends(require_admin)):
    """Add a new message from admin."""
    return await report_service.add_message(
        report_id=report_id,
        sender_id=admin["id"],
        sender_type="admin",
        message=payload.get("message"),
        file_url=payload.get("file_url")
    )
