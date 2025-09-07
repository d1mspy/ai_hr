import re
from functools import lru_cache
from .aliases import ALIASES

@lru_cache(maxsize=1)
def _compiled():
    pats = {}
    for canon, variants in ALIASES.items():
        pats[canon] = re.compile(r"\b(?:{})\b".format("|".join(map(re.escape, variants))), re.I)
    return pats

def normalize_skills(text: str) -> set[str]:
    pats = _compiled()
    found = set()
    for canon, rx in pats.items():
        if rx.search(text):
            found.add(canon)
    return found
