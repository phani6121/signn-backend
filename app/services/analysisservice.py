from fastapi import HTTPException

from ..schemas.analysis import AnalysisDetailsResponse, AnalysisStatusResponse
from .shiftservice import analysis_status, shifts, utc_now_iso


def get_analysis_status(shift_id: str) -> AnalysisStatusResponse:
    if shift_id not in shifts:
        raise HTTPException(status_code=404, detail="Shift not found")
    status = analysis_status.get(shift_id, "pending")
    return AnalysisStatusResponse(shift_id=shift_id, status=status, updated_at=utc_now_iso())


def get_analysis_details(shift_id: str) -> AnalysisDetailsResponse:
    if shift_id not in shifts:
        raise HTTPException(status_code=404, detail="Shift not found")
    return AnalysisDetailsResponse(
        shift_id=shift_id,
        summary="Preliminary analysis available.",
        signals={"attention": 0.72, "fatigue": 0.18, "stress": 0.33},
        updated_at=utc_now_iso(),
    )
