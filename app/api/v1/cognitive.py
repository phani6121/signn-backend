from fastapi import APIRouter

from ...schemas.cognitive import CognitiveStartRequest, CognitiveStartResponse
from ...services.shiftservice import start_cognitive

router = APIRouter()


@router.post("/cognitive/start", response_model=CognitiveStartResponse)
def cognitive_start(payload: CognitiveStartRequest) -> CognitiveStartResponse:
    return start_cognitive(payload)
