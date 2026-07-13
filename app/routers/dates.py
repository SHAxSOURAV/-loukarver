from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form, Request
from typing import List, Optional
import os
import uuid

from app.routers.auth import get_current_user
from app.schemas.dates import (
    DateCreate, DateUpdate, DateResponse, DatePaginatedResponse,
    DateRespond, DateReviewCreate, GenericResponse, DateReviewsResponse
)
from app.services.dates import date_service

router = APIRouter(prefix="/dates", tags=["Dates"])

@router.post("/", response_model=DateResponse, status_code=status.HTTP_201_CREATED)
async def create_date(payload: DateCreate, current_user: dict = Depends(get_current_user)):
    """Create a new proposed date for your partner."""
    try:
        return await date_service.create_date(current_user["id"], payload)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=DatePaginatedResponse)
async def list_dates(
    status: Optional[str] = Query(None, description="Filter by status (Proposed, Accepted, Rejected, Completed)"),
    search: Optional[str] = Query(None, description="Search term for where, city, name"),
    sort: Optional[str] = Query(None, description="Sort order"),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    timezone: str = Query("UTC", description="Your current IANA timezone (e.g. Asia/Dhaka)"),
    current_user: dict = Depends(get_current_user)
):
    """List dates involving the current user."""
    try:
        data, total = await date_service.get_dates(current_user["id"], status, search, sort, page, size, timezone)
        return DatePaginatedResponse(success=True, data=data, total=total, page=page, size=size)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{date_id}", response_model=DateResponse)
async def get_date(
    date_id: str, 
    timezone: str = Query("UTC", description="Your current IANA timezone (e.g. Asia/Dhaka)"),
    current_user: dict = Depends(get_current_user)
):
    """Get details of a specific date."""
    try:
        date = await date_service.get_date_by_id(date_id, current_user["id"], timezone)
        if not date:
            raise HTTPException(status_code=404, detail="Date not found.")
        return date
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/{date_id}", response_model=DateResponse)
async def update_date(date_id: str, payload: DateUpdate, current_user: dict = Depends(get_current_user)):
    """Update a proposed date. Only the creator can update."""
    try:
        return await date_service.update_date(date_id, current_user["id"], payload)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{date_id}", response_model=GenericResponse)
async def delete_date(date_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a date. Only the creator can delete."""
    try:
        success = await date_service.delete_date(date_id, current_user["id"])
        if not success:
            raise HTTPException(status_code=400, detail="Could not delete date.")
        return GenericResponse(success=True, message="Date deleted successfully.")
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/{date_id}/respond", response_model=DateResponse)
async def respond_to_date(date_id: str, payload: DateRespond, current_user: dict = Depends(get_current_user)):
    """Accept or reject a proposed date. Only the partner can respond."""
    try:
        return await date_service.respond_to_date(date_id, current_user["id"], payload)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/{date_id}/complete", response_model=DateResponse)
async def complete_date(date_id: str, current_user: dict = Depends(get_current_user)):
    """Mark an accepted date as completed. Can only be done after the date time."""
    try:
        return await date_service.complete_date(date_id, current_user["id"])
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{date_id}/review", response_model=DateResponse)
async def add_review(
    date_id: str, 
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Add a review to a completed date with optional photos."""
    try:
        # Parse the form data manually to handle both multipart and urlencoded
        form = await request.form()
        
        rating_val = form.get("rating")
        if rating_val is None:
            raise HTTPException(status_code=422, detail="rating is required")
        rating = int(rating_val)
        if rating < 1 or rating > 5:
            raise HTTPException(status_code=422, detail="rating must be between 1 and 5")
        
        text = str(form.get("text", ""))
        
        photo_urls = []
        # Process uploaded files
        for key in form:
            value = form.getlist(key)
            if key == "files":
                for item in value:
                    if hasattr(item, 'read'):  # It's an UploadFile
                        if not item.filename or item.size == 0:
                            continue
                        os.makedirs("uploads/dates", exist_ok=True)
                        ext = ".jpg"
                        if item.filename:
                            ext = os.path.splitext(item.filename)[1] or ".jpg"
                        filename = f"{uuid.uuid4().hex}{ext}"
                        file_path = os.path.join("uploads", "dates", filename)
                        with open(file_path, "wb") as f:
                            f.write(await item.read())
                        photo_urls.append(f"/{file_path.replace(os.sep, '/')}")
                
        payload = DateReviewCreate(rating=rating, text=text, photos=photo_urls)
        result = await date_service.add_review(date_id, current_user["id"], payload)
        await form.close()
        return result
    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        print(f"Error in add_review route: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{date_id}/review/update", response_model=DateResponse)
async def update_review(
    date_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Update an existing review on a date."""
    try:
        form = await request.form()
        
        rating_val = form.get("rating")
        if rating_val is None:
            raise HTTPException(status_code=422, detail="rating is required")
        rating = int(rating_val)
        if rating < 1 or rating > 5:
            raise HTTPException(status_code=422, detail="rating must be between 1 and 5")
        
        text = str(form.get("text", ""))
        
        existing_photos_raw = form.get("existing_photos")
        existing_photos = []
        if existing_photos_raw:
            import json
            try:
                existing_photos = json.loads(existing_photos_raw)
            except Exception:
                existing_photos = [p.strip() for p in str(existing_photos_raw).split(",") if p.strip()]
        
        photo_urls = list(existing_photos)
        
        # Process newly uploaded files
        for key in form:
            value = form.getlist(key)
            if key == "files":
                for item in value:
                    if hasattr(item, 'read'):  # It's an UploadFile
                        if not item.filename or item.size == 0:
                            continue
                        os.makedirs("uploads/dates", exist_ok=True)
                        ext = ".jpg"
                        if item.filename:
                            ext = os.path.splitext(item.filename)[1] or ".jpg"
                        filename = f"{uuid.uuid4().hex}{ext}"
                        file_path = os.path.join("uploads", "dates", filename)
                        with open(file_path, "wb") as f:
                            f.write(await item.read())
                        photo_urls.append(f"/{file_path.replace(os.sep, '/')}")
                        
        payload = DateReviewCreate(rating=rating, text=text, photos=photo_urls)
        result = await date_service.update_review(date_id, current_user["id"], payload)
        await form.close()
        return result
    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        print(f"Error in update_review route: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{date_id}/reviews", response_model=DateReviewsResponse)
async def get_date_reviews(
    date_id: str, 
    timezone: str = Query("UTC", description="Your current IANA timezone (e.g. Asia/Dhaka)"),
    current_user: dict = Depends(get_current_user)
):
    """Get both user and partner reviews for a specific date."""
    try:
        reviews = await date_service.get_date_reviews(date_id, current_user["id"], timezone)
        return DateReviewsResponse(success=True, data=reviews)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from pydantic import BaseModel

class PingPayload(BaseModel):
    delay: str
    note: str

@router.post("/{date_id}/ping", response_model=GenericResponse)
async def ping_date(date_id: str, payload: PingPayload, current_user: dict = Depends(get_current_user)):
    """Send a running late ping to your partner."""
    try:
        await date_service.ping_date(date_id, current_user["id"], payload.delay, payload.note)
        return GenericResponse(success=True, message="Ping sent successfully.")
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class CancelRequestPayload(BaseModel):
    reason: str

@router.post("/{date_id}/request_cancel", response_model=DateResponse)
async def request_cancel(date_id: str, payload: CancelRequestPayload, current_user: dict = Depends(get_current_user)):
    """Request to cancel an accepted date."""
    try:
        return await date_service.request_cancel(date_id, current_user["id"], payload.reason)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{date_id}/cancel", response_model=DateResponse)
async def cancel_date(date_id: str, current_user: dict = Depends(get_current_user)):
    """Directly cancel an accepted date."""
    try:
        return await date_service.cancel_date(date_id, current_user["id"])
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{date_id}/photos/request_delete", response_model=DateResponse)
async def request_delete_photo(date_id: str, payload: PhotoPayload, current_user: dict = Depends(get_current_user)):
    try:
        return await date_service.request_delete_photo(date_id, current_user["id"], payload.photo_url)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{date_id}/photos/approve_delete", response_model=DateResponse)
async def approve_delete_photo(date_id: str, payload: PhotoPayload, current_user: dict = Depends(get_current_user)):
    try:
        return await date_service.approve_delete_photo(date_id, current_user["id"], payload.photo_url)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{date_id}/photos/reject_delete", response_model=DateResponse)
async def reject_delete_photo(date_id: str, payload: PhotoPayload, current_user: dict = Depends(get_current_user)):
    try:
        return await date_service.reject_delete_photo(date_id, current_user["id"], payload.photo_url)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
