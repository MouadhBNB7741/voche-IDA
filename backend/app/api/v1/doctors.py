from datetime import date
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends, File, Form, Response, UploadFile, status
from typing import List, Optional
from app.api.dependencies.connections import get_connection

from app.models.doctor_model import DoctorModel
from app.schemas.doctor import VerificationRequest, VerificationResponse, VerificationReview
from app.api.middleware.auth_middleware import auth_middleware, auth_middleware_onboarding
from app.services.storage_service import get_private_storage
from app.services.verification_service import content_type_for, submit_licence

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

@router.post("/verification/upload", response_model=VerificationResponse, status_code=status.HTTP_201_CREATED)
async def submit_verification_with_document(
    license_number: str = Form(..., min_length=1, max_length=100),
    institution: str = Form(..., min_length=1, max_length=255),
    country: str = Form(..., min_length=2, max_length=100),
    specialization: str = Form(..., min_length=2, max_length=100),
    issuing_region: Optional[str] = Form(None, max_length=100),
    expiration_date: Optional[date] = Form(None),
    file: UploadFile = File(...),
    current_user: dict = Depends(auth_middleware_onboarding),
    conn=Depends(get_connection)
):
    """Submit a licence for review, with its document (PDF, JPG, PNG or WEBP, 5 MB max)."""
    return await submit_licence(conn, current_user["id"], {
        "license_number": license_number,
        "institution": institution,
        "country": country,
        "specialization": specialization,
        "issuing_region": issuing_region,
        "expiration_date": expiration_date,
    }, file)

@router.get("/verification/{verification_id}/document")
async def get_verification_document(
    verification_id: UUID,
    current_user: dict = Depends(auth_middleware),
    conn=Depends(get_connection)
):
    """Open a licence document. Only admins and the doctor who uploaded it can see it."""
    verification = await DoctorModel(conn).get_verification(str(verification_id))
    if not verification or not verification.get("document_url"):
        raise HTTPException(status_code=404, detail="Document not found")
    if not is_admin(current_user) and verification["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="You do not have access to this document")

    key = verification["document_url"]
    data = await get_private_storage().read(key)
    if data is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return Response(content=data, media_type=content_type_for(key), headers={
        "Content-Disposition": f'inline; filename="licence.{key.rsplit(".", 1)[-1]}"',
        "Cache-Control": "private, no-store",
        "X-Content-Type-Options": "nosniff",
    })

@router.get("/verification", response_model=VerificationResponse)
async def get_my_verification(
    current_user: dict = Depends(auth_middleware_onboarding),
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
