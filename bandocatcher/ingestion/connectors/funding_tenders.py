import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from .base import Opportunity

API = "https://api.tech.ec.europa.eu/search-api/prod/rest/search"

def _post(form: dict) -> dict:
    body = urllib.parse.urlencode(form).encode("utf-8")
    req = urllib.request.Request(
        API + "?apiKey=SEDIA&text=***",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json", "User-Agent": "BandoCatcher/0.1"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.loads(r.read().decode("utf-8"))

def _first(value):
    if isinstance(value, dict):
        for key in ("en", "eng", "it", "ita"):
            if key in value:
                return _first(value[key])
        for v in value.values():
            return _first(v)
    if isinstance(value, list):
        return _first(value[0]) if value else ""
    return str(value or "")

def fetch(limit: int = 50) -> list[Opportunity]:
    query = {"bool":{"must":[{"terms":{"type":["0","1","2","8"]}},{"terms":{"status":["31094501","31094502","31094503"]}}]}}
    form = {
        "pageSize": str(min(limit, 50)),
        "pageNumber": "1",
        "sort": json.dumps({"order":"DESC","field":"startDate"}),
        "query": json.dumps(query, separators=(",",":")),
        "languages": json.dumps(["en"]),
        "displayFields": json.dumps([
            "type","identifier","reference","title","status","caName",
            "startDate","deadlineDate","deadlineModel","frameworkProgramme",
            "typesOfAction","callIdentifier"
        ]),
    }
    data = _post(form)
    docs = data.get("results") or data.get("items") or data.get("documents") or []
    now = datetime.now(timezone.utc).date().isoformat()
    out = []
    for d in docs:
        identifier = _first(d.get("identifier") or d.get("callIdentifier") or d.get("reference"))
        if not identifier:
            continue
        title = _first(d.get("title")) or identifier
        deadline = _first(d.get("deadlineDate")) or None
        authority = _first(d.get("caName")) or "Commissione europea"
        status_code = _first(d.get("status"))
        status = "OPEN" if status_code == "31094501" else ("FORTHCOMING" if status_code == "31094503" else "CLOSED")
        label = {"OPEN":"APERTO","FORTHCOMING":"IN APERTURA","CLOSED":"CHIUSO"}[status]
        official = "https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details/" + urllib.parse.quote(identifier, safe="-_.")
        out.append(Opportunity(
            id=f"eu-{identifier}",
            external_id=identifier,
            type="grant",
            title=title,
            authority=authority,
            geography=["Unione Europea"],
            status=status,
            status_label=label,
            deadline=deadline,
            deadline_at=deadline,
            deadline_precision="DATE_ONLY" if deadline and "T" not in deadline else ("EXACT_DATETIME" if deadline else "UNKNOWN"),
            description="Opportunità reperita tramite il portale ufficiale Funding & Tenders della Commissione europea.",
            beneficiaries=["Soggetti eleggibili secondo il topic/call ufficiale"],
            requirements=["Verificare topic, eligibility, work programme e documenti ufficiali"],
            tags=["EU", "Funding & Tenders", "grant"],
            source_id="funding-tenders",
            source_name="Funding & Tenders Portal",
            official_url=official,
            last_verified=now,
        ))
    return out
