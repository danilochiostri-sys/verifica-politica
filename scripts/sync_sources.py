import json,re,hashlib,urllib.request,urllib.parse,datetime,html as htmllib
from pathlib import Path
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/"data"/"sources.json"; OUT.parent.mkdir(parents=True,exist_ok=True)
UA="VerificaPoliticaBot/1.0"
def fetch(url,method="GET",body=None,timeout=45):
    h={"User-Agent":UA,"Accept":"application/json,application/xml,text/xml,text/html;q=0.9,*/*;q=0.8"}; data=None
    if body is not None: data=json.dumps(body).encode(); h["Content-Type"]="application/json"
    with urllib.request.urlopen(urllib.request.Request(url,data=data,headers=h,method=method),timeout=timeout) as r:return r.read()
def add(a,**d): d["source_kind"]="official"; a.append(d)
def normattiva():
    out=[]; base="https://api.normattiva.it/t/normattiva.api/bff-opendata/v1/api/v1"
    for term in ("DECRETO-LEGGE","LEGGE"):
      for page in range(1,4):
       try:
        o=json.loads(fetch(base+"/ricerca/semplice","POST",{"testoRicerca":term,"orderType":"recente","paginazione":{"paginaCorrente":page,"numeroElementiPerPagina":100}}))
        rows=o.get("listaAtti") or []
        if not rows: break
        for a in rows:
         title=(a.get("titoloAtto") or a.get("descrizioneAtto") or "").strip(" []"); denom=(a.get("denominazioneAtto") or term).strip()
         if term=="DECRETO-LEGGE" and "DECRETO-LEGGE" not in denom.upper(): continue
         date=a.get("dataEmanazione") or a.get("dataGU") or ""; code=a.get("codiceRedazionale") or ""
         url=f"https://www.gazzettaufficiale.it/eli/id/{a.get('dataGU')}/{code}/sg" if a.get("dataGU") and code else "https://www.normattiva.it/"
         add(out,title=title,authority="Normattiva / IPZS",document_type=denom,date=date[:10] if isinstance(date,str) else date,version="metadati ufficiali",article="",status="pubblicato",url=url,excerpt=title,reference_code=code,source_url="https://dati.normattiva.it/",keywords=re.findall(r"[a-z0-9]+",title.lower()))
       except Exception as e: print("Normattiva",term,page,e); break
    return out
def rss(url,authority,kind,limit=100):
    out=[]
    try:
      root=ET.fromstring(fetch(url))
      for i in root.findall(".//item")[:limit]:
       title=(i.findtext("title") or "").strip(); link=(i.findtext("link") or "").strip()
       desc=htmllib.unescape(re.sub("<[^>]+>"," ",i.findtext("description") or "")).strip()
       date=(i.findtext("pubDate") or i.findtext("{http://purl.org/dc/elements/1.1/}date") or "").strip()
       if title:add(out,title=title,authority=authority,document_type=kind,date=date,version="feed RSS",article="",status="pubblicato/iter",url=link,excerpt=desc[:900],reference_code="",source_url=url,keywords=re.findall(r"[a-z0-9]+",title.lower()))
    except Exception as e: print("RSS",url,e)
    return out
def camera():
    out=[]; ep="https://dati.camera.it/sparql"
    q="""PREFIX ocd:<http://dati.camera.it/ocd/> PREFIX dc:<http://purl.org/dc/elements/1.1/>
SELECT DISTINCT ?atto ?title ?date ?type ?identifier WHERE {?atto a ocd:atto; ocd:rif_leg <http://dati.camera.it/ocd/legislatura.rdf/repubblica_19>. OPTIONAL {?atto dc:title ?title.} OPTIONAL {?atto dc:date ?date.} OPTIONAL {?atto dc:type ?type.} OPTIONAL {?atto dc:identifier ?identifier.}} ORDER BY DESC(?date) LIMIT 500"""
    try:
      o=json.loads(fetch(ep+"?query="+urllib.parse.quote(q)+"&format=application%2Fsparql-results%2Bjson").decode())
      for r in o.get("results",{}).get("bindings",[]):
       b=lambda k:r.get(k,{}).get("value",""); uri=b("atto"); title=b("title")
       if uri or title:add(out,title=title or uri.rsplit("/",1)[-1],authority="Camera dei deputati",document_type=b("type") or "atto parlamentare",date=b("date"),version="Open Data OCD",article="",status="iter",url=uri.replace("http://","https://"),excerpt="",reference_code=b("identifier"),source_url="https://dati.camera.it/",keywords=re.findall(r"[a-z0-9]+",(title or "").lower()))
    except Exception as e: print("Camera",e)
    return out
def main():
    docs=normattiva()
    for u in ["https://www.senato.it/static/bgt/UltimiAtti/feedDDL.xml","https://www.senato.it/static/bgt/UltimiAtti/feedMDDL.xml","https://www.senato.it/static/bgt/UltimiAtti/feedADG.xml","https://www.senato.it/static/bgt/UltimiAtti/feedDOC.xml"]: docs+=rss(u,"Senato della Repubblica","atto parlamentare",80)
    docs+=camera()
    docs+=rss("https://www.gazzettaufficiale.it/servizi/rss","Gazzetta Ufficiale","pubblicazione ufficiale",120)
    seen=set(); clean=[]
    for d in docs:
      k=(d.get("title",""),d.get("authority",""),d.get("url",""))
      if d.get("title") and k not in seen: seen.add(k); clean.append(d)
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    for d in clean:
      basis="|".join(str(d.get(k,"") or "") for k in ("title","authority","document_type","date","version","article","status","url","excerpt","reference_code"))
      d["record_fingerprint"]=hashlib.sha256(basis.encode("utf-8")).hexdigest()[:16]
      d["retrieved_at"]=now
      d["evidence_passage"]=str(d.get("excerpt","") or "").strip()
      d["evidence_basis"]="estratto presente nel catalogo sincronizzato" if d["evidence_passage"] else "nessun estratto disponibile nel catalogo sincronizzato"
    OUT.write_text(json.dumps({"updated_at":now,"sources":[
      {"id":"normattiva","name":"Normattiva / dati.normattiva.it","type":"normativa","url":"https://dati.normattiva.it/","coverage":"Atti normativi, versioni e multivigenza","connected":True},
      {"id":"gazzetta","name":"Gazzetta Ufficiale","type":"pubblicazione","url":"https://www.gazzettaufficiale.it/","coverage":"Pubblicazione ufficiale degli atti","connected":True},
      {"id":"senato","name":"Senato della Repubblica","type":"parlamento","url":"https://dati.senato.it/","coverage":"DDL, iter, documenti e RSS","connected":True},
      {"id":"camera","name":"Camera dei deputati – Open Data","type":"parlamento","url":"https://dati.camera.it/","coverage":"Atti parlamentari e dati aperti","connected":True}], "documents":clean},ensure_ascii=False,indent=2),encoding="utf-8")
    print("Wrote",len(clean),"records")
if __name__=="__main__":main()
