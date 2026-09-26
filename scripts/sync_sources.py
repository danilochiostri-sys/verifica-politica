import json, re, urllib.request, urllib.parse, datetime, html as htmllib
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"data"/"sources.json"
OUT.parent.mkdir(parents=True, exist_ok=True)
UA="VerificaPolitica-MVP/1.0 (+https://github.com/danilochiostri-sys/verifica-politica)"

def fetch(url, method="GET", body=None, headers=None, timeout=30):
    hs={"User-Agent":UA,"Accept":"application/json, text/xml, application/xml, text/html;q=0.9,*/*;q=0.8"}
    if headers: hs.update(headers)
    data=None
    if body is not None:
        data=json.dumps(body).encode()
        hs["Content-Type"]="application/json"
    req=urllib.request.Request(url,data=data,headers=hs,method=method)
    with urllib.request.urlopen(req,timeout=timeout) as r:
        return r.read(), r.headers.get("content-type","")

def add(items, **kw):
    items.append({"source_kind":"official", **kw})

def normattiva():
    base="https://api.normattiva.it/t/normattiva.api/bff-opendata/v1/api/v1"
    items=[]
    for term in ["DECRETO-LEGGE","LEGGE"]:
        try:
            raw,_=fetch(base+"/ricerca/semplice","POST",{
                "testoRicerca":term,"orderType":"recente",
                "paginazione":{"paginaCorrente":1,"numeroElementiPerPagina":100}
            })
            obj=json.loads(raw.decode("utf-8"))
            for a in obj.get("listaAtti",[]):
                denom=(a.get("denominazioneAtto") or "").upper()
                if term=="DECRETO-LEGGE" and "DECRETO-LEGGE" not in denom: continue
                title=(a.get("descrizioneAtto") or a.get("titoloAtto") or "").strip(" []")
                date=a.get("dataEmanazione") or a.get("dataGU")
                code=a.get("codiceRedazionale")
                url=""
                if a.get("dataGU") and code:
                    url=f"https://www.gazzettaufficiale.it/eli/id/{a['dataGU']}/{code}/sg"
                add(items,title=title,authority="Normattiva / IPZS",date=date[:10] if isinstance(date,str) else date,
                    document_type=denom or term,article="",version="metadati ufficiali",status="pubblicato",
                    url=url or "https://www.normattiva.it/",excerpt=a.get("titoloAtto") or "",
                    reference_code=code or "",source_url="https://dati.normattiva.it/")
        except Exception as e:
            print("Normattiva:",e)
    return items

def senato():
    page="https://dati.senato.it/sito/feed_rss?testo_generico=9"
    out=[]
    try:
        raw,_=fetch(page)
        text=raw.decode("utf-8","ignore")
        links=re.findall(r'href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',text,re.I|re.S)
        urls=[]
        for href,label in links:
            label=re.sub("<[^>]+>"," ",label)
            if any(k in label.lower() for k in ["disegni di legge","messaggi di approvazione","atti del governo","documenti non legislativi","tutti gli atti"]):
                urls.append(urllib.parse.urljoin(page,href))
        for url in urls[:8]:
            try:
                raw,_=fetch(url); root=ET.fromstring(raw)
                for item in root.findall(".//item")[:30]:
                    title=(item.findtext("title") or "").strip()
                    link=(item.findtext("link") or "").strip()
                    desc=htmllib.unescape(re.sub("<[^>]+>"," ",item.findtext("description") or "")).strip()
                    date=(item.findtext("pubDate") or "").strip()
                    if title:
                        add(out,title=title,authority="Senato della Repubblica",date=date,document_type="atto parlamentare",
                            article="",version="dato RSS",status="pubblicato/iter",url=link or "https://www.senato.it/",
                            excerpt=desc[:600],reference_code="",source_url="https://dati.senato.it/sito/feed_rss?testo_generico=9")
            except Exception as e:
                print("Senato feed:",url,e)
    except Exception as e:
        print("Senato:",e)
    return out

def camera():
    out=[]
    endpoint="https://dati.camera.it/sparql"
    query="""PREFIX ocd:<http://dati.camera.it/ocd/>
PREFIX dc:<http://purl.org/dc/elements/1.1/>
PREFIX rdfs:<http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?atto ?title ?date WHERE {
 ?atto a ocd:atto; ocd:rif_leg <http://dati.camera.it/ocd/legislatura.rdf/repubblica_19>.
 OPTIONAL {?atto dc:title ?title.}
 OPTIONAL {?atto dc:date ?date.}
} LIMIT 200"""
    try:
        url=endpoint+"?query="+urllib.parse.quote(query)+"&format=application%2Fsparql-results%2Bjson"
        raw,_=fetch(url)
        obj=json.loads(raw.decode())
        for row in obj.get("results",{}).get("bindings",[]):
            title=row.get("title",{}).get("value","").strip()
            uri=row.get("atto",{}).get("value","")
            date=row.get("date",{}).get("value","")
            if title or uri:
                add(out,title=title or uri.rsplit("/",1)[-1],authority="Camera dei deputati",date=date,
                    document_type="atto parlamentare",article="",version="Open Data OCD",status="iter",
                    url=uri.replace("http://","https://") if uri else "https://www.camera.it/",
                    excerpt="",reference_code="",source_url="https://dati.camera.it/")
    except Exception as e:
        print("Camera:",e)
    return out

def rss_from_page(source_name, page_url, authority, kind):
    out=[]
    try:
        raw,_=fetch(page_url)
        text=raw.decode("utf-8","ignore")
        hrefs=re.findall(r'(?:href|src)=["\']([^"\']+)["\']',text,re.I)
        candidates=[]
        for href in hrefs:
            u=urllib.parse.urljoin(page_url,href)
            low=u.lower()
            if low.endswith((".xml",".rss")) or "rss" in low:
                candidates.append(u)
        for u in dict.fromkeys(candidates)[:6]:
            try:
                raw,_=fetch(u); root=ET.fromstring(raw)
                found=False
                for item in root.findall(".//item")[:20]:
                    found=True
                    title=(item.findtext("title") or "").strip()
                    link=(item.findtext("link") or "").strip()
                    desc=re.sub(r"<[^>]+>"," ",item.findtext("description") or "").strip()
                    date=(item.findtext("pubDate") or item.findtext("{http://purl.org/dc/elements/1.1/}date") or "").strip()
                    if title: add(out,title=title,authority=authority,date=date,document_type=kind,article="",version="dato RSS",status="pubblicato",url=link or page_url,excerpt=htmllib.unescape(desc)[:600],reference_code="",source_url=page_url)
                if found: break
            except Exception as e: print("RSS:",u,e)
    except Exception as e: print("RSS page:",page_url,e)
    return out

def gazzetta():
    out=[]
    # Official Gazette offers RSS for its series; try the current-series endpoints used by the site.
    candidates=[
        "https://www.gazzettaufficiale.it/rss/serie_generale",
        "https://www.gazzettaufficiale.it/servizi/rss",
        "https://www.gazzettaufficiale.it/atto/serie_generale/caricaRss"
    ]
    for u in candidates:
        try:
            raw,_=fetch(u)
            root=ET.fromstring(raw)
            for item in root.findall(".//item")[:100]:
                title=(item.findtext("title") or "").strip(); link=(item.findtext("link") or "").strip()
                desc=re.sub("<[^>]+>"," ",item.findtext("description") or "").strip()
                date=(item.findtext("pubDate") or "").strip()
                if title: add(out,title=title,authority="Gazzetta Ufficiale",date=date,document_type="atto pubblicato in Serie Generale",article="",version="pubblicazione originaria",status="pubblicato",url=link or "https://www.gazzettaufficiale.it/",excerpt=htmllib.unescape(desc)[:600],reference_code="",source_url="https://www.gazzettaufficiale.it/")
            if out: break
        except Exception as e: print("Gazzetta:",u,e)
    return out

def main():
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    docs=[]
    docs += normattiva()
    docs += senato()
    docs += camera()
    docs += gazzetta()
    # Ministry / government official feeds: discover RSS where the institution exposes it.
    ministry_pages=[
      ("Ministero delle Imprese e del Made in Italy","https://www.mimit.gov.it/it/rss"),
      ("Ministero della Salute","https://www.salute.gov.it/new/it/altro/rss/"),
      ("Dipartimento della Protezione Civile","https://www.protezionecivile.gov.it/it/rss/")
    ]
    for name,page in ministry_pages:
        docs += rss_from_page(name,page,name,"documento/comunicazione istituzionale")
    # De-duplicate
    seen=set(); clean=[]
    for d in docs:
        key=(d.get("title"),d.get("authority"),d.get("url"))
        if key in seen: continue
        seen.add(key); clean.append(d)
    result={"updated_at":now,"sources":[
      {"id":"normattiva","name":"Normattiva / dati.normattiva.it","type":"normativa","url":"https://dati.normattiva.it/","coverage":"atti normativi, versioni e multivigenza","connected":True},
      {"id":"senato","name":"Dati Senato","type":"parlamento","url":"https://dati.senato.it/sito/scarica_i_dati","coverage":"DDL, iter, documenti, RSS","connected":True},
      {"id":"camera","name":"Open Data Camera","type":"parlamento","url":"https://dati.camera.it/","coverage":"atti parlamentari e linked open data","connected":True},
      {"id":"gazzetta","name":"Gazzetta Ufficiale","type":"pubblicazione","url":"https://www.gazzettaufficiale.it/","coverage":"pubblicazione ufficiale degli atti","connected":True},
      {"id":"ministeri","name":"Siti e feed dei Ministeri","type":"governo","url":"https://www.gov.it/","coverage":"comunicazioni e documenti disponibili tramite feed ufficiali","connected":True}
    ],"documents":clean}
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print("Wrote",len(clean),"records to",OUT)

if __name__=="__main__": main()
