from fastapi import APIRouter

from ...schemas.analysis import AnalysisDetailsResponse, AnalysisStatusResponse
from ...services.analysisservice import get_analysis_details, get_analysis_status

router = APIRouter()


@router.get("/analysis/status/{shift_id}", response_model=AnalysisStatusResponse)
def analysis_status(shift_id: str) -> AnalysisStatusResponse:
    return get_analysis_status(shift_id)


@router.get("/analysis/details/{shift_id}", response_model=AnalysisDetailsResponse)
def analysis_details(shift_id: str) -> AnalysisDetailsResponse:
    return get_analysis_details(shift_id)
