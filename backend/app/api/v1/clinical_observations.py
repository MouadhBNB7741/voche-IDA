from fastapi import APIRouter, HTTPException, Depends, status, Query
from typing import List
from uuid import UUID
from app.api.dependencies.connections import get_connection
from app.api.middleware.auth_middleware import auth_middleware
from app.models.clinical_model import ClinicalModel
from app.schemas.clinical_observation import CreateObservationRequest, ObservationResponse

router = APIRouter(prefix="/clinical-observations", tags=["Clinical Observations"])

@router.post("/", response_model=ObservationResponse, status_code=status.HTTP_201_CREATED)
async def create_observation(
    request: CreateObservationRequest,
    conn=Depends(get_connection),
    current_user: dict = Depends(auth_middleware),
):
    # Role Check: HCP Only
    if current_user.get("user_type") != "hcp":
        raise HTTPException(
            status_code=403, 
            detail="Only verified HCPs can submit observations"
        )
        
    model = ClinicalModel(conn)
    
    # Verify trial exists
    trial = await model.get_trial_by_id(str(request.trial_id))
    if not trial:
        raise HTTPException(status_code=404, detail="Trial not found")
        
    result = await model.create_observation(
        str(request.trial_id),
        current_user["id"],
        request.model_dump()
    )
    return result

@router.get("/trial/{trial_id}", response_model=List[ObservationResponse])
async def get_trial_observations(
    trial_id: UUID,
    conn=Depends(get_connection),
    current_user: dict = Depends(auth_middleware),
):

    if current_user.get("user_type") not in ["hcp", "admin"]:
         raise HTTPException(
            status_code=403, 
            detail="Access restricted to HCPs"
        )
        
    model = ClinicalModel(conn)
    return await model.get_observations(str(trial_id))
