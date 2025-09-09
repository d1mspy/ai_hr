from pydantic import BaseModel
from typing import Any, Dict, List

# спаршенный документ в md и json(sections)
# detected_meta - email и телефон
class ParsedDoc(BaseModel):
    text: str
    contacts: Dict[str, Any] | None = None
    
class ParsedText(BaseModel):
    cv_text: str | None = None
    vac_text: str | None = None

# ответ в виде обоих спаршенных документов
class ParsedDocsResponse(BaseModel):
    cv: ParsedDoc
    vacancy: Dict[str, Any]
    
class CompareResponse(BaseModel):
    decision: Dict[str, Any]
    vacancy: Dict[str, Any]
    text: ParsedText | None = None
    
class ParsingAndLLMResponse(BaseModel):
    decision: str | None = None
    score: int | None = None
    reasons: str | None = None
    details: Dict[str, Any] | None = None
    link: str | None = None
    
class InterviewDTO(BaseModel):
    summary: str
    meta: str
    hard_topics: List[Dict[str, str]]
    soft_topics: List[Dict[str, str]]
