from typing import List
from uuid import uuid4

from fastapi import HTTPException

from ..core.firebase import firestore_manager
from ..schemas.evaluation import (
    BehavioralQuestion,
    EvaluationFinishRequest,
    EvaluationFinishResponse,
    EvaluationResultResponse,
)
from .shiftservice import evaluation_results, shifts, utc_now_iso

def get_behavioral_questions() -> List[BehavioralQuestion]:
    return [
        BehavioralQuestion(
            id="q1",
            text="How often do you feel distracted during a shift?",
            choices=["Never", "Rarely", "Sometimes", "Often", "Always"],
        ),
        BehavioralQuestion(
            id="q2",
            text="How confident do you feel in handling unexpected events?",
            choices=["Not at all", "Slightly", "Moderately", "Very", "Extremely"],
        ),
    ]




QUESTION_LOOKUP = {q.id: q.text for q in get_behavioral_questions()}

def finish_evaluation(payload: EvaluationFinishRequest) -> EvaluationFinishResponse:
    if payload.shift_id not in shifts:
        raise HTTPException(status_code=404, detail="Shift not found")
    result_id = uuid4().hex
    score = max(0.0, min(1.0, 0.5 + 0.05 * len(payload.answers)))
    finished_at = utc_now_iso()
    verdict = "pass" if score >= 0.6 else "review"
    evaluation_results[result_id] = EvaluationResultResponse(
        result_id=result_id,
        shift_id=payload.shift_id,
        score=score,
        verdict=verdict,
        finished_at=finished_at,
    )
    firestore_manager.create_document(
        "evaluation_results",
        result_id,
        {
            "result_id": result_id,
            "session_id": payload.shift_id,
            "finished_at": finished_at,
            "verdict": verdict,
            "score": score,
        },
        merge=True,
    )
    for question_id, choice in payload.answers.items():
        behavioral_id = uuid4().hex
        question_text = QUESTION_LOOKUP.get(question_id, question_id)
        firestore_manager.create_document(
            "behavioral_questions",
            behavioral_id,
            {
                "behavioral_id": behavioral_id,
                "session_id": payload.shift_id,
                "question_id": question_id,
                "question_text": question_text,
                "choice": choice,
                "created_at": utc_now_iso(),
            },
            merge=True,
        )
    return EvaluationFinishResponse(result_id=result_id, score=score, finished_at=finished_at)


def get_evaluation_result(result_id: str) -> EvaluationResultResponse:
    if result_id not in evaluation_results:
        raise HTTPException(status_code=404, detail="Result not found")
    return evaluation_results[result_id]
