from typing import Dict

from fastapi import APIRouter

from ...schemas.scan import ScanFrameRequest, ScanStartRequest, ScanStartResponse
from ...services.scanservice import add_scan_frame, start_scan

router = APIRouter()


@router.post("/scan/start", response_model=ScanStartResponse)
def scan_start(payload: ScanStartRequest) -> ScanStartResponse:
    return start_scan(payload)


@router.post("/scan/frame")
def scan_frame(payload: ScanFrameRequest) -> Dict[str, object]:
    return add_scan_frame(payload)
