from typing import Dict

from fastapi import APIRouter

from ...schemas.shift import (
    ShiftCameraRequest,
    ShiftConsentRequest,
    ShiftStartRequest,
    ShiftStartResponse,
)
from ...services.shiftservice import set_shift_camera, set_shift_consent, start_shift

router = APIRouter()


@router.post("/shift/start", response_model=ShiftStartResponse)
def shift_start(payload: ShiftStartRequest) -> ShiftStartResponse:
    return start_shift(payload)


@router.post("/shift/{shift_id}/consent")
def shift_consent(shift_id: str, payload: ShiftConsentRequest) -> Dict[str, object]:
    return set_shift_consent(shift_id, payload)


@router.post("/shift/{shift_id}/camera/enable")
def shift_camera_enable(shift_id: str, payload: ShiftCameraRequest) -> Dict[str, object]:
    return set_shift_camera(shift_id, payload)
