from typing import List, Dict, Any
import mammoth
from docx import Document
from io import BytesIO

HEADING_STYLES = {"Heading 1", "Heading 2", "Heading 3", "Заголовок 1", "Заголовок 2", "Заголовок 3"}

def docx_to_markdown(docx_bytes: bytes) -> str:
    result = mammoth.convert_to_markdown(BytesIO(docx_bytes))
    md = result.value.strip()
    return md

def docx_to_struct(docx_bytes: bytes) -> Dict[str, Any]:
    # парсим структуру документа
    doc = Document(BytesIO(docx_bytes))
    
    # будущий JSON
    sections: List[Dict[str, Any]] = []
    # текущая секция
    current = {"heading": None, "content": "", "list_items": [], "tables": []}
    
    # сброс текущего блока текста в список секций 
    def flush_current():
        nonlocal current
        if current["heading"] or current["content"] or current["list_items"] or current["tables"]:
            current["content"] = current["content"].strip()
            sections.append(current)
        current = {"heading": None, "content": "", "list_items": [], "tables": []}

    # проход по документу
    for block in doc.element.body.iterchildren():
        tag = block.tag
        # абзацы
        if tag.endswith("p"):
            p = block
            texts = [r.text for r in p.iter() if hasattr(r, "text") and r.text]
            text = " ".join(t.strip() for t in texts if t and t.strip())
            if not text:
                continue
                
            # проверка на начало новой секции
            is_heading = False
            pPr = p.find("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}pPr")
            if pPr is not None:
                pStyle = pPr.find("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}pStyle")
                if pStyle is not None and pStyle.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val"):
                    style_val = pStyle.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val")
                    if style_val in HEADING_STYLES or style_val.lower().startswith("heading"):
                        is_heading = True

            # списки (через numbering properties)
            numPr = pPr.find("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}numPr") if pPr is not None else None
            if is_heading:
                flush_current()
                current["heading"] = text
            elif numPr is not None:
                current["list_items"].append(text)
            else:
                if current["content"]:
                    current["content"] += "\n" + text
                else:
                    current["content"] = text
        
        # вытяжка таблицы в список строк/столбцов
        elif tag.endswith("tbl"):
            rows = []
            for tr in block.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tr"):
                cells = []
                for tc in tr.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tc"):
                    cell_texts = [r.text for r in tc.iter() if hasattr(r, "text") and r.text]
                    cells.append(" ".join(t.strip() for t in cell_texts if t and t.strip()))
                if any(cells):
                    rows.append(cells)
            if rows:
                current["tables"].append(rows)

    flush_current()
    
    # простая метадата (email/phone)
    full_text = "\n".join(
        [sec["heading"] or "" for sec in sections] +
        [sec["content"] for sec in sections if sec["content"]] +
        sum([sec["list_items"] for sec in sections], [])
    )
    import re
    emails = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", full_text)
    phones = re.findall(r"(?:\+?\d[\s\-()]*){7,}", full_text)

    return {
        "sections": sections,
        "detected_meta": {
            "emails": list(set(emails))[:5],
            "phones": list(set(phones))[:5]
        }
    }