from pydantic import BaseModel, Field
from typing import Any, Dict, List

# спаршенный документ в md и json(sections)
# detected_meta - email и телефон
class ParsedDoc(BaseModel):
    markdown: str
    sections: List[Dict[str, Any]]
    detected_meta: Dict[str, Any] | None = None

# ответ в виде обоих спаршенных документов
class ParsedDocsResponse(BaseModel):
    cv: ParsedDoc
    vacancy: ParsedDoc