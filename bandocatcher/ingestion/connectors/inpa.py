import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from .base import Opportunity

LIST_URL = "https://www.inpa.gov.it/bandi-e-avvisi/"
SEARCH_URL = "https://portale.inpa.gov.it/concorsi-smart/api/concorso-public-area/search-better"
DETAIL_PATH = "/bandi-e-avvisi/dettaglio-bando-avviso/?concorso_id="

class _HTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.href = None
        self.parts = []
        self.links = []
        self.all_text = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and attrs.get("href"):
            self.href = attrs["href"]; self.parts = []
        elif tag in ("br","p","div","li","h1","h2","h3"):
            self.parts.append(" ")
    def handle_data(self, data):
        text = re.sub(r"\s+", " ", data).strip()
        if not text: return
        self.all_text.append(text)
        if self.href is not None: self.parts.append(text)
    def handle_endtag(self, tag):
        if tag == "a" and self.href is not None:
            self.links.append((self.href, re.sub(r"\s+"," "," ".join(self.parts)).strip()))
            self.href = None; self.parts = []

def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent":"BandoCatcher/0.1","Accept":"text/html"})
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.read().decode("utf-8", errors="replace")

def _post_json(url, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST", headers={
        "User-Agent":"BandoCatcher/0.1",
        "Accept":"application/json",
        "Content-Type":"application/json",
    })
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.loads(r.read().decode("utf-8", errors="replace"))

def _abs(href): return urllib.parse.urljoin(LIST_URL, href)

def _detail_id(url):
    m = re.search(r"[?&]concorso_id=([a-fA-F0-9]+)", url)
    return m.group(1) if m else None

def _api_id(row):
    for key in ("concorsoId", "concorso_id", "id", "codice"):
        value = row.get(key)
        if value not in (None, ""):
            return str(value)
    return None

def _api_title(row):
    for key in ("titolo", "title", "descrizione"):
        value = row.get(key)
        if value:
            return re.sub(r"\s+", " ", str(value)).strip()
    return None

def discover(limit=50, html=None, api_payload=None):
    # inPA renders the public result set client-side. Prefer its official public
    # search API; retain HTML fixture support for backwards-compatible tests.
    if api_payload is None and html is None:
        api_payload = _post_json(SEARCH_URL, {
            "page": 0,
            "size": limit,
            "status": ["OPEN"],
        })
    if api_payload is not None:
        rows = api_payload.get("content") or api_payload.get("data") or []
        out, seen = [], set()
        for row in rows:
            if not isinstance(row, dict):
                continue
            cid = _api_id(row)
            if not cid or cid in seen:
                continue
            seen.add(cid)
            out.append({
                "external_id": cid,
                "official_url": _abs(DETAIL_PATH + urllib.parse.quote(cid, safe="")),
                "title_hint": _api_title(row) or cid,
            })
            if len(out) >= limit:
                break
        return out

    parser = _HTML(); parser.feed(html)
    out=[]; seen=set()
    for href,label in parser.links:
        url=_abs(href); cid=_detail_id(url)
        if not cid or cid in seen: continue
        seen.add(cid); out.append({"external_id":cid,"official_url":url,"title_hint":label})
        if len(out)>=limit: break
    return out

def _text(html):
    p=_HTML(); p.feed(html); return " ".join(p.all_text)

def _field(text,label,next_labels):
    stops="|".join(re.escape(x) for x in next_labels)
    m=re.search(rf"{re.escape(label)}\s*:?\s*(.*?)(?=\s+(?:{stops})\s*:|$)",text,re.I)
    return re.sub(r"\s+"," ",m.group(1)).strip() if m else None

def parse_detail(html, external_id, official_url):
    text=_text(html)
    m=re.search(r"<h1[^>]*>(.*?)</h1>",html,re.I|re.S)
    title=re.sub(r"<[^>]+>"," ",m.group(1)) if m else external_id
    title=re.sub(r"\s+"," ",title).strip()
    area=_field(text,"Area geografica",("Valutazione","Stato","Data apertura candidature"))
    status=_field(text,"Stato",("Data apertura candidature","Data chiusura candidature"))
    opening=_field(text,"Data apertura candidature",("Data chiusura candidature","Numero di posti"))
    closing=_field(text,"Data chiusura candidature",("Numero di posti","Ente di riferimento"))
    authority=_field(text,"Ente di riferimento",("Bando/Avviso e Allegati","Descrizione")) or "Ente pubblicatore"
    description=_field(text,"Descrizione",("Area geografica","Valutazione","Stato")) or ""
    normalized={"aperto":"OPEN","aperta":"OPEN","in apertura":"FORTHCOMING","chiuso":"CLOSED","chiusa":"CLOSED"}.get((status or "").strip().lower(),"UNKNOWN")
    now=datetime.now(timezone.utc).date().isoformat()
    return Opportunity(
        id=f"inpa-{external_id}", external_id=external_id, type="competition",
        title=title, authority=authority, geography=["Italia"]+([area] if area else []),
        status=normalized, status_label=(status or "DA VERIFICARE").upper(),
        deadline=closing, deadline_at=closing,
        deadline_precision="EXACT_DATETIME" if closing and re.search(r"\d{1,2}:\d{2}",closing) else ("DATE_ONLY" if closing else "UNKNOWN"),
        description=description,
        beneficiaries=["Candidati in possesso dei requisiti dell'avviso"],
        requirements=["Verificare requisiti, titoli e modalità di candidatura"],
        tags=["inPA","concorsi"], source_id="inpa", source_name="Portale inPA",
        official_url=official_url, last_verified=now, specific_link=True)

def fetch(limit=50):
    out=[]
    for item in discover(limit):
        try: out.append(parse_detail(_get(item["official_url"]),item["external_id"],item["official_url"]))
        except Exception: continue
    return out
