from typing import List

from fastapi import APIRouter

from ...schemas.evaluation import (
    BehavioralQuestion,
    EvaluationFinishRequest,
    EvaluationFinishResponse,
    EvaluationResultResponse,
)
from ...services.evaluationservice import finish_evaluation, get_behavioral_questions, get_evaluation_result

router = APIRouter()


@router.get("/evaluation/behavioral/questions", response_model=List[BehavioralQuestion])
def evaluation_questions() -> List[BehavioralQuestion]:
    return get_behavioral_questions()


@router.post("/evaluation/finish", response_model=EvaluationFinishResponse)
def evaluation_finish(payload: EvaluationFinishRequest) -> EvaluationFinishResponse:
    return finish_evaluation(payload)


@router.get("/evaluation/result/{result_id}", response_model=EvaluationResultResponse)
def evaluation_result(result_id: str) -> EvaluationResultResponse:
    return get_evaluation_result(result_id)
