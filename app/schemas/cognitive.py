from pydantic import BaseModel


class CognitiveStartRequest(BaseModel):
    shift_id: str


class CognitiveStartResponse(BaseModel):
    cognitive_id: str
    started_at: str
