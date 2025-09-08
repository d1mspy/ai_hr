from fastapi import HTTPException
import mammoth
from io import BytesIO
import tempfile, os
import docx2txt
import re
import asyncio

def docx_to_markdown(docx_bytes: bytes) -> str:
    result = mammoth.convert_to_markdown(BytesIO(docx_bytes))
    md = result.value.strip()
    return md
    
async def docx_to_txt(data: bytes) -> str:
    if not data:
        raise HTTPException(status_code=400, detail="Файл пустой")

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
    try:
        tmp.write(data)
        tmp.flush()
        tmp.close()
        text = await asyncio.to_thread(docx2txt.process, tmp.name)
        text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
        return _clean_text(text)
    finally:
        try:
            os.remove(tmp.name)
        except OSError:
            pass


def _clean_text(text: str) -> str:
  
    # нормализуем переводы строк и неразрывные пробелы
    text = text.replace('\r\n', '\n').replace('\r', '\n').replace('\u00A0', ' ')

    # email, телефоны, URLs
    text = re.sub(r'\bhttps?://\S+|www\.\S+\b', '', text)

    # номера страниц и мусор
    text = re.sub(r'(?i)Page\s+\d+\s+of\s+\d+', '', text)
    text = re.sub(r'(?i)Страница\s+\d+\s+из\s+\d+', '', text)

    # спецсимволы (оставляем буквы/цифры, пробел, таб, перевод строки и базовую пунктуацию)
    text = re.sub(r'[^\w \t\n.,!?;:()\-+@]', '', text)

    # множественные пробелы
    text = re.sub(r'[ \u00A0]{2,}', ' ', text)

    # убрать пустые строки
    text = re.sub(r'\n{2,}', '\n', text)

    return text.strip()