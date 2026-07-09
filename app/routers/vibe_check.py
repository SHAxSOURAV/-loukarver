from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from fastapi.responses import FileResponse
from typing import List, Optional
import os
import shutil
import uuid
from app.routers.auth import get_current_user
from app.schemas.vibe_check import (
    VibeCheckProfileCreate, VibeCheckProfileUpdate, VibeCheckProfileResponse, VibeCheckGenericResponse,
    VibeCheckConnectRequest, VibeCheckConnectionsResponse, VibeCheckRequestsResponse,
    VibeCheckRespondRequest, VibeInviteResponse, VibeInviteValidateResponse,
    VibeInviteAcceptRequest, VibeInviteAcceptResponse, SyncSummaryResponse,
    VibeCheckPasswordRequest, VibeCheckResetRespondRequest
)
from app.services.vibe_check import vibe_check_service
from app.services.auth import verify_password

router = APIRouter(prefix="/vibecheck", tags=["VibeCheck"])

# --- Invite System ---

@router.post("/invite", response_model=VibeInviteResponse)
async def generate_vibecheck_invite(current_user: dict = Depends(get_current_user)):
    """Generate a unique invite link for VibeCheck."""
    try:
        return await vibe_check_service.generate_invite(current_user["id"])
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/invite/{invite_code}", response_model=VibeInviteValidateResponse)
async def validate_vibecheck_invite(invite_code: str):
    """Validate an invite code and return inviter info."""
    try:
        return await vibe_check_service.validate_invite(invite_code)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/invite/accept", response_model=VibeInviteAcceptResponse)
async def accept_vibecheck_invite(payload: VibeInviteAcceptRequest, current_user: dict = Depends(get_current_user)):
    """Accept an invite and connect with the inviter."""
    try:
        return await vibe_check_service.accept_invite(current_user["id"], payload.invite_code)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Existing Endpoints ---

@router.get("/profile", response_model=VibeCheckProfileResponse)
async def get_vibecheck_profile(current_user: dict = Depends(get_current_user)):
    """Get the user's VibeCheck profile."""
    profile = await vibe_check_service.get_profile(current_user["id"])
    if not profile:
        raise HTTPException(status_code=404, detail="VibeCheck profile not setup yet.")
    return profile

@router.post("/setup", response_model=VibeCheckProfileResponse)
async def setup_vibecheck_profile(payload: VibeCheckProfileCreate, current_user: dict = Depends(get_current_user)):
    """Setup or update the user's VibeCheck profile."""
    try:
        return await vibe_check_service.create_or_update_profile(current_user["id"], payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/settings", response_model=VibeCheckProfileResponse)
async def update_vibecheck_settings(payload: VibeCheckProfileUpdate, current_user: dict = Depends(get_current_user)):
    """Update VibeCheck settings (like vibe_key_enabled)."""
    try:
        return await vibe_check_service.update_settings(current_user["id"], payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/connect", response_model=VibeCheckGenericResponse)
async def connect_vibecheck(payload: VibeCheckConnectRequest, current_user: dict = Depends(get_current_user)):
    """Connect with another user using their Vibe Key."""
    try:
        return await vibe_check_service.connect_with_partner(current_user["id"], payload.vibe_key)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/connections", response_model=VibeCheckConnectionsResponse)
async def list_vibecheck_connections(current_user: dict = Depends(get_current_user)):
    """List all people you are connected with in VibeCheck."""
    try:
        connections = await vibe_check_service.get_connections(current_user["id"])
        return {"success": True, "data": connections}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/requests", response_model=VibeCheckRequestsResponse)
async def list_vibecheck_requests(current_user: dict = Depends(get_current_user)):
    """List all pending connection requests."""
    try:
        requests = await vibe_check_service.get_pending_requests(current_user["id"])
        return {"success": True, "data": requests}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/requests/{request_id}/respond", response_model=VibeCheckGenericResponse)
async def respond_vibecheck_request(
    request_id: str, 
    payload: VibeCheckRespondRequest, 
    current_user: dict = Depends(get_current_user)
):
    """Accept or reject a connection request."""
    try:
        return await vibe_check_service.respond_to_request(current_user["id"], request_id, payload.accept)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/connection/{partner_id}/break", response_model=VibeCheckGenericResponse)
async def break_vibecheck_connection(
    partner_id: str, 
    payload: VibeCheckPasswordRequest, 
    current_user: dict = Depends(get_current_user)
):
    """Remove a connection from your VibeCheck network (requires password)."""
    try:
        if not verify_password(payload.password, current_user.get("password_hash", "")):
            raise HTTPException(status_code=401, detail="Invalid password.")
        
        from app.services.vibe_check import vibe_check_service
        result = await vibe_check_service.delete_connection(current_user["id"], partner_id)
        if not result:
            raise HTTPException(status_code=404, detail="Connection not found")
        return {"success": True, "message": "Connection broken"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/connection/{partner_id}/reset/request")
async def request_reset_connection(
    partner_id: str, 
    payload: VibeCheckPasswordRequest, 
    current_user: dict = Depends(get_current_user)
):
    """Send a reset request to your partner (requires password)."""
    try:
        if not verify_password(payload.password, current_user.get("password_hash", "")):
            raise HTTPException(status_code=401, detail="Invalid password.")
            
        return await vibe_check_service.request_reset_connection(current_user["id"], partner_id)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/connection/{request_id}/reset/respond", response_model=VibeCheckGenericResponse)
async def respond_reset_vibecheck_connection(
    request_id: str, 
    payload: VibeCheckResetRespondRequest, 
    current_user: dict = Depends(get_current_user)
):
    """Accept or reject a connection reset request."""
    try:
        return await vibe_check_service.respond_reset_connection(current_user["id"], request_id, payload.accept)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/connections/{partner_id}/release", response_model=VibeCheckGenericResponse)
async def release_connection(partner_id: str, current_user: dict = Depends(get_current_user)):
    """Release a stalled connection."""
    try:
        return await vibe_check_service.release_connection(current_user["id"], partner_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/connections/{partner_id}/restore", response_model=VibeCheckGenericResponse)
async def restore_connection(partner_id: str, current_user: dict = Depends(get_current_user)):
    """Restore a released connection."""
    try:
        return await vibe_check_service.restore_connection(current_user["id"], partner_id)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/regenerate-key", response_model=VibeCheckGenericResponse)
async def regenerate_vibecheck_key(current_user: dict = Depends(get_current_user)):
    """Generate a new unique Vibe Key for your profile."""
    try:
        new_key = await vibe_check_service.regenerate_vibe_key(current_user["id"])
        return {"success": True, "message": f"New Vibe Key generated: {new_key}"}
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/check", response_model=VibeCheckGenericResponse)
async def check_vibecheck_status(current_user: dict = Depends(get_current_user)):
    """Check if VibeCheck profile exists."""
    profile = await vibe_check_service.get_profile(current_user["id"])
    if profile:
        return {"success": True, "message": f"Profile exists for {profile['name']}"}
    return {"success": False, "message": "Profile not setup"}

# --- Profile Management ---

@router.patch("/profile", response_model=VibeCheckProfileResponse)
async def update_vibecheck_profile(payload: VibeCheckProfileUpdate, current_user: dict = Depends(get_current_user)):
    """Update the user's VibeCheck profile (name)."""
    try:
        return await vibe_check_service.update_profile(current_user["id"], name=payload.name)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/profile/picture", response_model=VibeCheckProfileResponse)
async def upload_vibecheck_profile_picture(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload or update profile picture for VibeCheck."""
    try:
        os.makedirs("uploads/vibecheck", exist_ok=True)
        ext = os.path.splitext(file.filename)[1] if file.filename else ".jpg"
        if not ext:
            ext = ".jpg"
        filename = f"{uuid.uuid4().hex}{ext}"
        file_path = os.path.join("uploads", "vibecheck", filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return await vibe_check_service.update_profile_picture(current_user["id"], file_path)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/profile/picture", response_model=VibeCheckGenericResponse)
async def delete_vibecheck_profile_picture(current_user: dict = Depends(get_current_user)):
    """Delete the user's VibeCheck profile picture."""
    try:
        return await vibe_check_service.delete_profile_picture(current_user["id"])
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/profile", response_model=VibeCheckGenericResponse)
async def delete_vibecheck_profile(current_user: dict = Depends(get_current_user)):
    """Delete the user's entire VibeCheck profile and all related data."""
    try:
        return await vibe_check_service.delete_profile(current_user["id"])
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/scan-qr", response_model=VibeCheckGenericResponse)
async def scan_qr_from_image(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Scan a QR code from an uploaded image to extract a Vibe Key."""
    try:
        import cv2
        import numpy as np
        
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            raise ValueError("Could not decode image.")
            
        detector = cv2.QRCodeDetector()
        data, bbox, _ = detector.detectAndDecode(img)
        
        if not data:
            raise ValueError("No QR code found in the image.")
            
        return {"success": True, "message": data}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sync-summary", response_model=SyncSummaryResponse)
async def get_sync_summary(partner_id: Optional[str] = Query(None), timezone: str = "UTC", current_user: dict = Depends(get_current_user)):
    """Get the combined sync score and breakdown for the user and their partner."""
    try:
        return await vibe_check_service.get_sync_summary(current_user["id"], timezone, partner_id=partner_id)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
