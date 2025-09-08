from repositories.db.repository import Repository
from utils.docx_extract import docx_to_txt
from utils.vacancy_extract import parse_vacancy_docx_to_profile
from utils.contacts_extract import extract_contacts
from schemas.docs import ParsedDoc, ParsedDocsResponse, ParsedText
from fastapi import HTTPException, status
import asyncio

class ParsingService():
    def __init__(self, repository: Repository):
        self.repository = repository
    
    async def parse_docs(self, cv: bytes, vacancy: bytes) -> ParsedDocsResponse:
        try:
            cv_text = await docx_to_txt(cv)
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Не удалось прочитать файл резюме (.docx может быть повреждён)")
        
        contacts = extract_contacts(cv_text)
        
        vac = parse_vacancy_docx_to_profile(vacancy)
        
        return ParsedDocsResponse(
            cv=ParsedDoc(
                text=cv_text,
                contacts=contacts,
            ),
            vacancy=vac
        )
        
    async def docs_to_text(self, cv: bytes, vac: bytes) -> ParsedText:
        cv_text, vac_text = await asyncio.gather(
            docx_to_txt(cv),
            docx_to_txt(vac),
        )
        return ParsedText(cv_text=cv_text, vac_text=vac_text)