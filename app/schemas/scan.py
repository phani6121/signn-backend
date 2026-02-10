from typing import Optional

from pydantic import BaseModel


class ScanStartRequest(BaseModel):
    shift_id: str


class ScanStartResponse(BaseModel):
    scan_id: str
    started_at: str


class ScanFrameRequest(BaseModel):
    scan_id: str
    frame_b64: Optional[str] = None
    frame_data: Optional[dict] = None


class ScanCompleteRequest(BaseModel):
    scan_id: str
