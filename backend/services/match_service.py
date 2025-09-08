from .parsing_service import ParsingService
from schemas.docs import ParsedDocsResponse, CompareResponse, ParsedText
from matching.matcher import decide as decide_core

class MatchService:
    def __init__(self, parsing_service: ParsingService):
        self.parsing = parsing_service

    async def compare_docs(self, cv: bytes, vacancy: bytes) -> CompareResponse:
        # парсим оба DOCX
        parsed: ParsedDocsResponse = await self.parsing.parse_docs(cv, vacancy)


        vac = { 
            "title": parsed.vacancy.get("title") or "Vacancy",
            "description_md": parsed.vacancy.get("description_md", ""),
            "must_have": parsed.vacancy.get("must_have", []),
            "nice_to_have": parsed.vacancy.get("nice_to_have", []),
            "min_years_total": parsed.vacancy.get("min_years_total"),
            "english_min_level": parsed.vacancy.get("english_min_level"),
        }

        cv = {
            "text": parsed.cv.text,
            "detected_meta": parsed.cv.contacts or {},
        }

        decision = decide_core(vac, cv)
        decision["contacts"] = parsed.cv.contacts
        dto = CompareResponse(decision=decision, vacancy=vac)
        
        return dto

    async def docs_to_text(self, cv: bytes, vacancy: bytes) -> ParsedText:
        docs_text = await self.parsing.docs_to_text(cv, vacancy)
        return docs_text