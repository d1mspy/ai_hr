from pydantic import BaseModel, Field
from typing import Dict, List, Any

class MatchDetails(BaseModel):
    bm25: float
    fuzzy: float
    must_coverage: float
    nice_coverage: float
    experience: float

class MatchDecision(BaseModel):
    decision: str = Field(description='"invite" | "manual_review" | "reject"')
    score: float
    reasons: List[str] = []
    details: MatchDetails

class DecideResponse(BaseModel):
    decision: MatchDecision
    cv: Dict[str, Any]
    vacancy: Dict[str, Any]
