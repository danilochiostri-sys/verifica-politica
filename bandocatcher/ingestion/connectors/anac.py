import io, json, urllib.parse, urllib.request
from datetime import datetime, timezone
from gzip import GzipFile
from .base import Opportunity

CKAN_API="https://dati.anticorruzione.it/opendata/api/3/action/package_search"
SEARCH_PORTAL="https://pubblicita.anticorruzione.it/free-search"

def _get(url):
    req=urllib.request.Request(url,headers={"User-Agent":"BandoCatcher/0.1","Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=45) as r: return r.read()

def _json(url):
    return json.loads(_get(url).decode("utf-8","ignore"))

def _discover_resource():
    data=_json(CKAN_API+"?"+urllib.parse.urlencode({"q":"ocds appalti ordinari","rows":50}))
    results=((data.get("result") or {}).get("results") or [])
    candidates=[]
    for pkg in results:
        for res in pkg.get("resources") or []:
            url=res.get("url")
            name=(res.get("name") or "").lower()
            fmt=(res.get("format") or "").lower()
            if not url: continue
            if "ocds" in name and fmt in ("json","jsonl","csv"):
                candidates.append((name,url))
    return sorted(candidates,reverse=True)[0] if candidates else None

def _iter_json_lines(raw):
    if raw[:2]==b"\x1f\x8b":
        raw=GzipFile(fileobj=io.BytesIO(raw)).read()
    text=raw.decode("utf-8","ignore")
    for line in text.splitlines():
        line=line.strip()
        if not line: continue
        try: yield json.loads(line)
        except json.JSONDecodeError: continue

def _first_lang(value):
    if isinstance(value,dict):
        for k in ("it","ita","en","eng"):
            if k in value: return _first_lang(value[k])
        for v in value.values(): return _first_lang(v)
    if isinstance(value,list): return _first_lang(value[0]) if value else ""
    return str(value or "")

def fetch(limit=100):
    discovered=_discover_resource()
    if not discovered: raise RuntimeError("ANAC_OCDS_RESOURCE_NOT_FOUND")
    name,url=discovered
    raw=_get(url)
    out=[]
    today=datetime.now(timezone.utc).date().isoformat()
    for release in _iter_json_lines(raw):
        tender=release.get("tender") or {}
        status=str(tender.get("status") or "").lower()
        if status and status not in ("active","planned"): continue
        end=tender.get("tenderPeriod",{}).get("endDate")
        if end and end[:10] < today: continue
        ocid=release.get("ocid") or release.get("id")
        title=_first_lang(tender.get("title")) or "Procedura di gara"
        authority=_first_lang((release.get("buyer") or release.get("procuringEntity") or {}).get("name")) or "Stazione appaltante"
        value=(tender.get("value") or {})
        cpvs=[]
        for item in tender.get("items") or []:
            cl=item.get("classification") or {}
            if cl.get("id"): cpvs.append(str(cl["id"]))
        cig=None
        for identifier in release.get("tender",{}).get("identifiers") or []:
            if str(identifier.get("scheme","")).lower()=="cig": cig=identifier.get("id"); break
        # BDNCP exposes a direct CIG search portal, but its current query URL is
        # intentionally not guessed. Until the specific URL pattern is validated,
        # keep official_url empty and mark the record as requiring resolution.
        official=None
        if not ocid: continue
        out.append(Opportunity(
            id="anac-"+str(ocid),
            external_id=str(cig or ocid),
            type="tender",
            title=title,
            authority=authority,
            geography=["Italia"],
            status="OPEN" if status=="active" or end else "UNKNOWN",
            status_label="APERTO" if status=="active" or end else "DA VERIFICARE",
            deadline=end,
            deadline_at=end,
            deadline_precision="EXACT_DATETIME" if end and "T" in end else ("DATE_ONLY" if end else "UNKNOWN"),
            description="Procedura di procurement presente nei dati OCDS della BDNCP/ANAC.",
            beneficiaries=["Operatori economici ammessi dalla procedura"],
            requirements=([f"CIG: {cig}"] if cig else [])+([f"CPV: {', '.join(cpvs[:5])}"] if cpvs else [])+["Verificare requisiti e documentazione nel procedimento ufficiale."],
            tags=["ANAC","BDNCP","OCDS","procurement"]+cpvs[:4],
            source_id="anac-bdncp",
            source_name="ANAC — BDNCP",
            official_url=official,
            last_verified=today,
            specific_link=False
        ))
        if len(out)>=limit: break
    return out
