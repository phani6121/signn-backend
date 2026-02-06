from typing import Optional

from pydantic import BaseModel, Field


class ShiftStartRequest(BaseModel):
    user_id: str
    location: Optional[str] = None


class ShiftStartResponse(BaseModel):
    shift_id: str
    started_at: str


class ShiftConsentRequest(BaseModel):
    consent: bool = Field(..., description="User consent to begin the shift.")


class ShiftCameraRequest(BaseModel):
    enabled: bool = True
