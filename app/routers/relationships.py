import os
import uuid
import shutil
import cv2
import numpy as np
from typing import Optional
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Response, Query
from fastapi.responses import FileResponse
from app.schemas.relationships import (
    RelationshipCreate,
    RelationshipResponse,
    AlignRequest,
    AlignResponse,
    BreakAlignmentRequest,
    RespondAlignmentRequest,
    CancelAlignmentRequest,
    PartnerPictureData,
    PartnerPictureResponse,
)
from app.services.relationships import relationship_service
from app.services.s3_utils import s3_service
from app.routers.auth import get_current_user
from app.schemas.auth import UserUpdate, UserMeResponse

router = APIRouter(prefix="/users", tags=["Users"])

@router.patch("/me", response_model=UserMeResponse, status_code=status.HTTP_200_OK, response_model_exclude_none=True)
async def update_user_profile_endpoint(payload: UserUpdate, current_user: dict = Depends(get_current_user)):
    """Updates the authenticated user's profile details."""
    try:
        update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
        if not update_data:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update.")
        updated = await relationship_service.update_user(current_user["id"], update_data)
        return updated
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred updating profile: {str(e)}"
        )

@router.get("", response_model=RelationshipResponse, status_code=status.HTTP_200_OK, response_model_exclude_none=True)
async def get_user_profile(current_user: dict = Depends(get_current_user)):
    """
    Retrieves the relationship profile details of the authenticated user.
    """
    try:
        data = await relationship_service.get_relationship_profile(current_user["id"], user=current_user)
        return RelationshipResponse(
            success=True,
            message="Relationship details retrieved successfully!",
            data=data
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred retrieving relationship data: {str(e)}"
        )

@router.get("/partner", response_model=RelationshipResponse, status_code=status.HTTP_200_OK, response_model_exclude_none=True)
async def get_partner_profile(current_user: dict = Depends(get_current_user)):
    """
    Retrieves the relationship profile details of the aligned partner.
    """
    try:
        data = await relationship_service.get_partner_details(current_user["id"], user=current_user)
        return RelationshipResponse(
            success=True,
            message="Partner details retrieved successfully!",
            data=data
        )
    except ValueError as ve:
        if str(ve) == "You are not aligned with any partner.":
            return RelationshipResponse(
                success=False,
                message=str(ve),
                data=None
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred retrieving partner data: {str(e)}"
        )

@router.get("/partner/picture", response_model=PartnerPictureResponse, status_code=status.HTTP_200_OK)
async def get_partner_profile_picture(
    response: Response,
    context: str = Query("aligned", pattern="^(aligned|vibe)$"),
    partner_id: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """
    Super-fast endpoint returning the partner's current profile picture.
    - context='aligned': fetches aligned partner from `users` collection.
    - context='vibe': fetches specific vibe partner from `vibe_check_profiles` by `partner_id`.
    Applies CloudFront CDN conversion and HTTP caching headers.
    """
    try:
        if context == "aligned":
            aligned_partner_id = current_user.get("partner", {}).get("user_id") if isinstance(current_user.get("partner"), dict) else None
            if not aligned_partner_id:
                u = await relationship_service.collection.find_one(
                    {"_id": ObjectId(current_user["id"])},
                    {"partner.user_id": 1, "is_aligned": 1}
                )
                if u and u.get("is_aligned"):
                    aligned_partner_id = u.get("partner", {}).get("user_id")

            if not aligned_partner_id:
                return PartnerPictureResponse(success=False, message="No aligned partner found.", data=None)

            partner = await relationship_service.collection.find_one(
                {"_id": ObjectId(aligned_partner_id)},
                {"profile_photo_url": 1, "name": 1, "profile_photos": 1}
            )
            if not partner:
                return PartnerPictureResponse(success=False, message="Partner profile not found.", data=None)

            raw_pic = partner.get("profile_photo_url")
            if not raw_pic and partner.get("profile_photos"):
                photos = partner.get("profile_photos")
                if isinstance(photos, list) and len(photos) > 0:
                    raw_pic = photos[0].get("url")

            cdn_url = s3_service.to_cdn_url(raw_pic) if raw_pic else None
            response.headers["Cache-Control"] = "private, max-age=60, stale-while-revalidate=300"

            return PartnerPictureResponse(
                success=True,
                data=PartnerPictureData(
                    partner_id=str(partner["_id"]),
                    name=partner.get("name", "Partner"),
                    picture_url=cdn_url,
                    context="aligned"
                )
            )

        elif context == "vibe":
            from app.services.vibe_check import vibe_check_service
            target_pid = partner_id
            if not target_pid:
                vibe_conn = await vibe_check_service.connections.find_one(
                    {"user_id": current_user["id"]},
                    {"partner_id": 1}
                )
                if vibe_conn:
                    target_pid = vibe_conn["partner_id"]

            if not target_pid:
                return PartnerPictureResponse(success=False, message="No vibe partner specified or found.", data=None)

            vibe_profile = await vibe_check_service.profiles.find_one(
                {"user_id": target_pid},
                {"profile_picture": 1, "name": 1}
            )
            if not vibe_profile:
                return PartnerPictureResponse(success=False, message="Vibe partner profile not found.", data=None)

            raw_pic = vibe_profile.get("profile_picture")
            cdn_url = s3_service.to_cdn_url(raw_pic) if raw_pic else None
            response.headers["Cache-Control"] = "private, max-age=60, stale-while-revalidate=300"

            return PartnerPictureResponse(
                success=True,
                data=PartnerPictureData(
                    partner_id=target_pid,
                    name=vibe_profile.get("name", "Vibe Partner"),
                    picture_url=cdn_url,
                    context="vibe"
                )
            )
        else:
            return PartnerPictureResponse(success=False, message="Invalid context specified.", data=None)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving partner picture: {str(e)}"
        )

@router.post("/create", response_model=RelationshipResponse, status_code=status.HTTP_201_CREATED, response_model_exclude_none=True)
async def create_relationship(submission: RelationshipCreate, current_user: dict = Depends(get_current_user)):
    """
    Saves or updates the relationship profile details of the authenticated user.
    
    Accepts:
    - name: string
    - City Name (or city_name): string
    - relationship start date (or relationship_start_date) in format mm.dd,yyyy or mm.dd.yyyy
    - is logn distance relation (or is_long_distance) [true/false]
    """
    try:
        saved_data = await relationship_service.update_relationship_profile(current_user["id"], submission, user=current_user)
        return RelationshipResponse(
            success=True,
            message="Relationship details saved successfully!",
            data=saved_data
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred saving relationship data: {str(e)}"
        )

@router.post("/aligned/request", status_code=status.HTTP_200_OK)
async def create_alignment_request_endpoint(payload: AlignRequest, current_user: dict = Depends(get_current_user)):
    """Sends a connection request to the partner with the specified secret key."""
    try:
        req = await relationship_service.create_alignment_request(current_user["id"], payload.secret_key)
        return {
            "success": True,
            "message": "Alignment request created.",
            "data": req
        }
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred sending alignment request: {str(e)}"
        )

@router.get("/aligned/request", status_code=status.HTTP_200_OK)
async def get_alignment_request_status_endpoint(current_user: dict = Depends(get_current_user)):
    """Gets current incoming and outgoing alignment requests."""
    try:
        data = await relationship_service.get_alignment_request_status(current_user["id"], user=current_user)
        return {
            "success": True,
            "data": data
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred getting alignment status: {str(e)}"
        )

@router.post("/aligned/request/respond", status_code=status.HTTP_200_OK)
async def respond_alignment_request_endpoint(payload: RespondAlignmentRequest, current_user: dict = Depends(get_current_user)):
    """Approves or declines an incoming alignment request."""
    try:
        res = await relationship_service.respond_alignment_request(current_user["id"], payload.request_id, payload.accept)
        return {
            "success": True,
            "message": "Request approved and aligned!" if payload.accept else "Request declined.",
            "data": res
        }
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred responding to request: {str(e)}"
        )

@router.post("/aligned/request/cancel", status_code=status.HTTP_200_OK)
async def cancel_alignment_request_endpoint(payload: CancelAlignmentRequest, current_user: dict = Depends(get_current_user)):
    """Cancels a pending outgoing alignment request."""
    try:
        res = await relationship_service.cancel_alignment_request(current_user["id"], payload.request_id)
        return {
            "success": True,
            "message": "Request cancelled successfully.",
            "data": res
        }
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred cancelling request: {str(e)}"
        )

@router.post("/regenerate-key", status_code=status.HTTP_200_OK)
async def regenerate_aligned_key_endpoint(current_user: dict = Depends(get_current_user)):
    """Generates a new Aligned secret key for the unaligned user."""
    try:
        new_key = await relationship_service.regenerate_aligned_key(current_user["id"], user=current_user)
        return {
            "success": True,
            "message": "New secret key generated successfully.",
            "secret_key": new_key
        }
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred regenerating key: {str(e)}"
        )

@router.post("/aligned", response_model=AlignResponse, status_code=status.HTTP_200_OK, response_model_exclude_none=True)
async def align_users(payload: AlignRequest, current_user: dict = Depends(get_current_user)):
    """
    Connects the authenticated user with another user using the partner's secret key.
    
    After connection:
    - Both users will have is_aligned set to true.
    - Each user will have the partner's information stored in their database record.
    """
    try:
        updated_user = await relationship_service.align_users(current_user["id"], payload.secret_key)
        return AlignResponse(
            success=True,
            message="Users successfully connected and aligned!",
            data=updated_user
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred connecting users: {str(e)}"
        )

@router.post("/break-alignment", response_model=AlignResponse, status_code=status.HTTP_200_OK, response_model_exclude_none=True)
async def break_alignment(payload: BreakAlignmentRequest, current_user: dict = Depends(get_current_user)):
    """
    Breaks the connection between the authenticated user and their partner, requiring a password.
    """
    try:
        from bson import ObjectId
        from app.services.auth import verify_password
        
        user_record = await relationship_service.collection.find_one({"_id": ObjectId(current_user["id"])})
        if not user_record:
            raise ValueError("User not found")
            
        # Verify password strictly
        hashed_password = user_record.get("password_hash")
        if not hashed_password or not verify_password(payload.password, hashed_password):
            raise ValueError("Incorrect password.")
            
        partner_id = user_record.get("partner", {}).get("user_id")
        updated_user = await relationship_service.break_alignment(current_user["id"])
        
        # Also auto-demote the vibe ladder for both users
        from app.services.vibe_pulse import vibe_pulse_service
        from app.schemas.vibe_pulse import PulseStatus
        from datetime import datetime, timezone
        
        now = datetime.now(timezone.utc)
        
        if partner_id:
            # 1. Demote current user's pulse
            await vibe_pulse_service.pulses.update_one(
                {"user_id": current_user["id"], "partner_id": partner_id, "status": PulseStatus.ALIGNED.value},
                {"$set": {
                    "status": PulseStatus.SERIOUS.value,
                    "updated_at": now
                }}
            )
            
            # 2. Demote partner's pulse
            their_pulse = await vibe_pulse_service.pulses.find_one({"user_id": partner_id, "partner_id": current_user["id"]})
            if their_pulse and their_pulse["status"] == PulseStatus.ALIGNED:
                await vibe_pulse_service.pulses.update_one(
                    {"user_id": partner_id, "partner_id": current_user["id"]},
                    {"$set": {
                        "status": PulseStatus.SERIOUS.value,
                        "updated_at": now
                    }}
                )
                
            # Broadcast real-time update to both users so their screens auto-reload
            try:
                from app.core.websocket import ws_manager
                await ws_manager.broadcast_to_user(partner_id, {"type": "PULSE_UPDATED"})
                await ws_manager.broadcast_to_user(partner_id, {"type": "ALIGNMENT_BROKEN"})
                await ws_manager.broadcast_to_user(current_user["id"], {"type": "ALIGNMENT_BROKEN"})
            except Exception:
                pass
        
        return AlignResponse(
            success=True,
            message="Relationship alignment broken successfully.",
            data=updated_user
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred breaking alignment: {str(e)}"
        )

@router.post("/photo", status_code=status.HTTP_200_OK)
@router.post("/photos", status_code=status.HTTP_200_OK)
async def upload_photo(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    """Uploads a profile photo for the authenticated user."""
    try:
        contents = await file.read()
        file_bytes = contents
        content_type = file.content_type or "image/jpeg"
        
        try:
            nparr = np.frombuffer(contents, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is not None:
                # Resize to 256x256 using INTER_AREA for downsampling
                resized = cv2.resize(img, (256, 256), interpolation=cv2.INTER_AREA)
                is_success, buffer = cv2.imencode(".jpg", resized, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
                if is_success:
                    file_bytes = buffer.tobytes()
                    content_type = "image/jpeg"
        except Exception as img_err:
            print(f"[Upload Photo Warning] Image optimization skipped due to format: {img_err}")
            
        filename = f"{uuid.uuid4().hex}.jpg" if content_type == "image/jpeg" else (file.filename or f"{uuid.uuid4().hex}.bin")
        file_url = await s3_service.upload_bytes(file_bytes, filename=filename, content_type=content_type, folder="profiles")
            
        updated = await relationship_service.add_profile_photo(current_user["id"], file_url)
        return {"success": True, "message": "Photo uploaded successfully", "data": updated}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload photo: {str(e)}")

@router.get("/photos", status_code=status.HTTP_200_OK)
@router.get("/photo", status_code=status.HTTP_200_OK)
async def get_my_photos(current_user: dict = Depends(get_current_user)):
    """Retrieves all profile photos for the current user."""
    try:
        data = await relationship_service.get_profile_photos(current_user["id"], user=current_user)
        return {"success": True, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get photos: {str(e)}")

@router.post("/photo/select", status_code=status.HTTP_200_OK)
@router.post("/photos/select", status_code=status.HTTP_200_OK)
async def select_photo(payload: dict, current_user: dict = Depends(get_current_user)):
    """Selects an existing photo as the active profile photo."""
    photo_id = payload.get("photo_id") or payload.get("url")
    if not photo_id:
        raise HTTPException(status_code=400, detail="Missing photo_id")
    try:
        updated = await relationship_service.select_profile_photo(current_user["id"], photo_id)
        return {"success": True, "message": "Profile photo selected", "data": updated}
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to select photo: {str(e)}")

@router.delete("/photo/{photo_id}", status_code=status.HTTP_200_OK)
@router.delete("/photos/{photo_id}", status_code=status.HTTP_200_OK)
async def delete_photo_item(photo_id: str, current_user: dict = Depends(get_current_user)):
    """Deletes a specific profile photo from the user's gallery."""
    try:
        updated = await relationship_service.delete_profile_photo_item(current_user["id"], photo_id)
        return {"success": True, "message": "Photo deleted successfully", "data": updated}
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete photo: {str(e)}")

@router.get("/photo/{user_id}")
async def get_photo(user_id: str, current_user: dict = Depends(get_current_user)):
    """Retrieves the profile photo if the requester is the owner or their aligned partner."""
    try:
        if current_user["id"] == user_id:
            file_path = current_user.get("profile_photo_url")
        else:
            # Check if partner
            partner_info = current_user.get("partner")
            if not partner_info or partner_info.get("user_id") != user_id:
                raise HTTPException(status_code=403, detail="Not authorized to view this photo.")
            file_path = await relationship_service.get_profile_photo_path(user_id)
            
        if not file_path:
            raise HTTPException(status_code=404, detail="Photo not found.")
            
        if s3_service.is_s3_or_cdn_url(file_path):
            from fastapi.responses import RedirectResponse
            return RedirectResponse(url=s3_service.to_cdn_url(file_path))
            
        clean_path = file_path.lstrip("/")
        if not os.path.exists(clean_path):
            raise HTTPException(status_code=404, detail="Photo not found.")
            
        return FileResponse(clean_path)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve photo: {str(e)}")

@router.delete("/photo", status_code=status.HTTP_200_OK)
@router.delete("/photos", status_code=status.HTTP_200_OK)
async def delete_photo(current_user: dict = Depends(get_current_user)):
    """Deletes the current user's profile photo."""
    try:
        file_path = current_user.get("profile_photo_url")
        if file_path:
            if s3_service.is_s3_or_cdn_url(file_path):
                await s3_service.delete_file(file_path)
            elif os.path.exists(file_path):
                os.remove(file_path)
            
        updated = await relationship_service.update_profile_photo(current_user["id"], None)
        return {"success": True, "message": "Photo deleted successfully", "data": updated}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete photo: {str(e)}")

@router.get("/sync-summary", status_code=status.HTTP_200_OK)
async def get_aligned_sync_summary(timezone: str = "UTC", current_user: dict = Depends(get_current_user)):
    """Get the combined sync score and breakdown for the user and their Aligned partner."""
    try:
        return await relationship_service.get_sync_summary(current_user["id"], timezone, user=current_user)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get sync summary: {str(e)}")


