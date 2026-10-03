import json
import urllib.request
from datetime import datetime, timedelta, timezone
from .base import Opportunity

API = "https://api.ted.europa.eu/v3/notices/search"

def _post(payload: dict) -> dict:
    req = urllib.request.Request(
        API,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json", "User-Agent": "BandoCatcher/0.1"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.loads(r.read().decode("utf-8"))

def _first(value):
    if isinstance(value, dict):
        for k in ("ita", "eng", "fra", "deu", "spa"):
            if k in value:
                return _first(value[k])
        for v in value.values():
            return _first(v)
    if isinstance(value, list):
        return _first(value[0]) if value else ""
    return str(value or "")

def _values(value):
    if isinstance(value, list):
        return [str(x) for x in value if x]
    return [str(value)] if value else []

def fetch(limit: int = 50) -> list[Opportunity]:
    start = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y%m%d")
    payload = {
        "query": f"publication-date>={start} SORT BY publication-date DESC",
        "fields": [
            "publication-number", "notice-title", "buyer-name", "buyer-country",
            "publication-date", "classification-cpv", "notice-type",
            "deadline-receipt-tender-date"
        ],
        "limit": min(limit, 100),
        "scope": "ACTIVE",
        "paginationMode": "PAGE_NUMBER",
        "page": 1,
    }
    data = _post(payload)
    now = datetime.now(timezone.utc).date().isoformat()
    out = []
    for n in data.get("notices", []):
        pub = _first(n.get("publication-number"))
        title = _first(n.get("notice-title")) or "Procurement notice"
        buyer = _first(n.get("buyer-name")) or "Amministrazione / ente"
        country = _first(n.get("buyer-country")) or "EU"
        deadline = _first(n.get("deadline-receipt-tender-date")) or None
        cpv = _values(n.get("classification-cpv"))
        official = f"https://ted.europa.eu/en/notice/-/detail/{pub}" if pub else "https://ted.europa.eu/"
        out.append(Opportunity(
            id=f"ted-{pub or abs(hash(title))}",
            external_id=pub or None,
            type="tender",
            title=title,
            authority=buyer,
            geography=["Unione Europea", country],
            status="OPEN",
            status_label="APERTO",
            deadline=deadline,
            deadline_at=deadline,
            deadline_precision="EXACT_DATETIME" if deadline and "T" in deadline else ("DATE_ONLY" if deadline else "UNKNOWN"),
            description="Avviso di procurement pubblicato su TED. Consultare sempre la scheda ufficiale e la documentazione collegata.",
            beneficiaries=["Operatori economici ammessi dalla procedura"],
            requirements=[f"CPV: {', '.join(cpv[:5])}" ] if cpv else ["Verificare requisiti e criteri nei documenti ufficiali"],
            tags=["TED", "procurement"] + cpv[:4],
            source_id="ted",
            source_name="TED — Tenders Electronic Daily",
            official_url=official,
            last_verified=now,
        ))
    return out
