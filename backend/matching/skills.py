import re
from functools import lru_cache

ALIASES = {
    # dev
    "python": {"python", "py"},
    "fastapi": {"fastapi"},
    "sql": {
        "sql", "postgres", "postgresql", "oracle", "mysql", "mssql",
        "субд", "subd", "dbms", "rdbms"
    },
    "docker": {"docker"},
    "kubernetes": {"kubernetes", "k8s"},
    "airflow": {"airflow", "apache airflow"},
    "pyspark": {"pyspark", "spark", "apache spark"},
    "git": {"git", "github", "gitlab"},
    "linux": {"linux", "unix"},
    "javascript": {"javascript", "js"},
    "react": {"react", "react.js", "reactjs", "js react"},

    # ЦОД / сети / серверы
    "datacenter": {"цод", "data center", "datacenter"},
    "lan": {"lan"},
    "san": {"san"},
    "tcpip": {"tcp/ip", "tcpip"},
    "sks": {"скс", "scs", "структурированные кабельные системы"},
    "cmdb": {"cmdb"},
    "dcim": {"dcim"},
    "bios": {"bios"},
    "bmc": {"bmc", "ipmi"},
    "raid": {"raid"},
    "x86": {"x86", "х86"},  # латиница и кириллица 'х'

    # офис/документооборот
    "excel": {"excel", "ms excel", "microsoft excel"},
    "word": {"word", "ms word", "microsoft word"},
    "powerpoint": {"powerpoint", "ms powerpoint", "microsoft powerpoint", "ppt"},
    "visio": {"visio", "microsoft visio"},

    # антифрод / финтех
    "antifraud": {"антифрод", "anti-fraud", "antifraud", "fraud monitoring"},
    "aml": {"aml", "aml/cft", "под/фт", "пода/фт", "пдфт", "cft"},
    "dbo_rbs": {"дбо", "rbs", "remote banking", "интернет-банк", "интернет банк"},
    "iso8583": {"iso8583", "iso 8583"},
    "3ds": {"3ds", "3-d secure", "3d secure", "3d-secure"},
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
