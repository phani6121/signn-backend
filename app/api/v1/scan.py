from typing import Dict

from fastapi import APIRouter

from ...schemas.scan import ScanCompleteRequest, ScanFrameRequest, ScanStartRequest, ScanStartResponse
from ...services.scanservice import add_scan_frame, complete_scan, start_scan

router = APIRouter()


@router.post("/scan/start", response_model=ScanStartResponse)
def scan_start(payload: ScanStartRequest) -> ScanStartResponse:
    return start_scan(payload)


@router.post("/scan/frame")
def scan_frame(payload: ScanFrameRequest) -> Dict[str, object]:
    return add_scan_frame(payload)


@router.post("/scan/complete")
def scan_complete(payload: ScanCompleteRequest) -> Dict[str, object]:
    return complete_scan(payload)
