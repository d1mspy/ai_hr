import re
from datetime import date
from typing import Optional, List, Tuple

import re
from datetime import date
from typing import Optional, List, Tuple

# RU месяцы (полные и краткие формы)
_RU_MONTHS_FULL = {
    "январь":1, "января":1,
    "февраль":2, "февраля":2,
    "март":3, "марта":3,
    "апрель":4, "апреля":4,
    "май":5, "мая":5,
    "июнь":6, "июня":6,
    "июль":7, "июля":7,
    "август":8, "августа":8,
    "сентябрь":9, "сентября":9,
    "октябрь":10, "октября":10,
    "ноябрь":11, "ноября":11,
    "декабрь":12, "декабря":12,
}
_RU_MONTHS_ABBR = {
    "янв":1, "фев":2, "мар":3, "апр":4, "май":5, "мая":5,
    "июн":6, "июл":7, "авг":8, "сен":9, "сент":9,
    "окт":10, "ноя":11, "дек":12,
}

def _ru_month_to_num(word: str) -> Optional[int]:
    w = word.lower().rstrip(".")
    if w in _RU_MONTHS_FULL:
        return _RU_MONTHS_FULL[w]
    if w in _RU_MONTHS_ABBR:
        return _RU_MONTHS_ABBR[w]
    return None

# EN месяцы
_EN_MONTHS = {
    "jan":1, "january":1,
    "feb":2, "february":2,
    "mar":3, "march":3,
    "apr":4, "april":4,
    "may":5,
    "jun":6, "june":6,
    "jul":7, "july":7,
    "aug":8, "august":8,
    "sep":9, "sept":9, "september":9,
    "oct":10, "october":10,
    "nov":11, "november":11,
    "dec":12, "december":12,
}

def _en_month_to_num(word: str) -> Optional[int]:
    return _EN_MONTHS.get(word.lower().rstrip("."))

# ==== токены ====
# допускаем даты вида:
#  - "Сентябрь 2014" / "сентября 2014" / "сен. 2014"
#  - "Sep 2014" / "September 2014"
#  - "02.2021" / "2021-02" / "2021"
_WORD_RU = r"[А-Яа-яЁё\.]+"
_WORD_EN = r"[A-Za-z\.]+"

_DATE_TOKEN = rf"""
    (?:
        {_WORD_RU}\s+\d{{4}}        # RU месяц + год
      | {_WORD_EN}\s+\d{{4}}        # EN месяц + год
      | \d{{1,2}}[./-]\d{{4}}       # 02.2021
      | \d{{4}}[./-]\d{{1,2}}       # 2021-02
      | \d{{4}}                     # 2019
    )
"""

# тире: -, – (U+2013), — (U+2014)
_DASH = r"[-–—]"

_PRESENT = r"(?:present|now|current|по\s+наст\.?|н\.в\.|настоящее\s+время|по\s+настоящее\s+время)"

RANGE_RX = re.compile(
    rf"(?P<d1>{_DATE_TOKEN})\s*{_DASH}\s*(?P<d2>{_DATE_TOKEN}|{_PRESENT})",
    re.I | re.X | re.U
)

_YEAR_FALLBACK = re.compile(r"\b(19|20)\d{2}\b")

def _parse_date_str(s: str) -> Optional[date]:
    """Пытается распарсить единичную дату из строки (RU/EN месяц-год, разные форматы)."""
    s = s.strip()
    # RU month yyyy
    m = re.fullmatch(rf"\s*({_WORD_RU})\s+(\d{{4}})\s*", s, flags=re.I | re.U)
    if m:
        mon = _ru_month_to_num(m.group(1))
        if mon:
            return date(int(m.group(2)), mon, 1)
    # EN month yyyy
    m = re.fullmatch(rf"\s*({_WORD_EN})\s+(\d{{4}})\s*", s, flags=re.I)
    if m:
        mon = _en_month_to_num(m.group(1))
        if mon:
            return date(int(m.group(2)), mon, 1)
    # 02.2021
    m = re.fullmatch(r"\s*(\d{1,2})[./-](\d{4})\s*", s)
    if m:
        mm, yy = int(m.group(1)), int(m.group(2))
        if 1 <= mm <= 12:
            return date(yy, mm, 1)
    # 2021-02
    m = re.fullmatch(r"\s*(\d{4})[./-](\d{1,2})\s*", s)
    if m:
        yy, mm = int(m.group(1)), int(m.group(2))
        if 1 <= mm <= 12:
            return date(yy, mm, 1)
    # 2019
    m = re.fullmatch(r"\s*(\d{4})\s*", s)
    if m:
        yy = int(m.group(1))
        return date(yy, 1, 1)
    return None

def _month_diff(a: date, b: date) -> int:
    return (b.year - a.year) * 12 + (b.month - a.month)

def _merge(intervals: List[Tuple[date, date]]) -> List[Tuple[date, date]]:
    if not intervals:
        return []
    intervals.sort(key=lambda x: x[0])
    merged = [intervals[0]]
    for s, e in intervals[1:]:
        ls, le = merged[-1]
        if s <= le:
            if e > le:
                merged[-1] = (ls, e)
        else:
            merged.append((s, e))
    return merged

def estimate_total_experience(md: str) -> Optional[float]:
    """
    Сумма интервалов (в годах, с точностью до месяцев).
    Понимает: 'Сентябрь 2014 — Декабрь 2014', любые тире, RU/EN месяцы, числовые форматы, 'н.в.'/'present'.
    """
    today = date.today()
    intervals: List[Tuple[date, date]] = []

    for m in RANGE_RX.finditer(md):
        left_raw = m.group("d1")
        right_raw = m.group("d2")
        # 'present' / 'н.в.'
        if re.fullmatch(_PRESENT, right_raw.strip(), flags=re.I | re.U):
            left = _parse_date_str(left_raw)
            right = today
        else:
            # правую дату выделяем как строку и парсим общей функцией
            left = _parse_date_str(left_raw)
            right = _parse_date_str(right_raw)

        if left and right and right >= left:
            intervals.append((left, right))

    if not intervals:
        # разница между min/max годом
        years = [int(x.group(0)) for x in _YEAR_FALLBACK.finditer(md)]
        if not years:
            return None
        return max(0.0, float(max(years) - min(years)))

    merged = _merge(intervals)
    months = sum(_month_diff(s, e) + 1 for s, e in merged)
    return round(months / 12.0, 2)

# язык

EN_RX = re.compile(
    r"(english|английск\w*)[^\n]{0,60}?"
    r"(a1|a2|b1|b2|c1|c2|pre[- ]?intermediate|upper[- ]?intermediate|intermediate|elementary|advanced|fluent|native|свободн\w*)",
    re.I
)

# маппинг к CEFR
EN_LEVEL_MAP = {
    "a1": "A1", "a2": "A2", "b1": "B1", "b2": "B2", "c1": "C1", "c2": "C2",
    "elementary": "A2",
    "pre-intermediate": "A2",
    "intermediate": "B1",
    "upper-intermediate": "B2",
    "advanced": "C1",
    "fluent": "C1",
    "native": "C2",
    "свободн": "C1",  # "свободно" и т.п.
}

def detect_english_level(md: str) -> Optional[str]:
    """
    Возвращает 'A1'...'C2', если в тексте явно указан уровень английского.
    Если уровня нет/не найден — вернёт None (а не просто факт наличия английского).
    """
    best = None
    for m in EN_RX.finditer(md):
        raw = m.group(2).lower()
        # нормализуем "upper intermediate" -> "upper-intermediate"
        raw = raw.replace("upper intermediate", "upper-intermediate").replace("pre intermediate", "pre-intermediate")
        # приводим к CEFR
        lvl = EN_LEVEL_MAP.get(raw, None)
        if not lvl:
            # для кириллического "свободно" хватит префикса
            if raw.startswith("свободн"):
                lvl = "C1"
        if lvl and (_cefr_rank(lvl) > _cefr_rank(best)):
            best = lvl
    return best

def _cefr_rank(lvl: Optional[str]) -> int:
    order = {"A1":1, "A2":2, "B1":3, "B2":4, "C1":5, "C2":6}
    return order.get(lvl or "", 0)