from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Optional
from app.api.dependencies.connections import get_connection

from app.models.doctor_model import DoctorModel
from app.schemas.doctor import VerificationRequest, VerificationResponse, VerificationReview
from app.api.middleware.auth_middleware import auth_middleware

router = APIRouter(prefix="/doctors", tags=["Doctor Verification"])

# Helper for admin check
def is_admin(user: dict) -> bool:
    return user.get("user_type") == "admin"


@router.post("/verification", response_model=VerificationResponse, status_code=status.HTTP_201_CREATED)
async def submit_verification(
    request: VerificationRequest,
    current_user: dict = Depends(auth_middleware),
    conn=Depends(get_connection)
):
    model = DoctorModel(conn)
    
    # Check if already pending or approved
    existing = await model.get_verification_by_user(current_user["id"])
    if existing and existing["status"] in ["pending", "approved"]:
        raise HTTPException(
            status_code=400, 
            detail=f"Verification already {existing['status']}"
        )
    
    result = await model.create_verification(current_user["id"], request.model_dump())
    return result

@router.get("/verification", response_model=VerificationResponse)
async def get_my_verification(
    current_user: dict = Depends(auth_middleware),
    conn=Depends(get_connection)
):
    model = DoctorModel(conn)
    result = await model.get_verification_by_user(current_user["id"])
    if not result:
        raise HTTPException(status_code=404, detail="No verification found")
    return result

@router.get("/admin/verifications", response_model=List[VerificationResponse])
async def list_pending_verifications(
    current_user: dict = Depends(auth_middleware),
    conn=Depends(get_connection)
):
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")
        
    model = DoctorModel(conn)
    result = await model.get_pending_verifications()
    return result

@router.patch("/admin/verifications/{verification_id}", response_model=VerificationResponse)
async def review_verification(
    verification_id: str,
    review: VerificationReview,
    current_user: dict = Depends(auth_middleware),
    conn=Depends(get_connection)
):
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")
        
    model = DoctorModel(conn)
    
    result = await model.review_verification(
        verification_id, 
        current_user["id"], 
        review.status.value, 
        review.rejection_reason
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="Verification not found")
        
    return result
