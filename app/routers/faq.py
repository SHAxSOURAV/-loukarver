from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from app.services.faq import faq_service
from app.schemas.faq import FAQCreate, FAQUpdate, FAQResponse
from app.routers.auth import get_current_user

router = APIRouter(prefix="/faq", tags=["faq"])

@router.get("", response_model=List[FAQResponse])
async def get_faqs():
    """Retrieve all FAQs."""
    return await faq_service.get_all()

@router.post("", response_model=FAQResponse, status_code=status.HTTP_201_CREATED)
async def create_faq(payload: FAQCreate, current_user: dict = Depends(get_current_user)):
    """Create a new FAQ. Admin only."""
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can manage FAQs.")
    return await faq_service.create(payload)

@router.put("/{faq_id}", response_model=FAQResponse)
async def update_faq(faq_id: str, payload: FAQUpdate, current_user: dict = Depends(get_current_user)):
    """Update an existing FAQ. Admin only."""
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can manage FAQs.")
        
    updated = await faq_service.update(faq_id, payload)
    if not updated:
        raise HTTPException(status_code=404, detail="FAQ not found")
    return updated

@router.delete("/{faq_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_faq(faq_id: str, current_user: dict = Depends(get_current_user)):
    """Delete an FAQ. Admin only."""
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can manage FAQs.")
        
    deleted = await faq_service.delete(faq_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="FAQ not found")
    return None
