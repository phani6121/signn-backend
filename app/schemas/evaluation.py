from typing import Dict, List

from pydantic import BaseModel


class BehavioralQuestion(BaseModel):
    id: str
    text: str
    choices: List[str]


class EvaluationFinishRequest(BaseModel):
    shift_id: str
    answers: Dict[str, str]


class EvaluationFinishResponse(BaseModel):
    result_id: str
    score: float
    finished_at: str


class EvaluationResultResponse(BaseModel):
    result_id: str
    shift_id: str
    score: float
    verdict: str
    finished_at: str
