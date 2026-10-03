import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urljoin
from urllib.request import Request, urlopen
from .base import Opportunity

BASE="https://www.invitalia.it/"
LIST_URL=BASE+"per-le-imprese/incentivi-e-strumenti/"
DETAIL_RE=re.compile(r"/incentivi-e-strumenti/[^/?#]+/?$",re.I)

class Parser(HTMLParser):
    def __init__(self):
        super().__init__(); self.links=[]; self.text=[]
    def handle_starttag(self,tag,attrs):
        if tag=="a":
            href=dict(attrs).get("href","")
            if href: self.links.append(href)
    def handle_data(self,data): self.text.append(data)

def _get(url):
    req=Request(url,headers={"User-Agent":"BandoCatcher/0.1 (+public-source-aggregator)","Accept":"text/html"})
    with urlopen(req,timeout=30) as r: return r.read().decode("utf-8","ignore")

def _text(html):
    p=Parser(); p.feed(html); return re.sub(r"\s+"," "," ".join(p.text)).strip()

def discover():
    p=Parser(); p.feed(_get(LIST_URL))
    out=[]
    for href in p.links:
        full=urljoin(LIST_URL,href)
        path=full.split("?",1)[0].rstrip("/")+"/"
        if full.startswith(BASE) and DETAIL_RE.search(path) and path.rstrip("/")!=LIST_URL.rstrip("/"):
            out.append(full)
    return list(dict.fromkeys(out))

def parse_detail(url,html):
    text=_text(html)
    m=re.search(r"<h1[^>]*>(.*?)</h1>",html,re.I|re.S)
    title=re.sub(r"<[^>]+>"," ",m.group(1)).strip() if m else None
    if not title: return None
    sm=re.search(r"Stato incentivo o strumento\s+(Attivo|In apertura|Chiuso)",text,re.I)
    status_txt=sm.group(1).lower() if sm else "unknown"
    status_code="OPEN" if status_txt=="attivo" else ("FORTHCOMING" if "apertura" in status_txt else ("CLOSED" if "chiuso" in status_txt else "UNKNOWN"))
    close=re.search(r"Data chiusura\s+([0-9]{1,2}/[0-9]{1,2}/[0-9]{4})",text,re.I)
    opening=re.search(r"Data apertura\s+([0-9]{1,2}/[0-9]{1,2}/[0-9]{4})",text,re.I)
    intro=""
    cm=re.search(r"## COS'?[ÈE].{0,800}?([^\n]{30,300})",text,re.I)
    if cm: intro=cm.group(1).strip()
    return Opportunity(
        id="invitalia-"+url.rstrip("/").split("/")[-1],
        external_id=url.rstrip("/").split("/")[-1],
        type="grant", title=title, authority="Invitalia", geography=["Italia"],
        status=status_code,status_label={"OPEN":"APERTO","FORTHCOMING":"IN APERTURA","CLOSED":"CHIUSO","UNKNOWN":"DA VERIFICARE"}[status_code],
        deadline=close.group(1) if close else None,deadline_at=close.group(1) if close else None,
        deadline_precision="DATE_ONLY" if close else "UNKNOWN",
        description=intro or "Incentivo o strumento gestito da Invitalia. Consultare la scheda ufficiale e la documentazione collegata.",
        beneficiaries=["Verificare i soggetti destinatari nella scheda ufficiale"],
        requirements=["Verificare requisiti, spese ammissibili e modalità di domanda nella scheda ufficiale."],
        tags=["Invitalia","incentivo"],
        source_id="invitalia",source_name="Invitalia",official_url=url,last_verified=datetime.now(timezone.utc).date().isoformat(),specific_link=True)
def fetch(limit=40):
    out=[]
    for url in discover():
        try:
            o=parse_detail(url,_get(url))
            if o: out.append(o)
        except Exception:
            continue
        if len(out)>=limit: break
    return out
