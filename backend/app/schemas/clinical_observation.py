from datetime import datetime
from uuid import UUID
from typing import Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict

class SeverityLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"

class CreateObservationRequest(BaseModel):
    trial_id: UUID
    summary: str = Field(..., min_length=10)
    feedback_data: Optional[Dict[str, Any]] = {}
    severity_level: SeverityLevel

class ObservationResponse(BaseModel):
    observation_id: UUID
    trial_id: UUID
    doctor_id: UUID
    summary: str
    feedback_data: Dict[str, Any]
    severity_level: str
    flagged: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
