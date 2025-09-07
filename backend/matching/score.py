from rank_bm25 import BM25Okapi
from rapidfuzz import fuzz
from .skills import normalize_skills

def bm25_score(vac_text: str, res_text: str) -> float:
    docs = [vac_text.lower().split()]
    bm25 = BM25Okapi(docs)
    s = bm25.get_scores(res_text.lower().split())[0]
    return float(min(1.0, s / 5.0))

def fuzzy_score(vac_text: str, res_text: str) -> float:
    return fuzz.token_set_ratio(vac_text, res_text) / 100.0

def coverage_score(req: list[str], res_skills: set[str]) -> float:
    if not req:
        return 1.0
    got = sum(1 for x in req if x.lower() in res_skills)
    return got / len(req)
