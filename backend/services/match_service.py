from .parsing_service import ParsingService
from schemas.docs import ParsedDocsResponse, CompareResponse
from matching.matcher import decide as decide_core

class MatchService:
    def __init__(self, parsing_service: ParsingService):
        self.parsing = parsing_service

    async def compare_docs(self, cv_bytes: str, vacancy_bytes: bytes) -> dict:
        # парсим оба DOCX
        parsed: ParsedDocsResponse = await self.parsing.parse_docs(cv_bytes, vacancy_bytes)

        vac = {
            "title": parsed.vacancy.get("title") or "Vacancy",
            "description_md": parsed.vacancy.get("description_md", ""),
            "must_have": parsed.vacancy.get("must_have", []),
            "nice_to_have": parsed.vacancy.get("nice_to_have", []),
            "min_years_total": parsed.vacancy.get("min_years_total"),
            "english_min_level": parsed.vacancy.get("english_min_level"),
        }

        cv = {
            "markdown": parsed.cv.markdown,
            "detected_meta": parsed.cv.detected_meta or {},
            "sections": parsed.cv.sections,
        }

        decision = decide_core(vac, cv)
        dto = CompareResponse(decision=decision, cv=cv["markdown"], vacancy=vac)
        
        return dto
