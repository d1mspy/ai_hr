from typing import Dict, Any, List, Tuple, Optional
from io import BytesIO
import re
from docx import Document
from matching.skills import normalize_skills

# ключи/синонимы столбца "Наименование поля"
KEY_SYNONYMS: Dict[str, List[str]] = {
    "title": [
        r"название", r"должность", r"вакансия", r"позиция",
    ],
    "duties_md": [
        r"обязанности(?:\s*\(.*\))?", r"функциональные\s+обязанности",
    ],
    "requirements_md": [
        r"требования(?:\s*\(.*\))?", r"требования\s+к\s+кандидату",
    ],
    "experience_text": [
        r"требуемый\s+опыт\s+работы", r"опыт\s+работы", r"стаж",
    ],
    "langs_text": [
        r"знание\s+иностранных\s+языков", r"иностранные\s+языки",
    ],
    "langs_level_text": [
        r"уровень\s+владения\s+языка", r"уровень\s+языка",
    ],
}

# компилируем паттерны для поиска канона по ключу таблицы (без учёта регистра/пробелов)
COMPILED = {canon: [re.compile(pat, re.I) for pat in pats] for canon, pats in KEY_SYNONYMS.items()}

def _clean_text(s: str) -> str:
    s = (s or "").replace("\r", "\n")
    s = re.sub(r"\u00A0", " ", s)         # NBSP -> space
    s = re.sub(r"[ \t]+", " ", s)         # лишние пробелы
    s = re.sub(r"\n{2,}", "\n", s)        # множественные переносы
    return s.strip()

def _tables_to_pairs(doc: Document) -> List[Tuple[str, str]]:
    pairs: List[Tuple[str, str]] = []
    for table in doc.tables:
        for row in table.rows:
            if len(row.cells) < 2:
                continue
            k = _clean_text(row.cells[0].text).strip(" :")
            v = _clean_text(row.cells[1].text)
            if k and v:
                pairs.append((k, v))
    return pairs

def _canon_key(raw_key: str) -> Optional[str]:
    """Находит канонический ключ по содержимому первой ячейки"""
    k = raw_key.strip().lower()
    for canon, regexes in COMPILED.items():
        if any(rx.search(k) for rx in regexes):
            return canon
    return None

def _parse_min_years(text: str) -> Optional[float]:
    """Из '1-3 года'/'от 2 лет'/'3 года' -> минимальные годы как float."""
    if not text:
        return None
    t = text.lower().replace(",", ".")
    # диапазон: 1–3 года
    m = re.search(r"(\d+(?:\.\d+)?)\s*[-–—]\s*(\d+(?:\.\d+)?)\s*год", t)
    if m:
        return float(m.group(1))
    # 'от 2 лет'|'2 года'|'2 лет'
    m = re.search(r"(?:от\s*)?(\d+(?:\.\d+)?)\s*год", t)
    if m:
        return float(m.group(1))
    # 'без опыта'
    if re.search(r"без\s+опыта", t):
        return 0.0
    return None

# детектор минимального уровня английского в тексте вакансии
_EN_RX = re.compile(
    r"(english|английск\w*)[^\n]{0,60}?"
    r"(a1|a2|b1|b2|c1|c2|pre[- ]?intermediate|upper[- ]?intermediate|intermediate|elementary|advanced|fluent|native|свободн\w*)",
    re.I
)
_EN_LEVEL_MAP = {
    "a1":"A1","a2":"A2","b1":"B1","b2":"B2","c1":"C1","c2":"C2",
    "elementary":"A2","pre-intermediate":"A2","intermediate":"B1",
    "upper-intermediate":"B2","advanced":"C1","fluent":"C1","native":"C2","свободн":"C1",
}
def _norm_en_level(raw: str) -> Optional[str]:
    r = raw.lower().replace("upper intermediate","upper-intermediate").replace("pre intermediate","pre-intermediate")
    for k, v in _EN_LEVEL_MAP.items():
        if k in r:
            return v
    return None

def _extract_english_min_level(*texts: str) -> Optional[str]:
    best = None
    order = {"A1":1,"A2":2,"B1":3,"B2":4,"C1":5,"C2":6}
    for T in texts:
        for m in _EN_RX.finditer(T or ""):
            lvl = _norm_en_level(m.group(2))
            if lvl and order[lvl] > order.get(best or "", 0):
                best = lvl
    return best

def _extract_skills(requirements_md: str, duties_md: str) -> Dict[str, List[str]]:
    req = requirements_md or ""
    duties = duties_md or ""
    must = sorted(normalize_skills(req))
    nice_all = sorted(normalize_skills(duties))
    nice = [s for s in nice_all if s not in must]
    return {"must_have": must, "nice_to_have": nice}

def  parse_vacancy_docx_to_profile(docx_bytes: bytes) -> Dict[str, Any]:
    """
    Читает все таблицы DOCX вакансии (формат 'Наименование поля' / 'Значение')
    и строит профиль под мэтчер: title, description_md, must/nice, min_years_total, english_min_level.
    Работает и если названия полей отличаются — через KEY_SYNONYMS.
    """
    doc = Document(BytesIO(docx_bytes))
    pairs = _tables_to_pairs(doc)

    bag: Dict[str, str] = {}
    for raw_k, v in pairs:
        canon = _canon_key(raw_k)
        if canon:
            # если поле повторилось — дописываем с переносом
            bag[canon] = (bag.get(canon, "") + ("\n" if bag.get(canon) else "") + v).strip()

    title = bag.get("title") or "Vacancy"
    duties_md = bag.get("duties_md") or ""
    req_md = bag.get("requirements_md") or ""

    min_years_total = _parse_min_years(bag.get("experience_text", ""))
    english_min_level = _extract_english_min_level(
        bag.get("langs_text", ""), bag.get("langs_level_text", ""), req_md
    )

    skills = _extract_skills(req_md, duties_md)

    description_md = "\n\n".join(x for x in [
        f"**Обязанности**:\n{duties_md}" if duties_md else "",
        f"**Требования**:\n{req_md}" if req_md else "",
    ] if x)

    return {
        "title": title,
        "description_md": description_md,
        "must_have": skills["must_have"],
        "nice_to_have": skills["nice_to_have"],
        "min_years_total": min_years_total,
        "english_min_level": english_min_level,
    }
