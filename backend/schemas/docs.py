from pydantic import BaseModel, Field
from typing import Any, Dict, List

# спаршенный документ в md и json(sections)
# detected_meta - email и телефон
class ParsedDoc(BaseModel):
    text: str
    sections: List[Dict[str, Any]]
    detected_meta: Dict[str, Any] | None = None
    
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