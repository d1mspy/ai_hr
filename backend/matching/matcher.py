from typing import Dict, Any, List
from .skills import normalize_skills
from .score import bm25_score, fuzzy_score, coverage_score
from .extract import estimate_total_experience, detect_english_level

WEIGHTS = { "bm25":0.01, "fuzzy":0.05, "must_coverage":0.10, "nice_coverage":0.10, "experience":0.85 }
INVITE_THR = 0.65
REJECT_THR  = 0.40

def decide(vac: Dict[str, Any], cv: Dict[str, Any]) -> Dict[str, Any]:
    """
    vac ожидает ключи:
      title, description_md, must_have, nice_to_have, min_years_total, english_min_level (опц.)
    cv ожидает ключи:
      markdown, (sections?, detected_meta?) - еще не реализовано
    """
    vac_text = f"{vac.get('title','')}\n{vac.get('description_md','')}"
    cv_text  = cv["text"]

    # уровень английского в CV (A1..C2 или None)
    cv_en_level = detect_english_level(cv_text)

    # similarity
    s_bm25 = bm25_score(vac_text, cv_text)
    s_fuzzy = fuzzy_score(vac_text, cv_text)

    # coverage по навыкам
    cv_skills = normalize_skills(cv_text)
    must_cov  = coverage_score(vac.get("must_have", []), cv_skills)
    nice_cov  = coverage_score(vac.get("nice_to_have", []), cv_skills)

    # опыт (годы)
    exp_years = estimate_total_experience(cv_text) or 0.0
    min_req   = vac.get("min_years_total")
    exp_ok    = 1.0 if (min_req is None or exp_years >= float(min_req)) else (exp_years / max(1.0, float(min_req)))

    details = {
        "bm25": s_bm25,
        "fuzzy": s_fuzzy,
        "must_coverage": must_cov,
        "nice_coverage": nice_cov,
        "experience": exp_ok,
    }
    score = sum(details[k] * WEIGHTS[k] for k in WEIGHTS)

    if score >= INVITE_THR:
        decision = "invite"
    elif score <= REJECT_THR:
        decision = "reject"
    else:
        decision = "manual_review"

    reasons: List[str] = []
    if must_cov < 1.0 and vac.get("must_have"):
        miss = [m for m in vac["must_have"] if m.lower() not in cv_skills]
        if miss:
            reasons.append("Не все must-have закрыты: " + ", ".join(miss))
    if min_req is not None and exp_ok < 1.0:
        reasons.append(f"Стаж {exp_years:.1f} < требуемых {float(min_req):.1f}")
    if vac.get("english_min_level"):
        reasons.append(f"English level (CV): {cv_en_level or 'не указан'}")

    return {
        "decision": decision,
        "score": round(score, 3),
        "reasons": reasons,
        "details": {k: round(v, 3) for k, v in details.items()},
    }
