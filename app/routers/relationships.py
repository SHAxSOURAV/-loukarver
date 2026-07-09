import os
import uuid
import shutil
import cv2
import numpy as np
from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File
from fastapi.responses import FileResponse
from app.schemas.relationships import RelationshipCreate, RelationshipResponse, AlignRequest, AlignResponse, BreakAlignmentRequest
from app.services.relationships import relationship_service
from app.routers.auth import get_current_user
from app.schemas.auth import UserUpdate

router = APIRouter(prefix="/users", tags=["Users"])

@router.patch("/me", response_model=RelationshipResponse, status_code=status.HTTP_200_OK, response_model_exclude_none=True)
async def update_user_profile_endpoint(payload: UserUpdate, current_user: dict = Depends(get_current_user)):
    """Updates the authenticated user's profile details."""
    try:
        updated = await relationship_service.update_user(current_user["id"], payload.model_dump())
        return RelationshipResponse(
            success=True,
            message="Profile updated successfully!",
            data=updated
        )
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
        data = await relationship_service.get_relationship_profile(current_user["id"])
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
        data = await relationship_service.get_partner_details(current_user["id"])
        return RelationshipResponse(
            success=True,
            message="Partner details retrieved successfully!",
            data=data
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred retrieving partner data: {str(e)}"
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
        saved_data = await relationship_service.update_relationship_profile(current_user["id"], submission)
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
        
        # Verify password
        user_record = await relationship_service.collection.find_one({"_id": ObjectId(current_user["id"])})
        if not user_record:
            raise ValueError("User not found")
            
        hashed_password = user_record.get("password_hash")
        if not hashed_password or not verify_password(payload.password, hashed_password):
            raise ValueError("Incorrect password.")
            
        updated_user = await relationship_service.break_alignment(current_user["id"])
        
        # Also auto-demote the vibe ladder for both users
        from app.services.vibe_pulse import vibe_pulse_service
        from app.schemas.vibe_pulse import PulseStatus
        from datetime import datetime, timezone
        
        now = datetime.now(timezone.utc)
        partner_id = user_record.get("partner", {}).get("user_id")
        
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
                
            # Broadcast update to partner so their screen refreshes
            try:
                from app.core.websocket import ws_manager
                await ws_manager.broadcast_to_user(partner_id, {"type": "PULSE_UPDATED"})
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
async def upload_photo(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    """Uploads a profile photo for the authenticated user."""
    try:
        os.makedirs("uploads/profiles", exist_ok=True)
        ext = ".jpg"
        filename = f"{uuid.uuid4().hex}{ext}"
        file_path = os.path.join("uploads", "profiles", filename)
        
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            raise ValueError("Invalid image file uploaded.")
            
        # Resize to 256x256 using INTER_AREA for downsampling
        resized = cv2.resize(img, (256, 256), interpolation=cv2.INTER_AREA)
        
        # Save as optimized JPEG
        cv2.imwrite(file_path, resized, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
            
        updated = await relationship_service.update_profile_photo(current_user["id"], file_path)
        return {"success": True, "message": "Photo uploaded successfully", "data": updated}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload photo: {str(e)}")

@router.get("/photo/{user_id}")
async def get_photo(user_id: str, current_user: dict = Depends(get_current_user)):
    """Retrieves the profile photo if the requester is the owner or their aligned partner."""
    try:
        if current_user["id"] != user_id:
            # Check if partner
            partner_info = current_user.get("partner")
            if not partner_info or partner_info.get("user_id") != user_id:
                raise HTTPException(status_code=403, detail="Not authorized to view this photo.")
                
        file_path = await relationship_service.get_profile_photo_path(user_id)
        if not file_path or not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Photo not found.")
            
        return FileResponse(file_path)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve photo: {str(e)}")

@router.delete("/photo", status_code=status.HTTP_200_OK)
async def delete_photo(current_user: dict = Depends(get_current_user)):
    """Deletes the current user's profile photo."""
    try:
        file_path = await relationship_service.get_profile_photo_path(current_user["id"])
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            
        updated = await relationship_service.update_profile_photo(current_user["id"], None)
        return {"success": True, "message": "Photo deleted successfully", "data": updated}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete photo: {str(e)}")

@router.get("/sync-summary", status_code=status.HTTP_200_OK)
async def get_aligned_sync_summary(timezone: str = "UTC", current_user: dict = Depends(get_current_user)):
    """Get the combined sync score and breakdown for the user and their Aligned partner."""
    try:
        return await relationship_service.get_sync_summary(current_user["id"], timezone)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get sync summary: {str(e)}")


