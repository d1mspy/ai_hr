from typing import List, Optional
from .skills import normalize_skills

# CEFR ранги для сравнения минимального уровня
_CEFR_RANK = {"A1":1, "A2":2, "B1":3, "B2":4, "C1":5, "C2":6}

def _rank(lvl: Optional[str]) -> int:
    return _CEFR_RANK.get((lvl or "").upper(), 0)

def hard_gate(
    must_have: List[str],                # обязательные навыки из профиля вакансии
    english_min_level: Optional[str],    # минимально требуемый уровень английского или None
    cv_text: str,                        # markdown/текст CV целиком
    cv_english_level: Optional[str],     # найденный в CV уровень английского или None
) -> List[str]:
    """
    Жёсткий фильтр:
      - проверяет покрытие must-have навыков
      - проверяет минимум по английскому, если задан
    Возвращает список причин отказа. Пустой список = гейт пройден.
    """
    reasons: List[str] = []

    # must-have покрытие
    cv_skills = normalize_skills(cv_text)
    missing = [m for m in must_have if m.lower() not in cv_skills]
    if missing:
        reasons.append("Нет must-have: " + ", ".join(missing))

    # английский: сравнение CEFR
    if english_min_level:
        if not cv_english_level or _rank(cv_english_level) < _rank(english_min_level):
            reasons.append(f"Требуется английский {english_min_level}+ (найдено: {cv_english_level or 'не указан'})")

    return reasons
