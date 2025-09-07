import re
from functools import lru_cache

ALIASES = {
    "python": {"python", "py"},
    "fastapi": {"fastapi"},
    "sql": {"sql", "postgres", "postgresql", "oracle", "mysql", "mssql"},
    "docker": {"docker"},
    "kubernetes": {"kubernetes", "k8s"},
    "airflow": {"airflow", "apache airflow"},
    "pyspark": {"pyspark", "spark", "apache spark"},
    "git": {"git", "github", "gitlab"},
    "linux": {"linux", "unix"},
    "javascript": {"javascript", "js"},
    "react": {"react", "react.js", "reactjs", "js react"},
}

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
