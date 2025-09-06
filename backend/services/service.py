from repositories.db.repository import Repository
from utils.docx_extract import docx_to_markdown, docx_to_struct
from schemas.docs import ParsedDoc, ParsedDocsResponse
from fastapi import HTTPException, status
import anyio

class Service():
    def __init__(self, repository: Repository):
        self.repository = repository
    
    async def compare_docs(self, cv: bytes, vacancy: bytes) -> ParsedDocsResponse:
        try:
            cv_md, cv_struct = await _parse_pair(cv)
            vac_md, vac_struct = await _parse_pair(vacancy)
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Не удалось прочитать файл резюме (.docx может быть повреждён)")
        
        return ParsedDocsResponse(
            cv=ParsedDoc(
                markdown=cv_md,
                sections=cv_struct["sections"],
                detected_meta=cv_struct.get("detected_meta"),
            ),
            vacancy=ParsedDoc(
                markdown=vac_md,
                sections=vac_struct["sections"],
                detected_meta=vac_struct.get("detected_meta"),
            )
        )

# парсинг документа в два формата 
async def _parse_pair(doc_bytes: bytes):
    md = await anyio.to_thread.run_sync(docx_to_markdown, doc_bytes)
    struct = await anyio.to_thread.run_sync(docx_to_struct, doc_bytes)
    return md, struct
