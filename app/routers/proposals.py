from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from app.routers.auth import get_current_user
from app.schemas.proposals import ProposalCreate, ProposalResponse, GenericProposalResponse
from app.services.proposals import proposal_service

router = APIRouter(prefix="/proposals", tags=["Proposals"])

@router.post("/", response_model=ProposalResponse)
async def create_proposal(payload: ProposalCreate, current_user: dict = Depends(get_current_user)):
    """Create a new proposal and notify the partner."""
    try:
        doc = await proposal_service.create_proposal(current_user["id"], payload)
        return ProposalResponse(**doc)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/pending", response_model=List[ProposalResponse])
async def get_pending_proposals(current_user: dict = Depends(get_current_user)):
    """Get all pending proposals for the current user and their partner."""
    try:
        proposals = await proposal_service.get_pending_proposals(current_user["id"])
        return proposals
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{proposal_id}/approve", response_model=GenericProposalResponse)
async def approve_proposal(proposal_id: str, current_user: dict = Depends(get_current_user)):
    """Approve a proposal."""
    try:
        success = await proposal_service.approve_proposal(current_user["id"], proposal_id)
        return GenericProposalResponse(success=success, message="Proposal approved.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{proposal_id}/reject", response_model=GenericProposalResponse)
async def reject_proposal(proposal_id: str, current_user: dict = Depends(get_current_user)):
    """Reject a proposal."""
    try:
        success = await proposal_service.reject_proposal(current_user["id"], proposal_id)
        return GenericProposalResponse(success=success, message="Proposal rejected.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
