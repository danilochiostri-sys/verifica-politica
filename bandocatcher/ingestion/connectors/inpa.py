import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urljoin
from urllib.request import Request, urlopen
from .base import Opportunity

BASE="https://www.inpa.gov.it/"
LIST_URL=BASE+"bandi-e-avvisi/"
DETAIL_RE=re.compile(r"/bandi-e-avvisi/dettaglio-bando-avviso/\?concorso_id=[A-Za-z0-9]+", re.I)

class Parser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links=[]
        self.text=[]
    def handle_starttag(self,tag,attrs):
        if tag=="a":
            href=dict(attrs).get("href","")
            if href: self.links.append(href)
    def handle_data(self,data):
        self.text.append(data)

def _get(url):
    req=Request(url,headers={"User-Agent":"BandoCatcher/0.1 (+public-source-aggregator)"})
    with urlopen(req,timeout=30) as r:
        return r.read().decode("utf-8","ignore")

def _text(html):
    p=Parser(); p.feed(html)
    return re.sub(r"\s+"," "," ".join(p.text)).strip()

def _field(text,label,next_labels):
    pattern=re.escape(label)+r"\s*([^\n]+?)\s+(?="+ "|".join(re.escape(x) for x in next_labels)+r"|$)"
    m=re.search(pattern,text,re.I)
    return m.group(1).strip() if m else None

def discover(max_pages=5):
    urls=[]
    for n in range(1,max_pages+1):
        url=LIST_URL if n==1 else urljoin(BASE,f"page/{n}/")
        try: html=_get(url)
        except Exception: continue
        for href in ParserLinks(html):
            full=urljoin(url,href)
            if DETAIL_RE.search(full): urls.append(full)
    return list(dict.fromkeys(urls))

def ParserLinks(html):
    p=Parser(); p.feed(html); return p.links

def parse_detail(url,html):
    p=Parser(); p.feed(html); text=_text(html)
    title=None
    m=re.search(r"<h1[^>]*>(.*?)</h1>",html,re.I|re.S)
    if m: title=re.sub(r"<[^>]+>"," ",m.group(1)).strip()
    if not title: 
        mt=re.match(r"(.*?)Descrizione:",text,re.I)
        title=mt.group(1).strip(" -") if mt else None
    if not title or "dettaglio-bando-avviso" not in url: return None
    status=_field(text,"Stato:",["Data apertura candidature:","Numero di posti:"]) or "UNKNOWN"
    opening=_field(text,"Data apertura candidature:",["Data chiusura candidature:","Numero di posti:"])
    closing=_field(text,"Data chiusura candidature:",["Numero di posti:","Ente di riferimento:"])
    geo=_field(text,"Area geografica:",["Valutazione:","Stato:"]) or "Nazionale"
    authority=_field(text,"Ente di riferimento:",["Link al sito della PA:","Bando/Avviso e Allegati:"]) or "Amministrazione pubblica"
    posts=_field(text,"Numero di posti:",["Ente di riferimento:","Bando/Avviso e Allegati:"])
    status_u=status.lower()
    status_code="OPEN" if "aperto" in status_u else ("CLOSED" if "chiuso" in status_u else "UNKNOWN")
    return Opportunity(
        id="inpa-"+url.split("concorso_id=")[-1],
        external_id=url.split("concorso_id=")[-1],
        type="competition", title=title, authority=authority,
        geography=["Italia",geo], status=status_code,
        status_label={"OPEN":"APERTO","CLOSED":"CHIUSO","UNKNOWN":"DA VERIFICARE"}[status_code],
        deadline=closing, deadline_at=closing, deadline_precision="EXACT_DATETIME" if closing else "UNKNOWN",
        description="Opportunità pubblicata sul Portale inPA. Consultare la pagina ufficiale e gli allegati.",
        beneficiaries=["Candidati in possesso dei requisiti dell'avviso"],
        requirements=([f"Numero di posti: {posts}"] if posts else [])+["Verificare titolo di studio, requisiti e modalità di candidatura nel testo ufficiale."],
        tags=["inPA","concorso",geo],
        source_id="inpa",source_name="Portale inPA",official_url=url,last_verified=datetime.now(timezone.utc).date().isoformat(),specific_link=True)
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
