from typing import Dict

from pydantic import BaseModel


class AnalysisStatusResponse(BaseModel):
    shift_id: str
    status: str
    updated_at: str


class AnalysisDetailsResponse(BaseModel):
    shift_id: str
    summary: str
    signals: Dict[str, float]
    updated_at: str
