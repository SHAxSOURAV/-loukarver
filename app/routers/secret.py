from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks, Form, Query, Request
from fastapi.responses import FileResponse, RedirectResponse
from typing import List

from app.core.config import settings
from app.routers.auth import get_current_user
from app.schemas.secret import (
    SecretRead, SecretPaginatedResponse, GenericResponse,
    SecretPatchScreenshot
)
from app.services.secret import secret_service
from app.services.s3_utils import s3_service

router = APIRouter(prefix="/secret", tags=["Secret"])

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

@router.post("/upload", response_model=GenericResponse, status_code=status.HTTP_201_CREATED)
async def upload_secret(
    file: UploadFile = File(...),
    prevent_screenshot: bool = Form(True),
    delete_after: str = Form("24 Hours"),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload a secret file for your partner. Max size: 100MB.
    `prevent_screenshot`: If true, hints the client to block screenshots/recording.
    `delete_after`: Duration (e.g., '10 Minutes', '1 Hours', '10 Seconds').
    """
    try:
        await secret_service.save_secret(current_user["id"], file, prevent_screenshot, delete_after)
        return GenericResponse(success=True, message="Secret sent to partner!")
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.get("/received", response_model=SecretPaginatedResponse)
async def list_received_secrets(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    timezone: str = Query("UTC", description="Your current IANA timezone (e.g. Asia/Dhaka)"),
    current_user: dict = Depends(get_current_user)
):
    """List unviewed secrets received from your partner (Paginated)."""
    try:
        data, total = await secret_service.get_secrets_for_me(current_user["id"], page, size, timezone, user_doc=current_user)
        return SecretPaginatedResponse(success=True, data=data, total=total, page=page, size=size)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sent", response_model=SecretPaginatedResponse)
async def list_sent_secrets(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    timezone: str = Query("UTC", description="Your current IANA timezone (e.g. Asia/Dhaka)"),
    current_user: dict = Depends(get_current_user)
):
    """List unviewed secrets you sent to your partner (Paginated)."""
    try:
        data, total = await secret_service.get_sent_secrets(current_user["id"], page, size, timezone, user_doc=current_user)
        return SecretPaginatedResponse(success=True, data=data, total=total, page=page, size=size)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/{secret_id}/screenshot", response_model=GenericResponse)
async def patch_screenshot_protection(
    secret_id: str,
    payload: SecretPatchScreenshot,
    current_user: dict = Depends(get_current_user)
):
    """Update the screenshot protection state for a secret you sent."""
    try:
        success = await secret_service.patch_screenshot_protection(
            secret_id, current_user["id"], payload.prevent_screenshot
        )
        if not success:
            raise HTTPException(status_code=404, detail="Secret not found or not owned by you.")
        return GenericResponse(success=True, message="Screenshot protection updated.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/view-url/{secret_id}")
async def get_secret_view_url_endpoint(
    secret_id: str,
    timezone: str = Query("UTC", description="Your current IANA timezone (e.g. Asia/Dhaka)"),
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieves the direct viewing URL and metadata for a secret.
    """
    try:
        doc = await secret_service.get_secret_metadata(secret_id, current_user["id"], timezone)
        if doc["recipient_id"] == current_user["id"]:
            await secret_service.mark_secret_viewed(secret_id)

        file_url = doc.get("stored_filename", "")
        if file_url:
            if s3_service.s3_client or getattr(settings, "AWS_CLOUDFRONT_DOMAIN", None) or s3_service.is_s3_or_cdn_url(file_url):
                file_url = s3_service.generate_presigned_view_url(file_url, expires_in=7200)
            elif not file_url.startswith("http") and not file_url.startswith("/"):
                file_url = f"/{file_url}"

        filename = doc.get("filename", "")
        file_type = doc.get("file_type", "")
        is_video = bool((file_type and file_type.startswith("video")) or filename.endswith(".mp4") or filename.endswith(".mov"))

        return {
            "success": True,
            "data": {
                "id": str(doc.get("id") or doc.get("_id")),
                "url": file_url,
                "filename": filename,
                "file_type": file_type,
                "is_video": is_video,
                "prevent_screenshot": doc.get("prevent_screenshot", True),
                "delete_after": doc.get("delete_after", "24 Hours")
            }
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/view/{secret_id}")
async def view_secret(
    secret_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    timezone: str = Query("UTC", description="Your current IANA timezone (e.g. Asia/Dhaka)"),
    current_user: dict = Depends(get_current_user)
):
    """
    Open and view a secret media (video or photo).
    Supports both JSON API consumption for mobile players and direct HTTP redirects.
    """
    try:
        doc = await secret_service.get_secret_metadata(secret_id, current_user["id"], timezone)
        
        # If recipient is viewing, trigger view marking
        if doc["recipient_id"] == current_user["id"]:
            await secret_service.mark_secret_viewed(secret_id)
            
        file_url = doc.get("stored_filename", "")
        if file_url:
            if s3_service.s3_client or getattr(settings, "AWS_CLOUDFRONT_DOMAIN", None) or s3_service.is_s3_or_cdn_url(file_url):
                file_url = s3_service.generate_presigned_view_url(file_url, expires_in=7200)
            elif not file_url.startswith("http") and not file_url.startswith("/"):
                file_url = f"/{file_url}"

        filename = doc.get("filename", "")
        file_type = doc.get("file_type", "")
        is_video = bool((file_type and file_type.startswith("video")) or filename.endswith(".mp4") or filename.endswith(".mov"))

        data = {
            "id": str(doc.get("id") or doc.get("_id")),
            "url": file_url,
            "filename": filename,
            "file_type": file_type,
            "is_video": is_video,
            "prevent_screenshot": doc.get("prevent_screenshot", True),
            "delete_after": doc.get("delete_after", "24 Hours")
        }

        return {
            "success": True,
            "data": data
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{secret_id}/rewatch/request", response_model=GenericResponse)
async def request_rewatch(
    secret_id: str,
    current_user: dict = Depends(get_current_user)
):
    try:
        await secret_service.request_rewatch(secret_id, current_user["id"])
        return GenericResponse(success=True, message="Rewatch requested.")
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{secret_id}/rewatch/approve", response_model=GenericResponse)
async def approve_rewatch(
    secret_id: str,
    current_user: dict = Depends(get_current_user)
):
    try:
        await secret_service.approve_rewatch(secret_id, current_user["id"])
        return GenericResponse(success=True, message="Rewatch approved.")
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{secret_id}/rewatch/decline", response_model=GenericResponse)
async def decline_rewatch(
    secret_id: str,
    current_user: dict = Depends(get_current_user)
):
    try:
        await secret_service.decline_rewatch(secret_id, current_user["id"])
        return GenericResponse(success=True, message="Rewatch declined.")
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{secret_id}/revoke", response_model=GenericResponse)
async def revoke_secret(
    secret_id: str,
    current_user: dict = Depends(get_current_user)
):
    try:
        await secret_service.revoke_secret(secret_id, current_user["id"])
        return GenericResponse(success=True, message="Secret revoked.")
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
