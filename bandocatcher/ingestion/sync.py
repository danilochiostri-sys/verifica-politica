import json,sys
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from ingestion.connectors.ted import fetch as fetch_ted
from ingestion.connectors.funding_tenders import fetch as fetch_ft
from ingestion.connectors.inpa import fetch as fetch_inpa
from ingestion.connectors.invitalia import fetch as fetch_invitalia
from ingestion.connectors.anac import fetch as fetch_anac

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"data"/"opportunities.js"
META=ROOT/"data"/"sync-status.json"

def dedupe(items):
    seen={}
    for x in items:
        key=x.external_id or (x.title.strip().lower(),x.authority.strip().lower())
        if key not in seen: seen[key]=x
    return list(seen.values())

def run():
    errors=[]; items=[]; attempted=[]
    for name,fn in (("ted",fetch_ted),("funding-tenders",fetch_ft),("inpa",fetch_inpa),("invitalia",fetch_invitalia),("anac-bdncp",fetch_anac)):
        attempted.append(name)
        try: items.extend(fn())
        except Exception as e: errors.append({"source":name,"error":str(e)})
    items=dedupe(items)
    # Public UI invariant: never publish an opportunity as clickable official
    # unless a specific source URL exists.
    published=[x for x in items if x.specific_link and x.official_url]
    now=datetime.now(timezone.utc).isoformat()
    if published:
        OUT.write_text("window.BC_OPPORTUNITIES="+json.dumps([x.to_dict() for x in published],ensure_ascii=False,separators=(",",":"))+";\n",encoding="utf-8")
    META.write_text(json.dumps({
        "updated_at":now,
        "sources":attempted,
        "items_seen":len(items),
        "items_published":len(published),
        "unresolved_specific_links":len(items)-len(published),
        "errors":errors,
        "mode":"live" if published else "demo"
    },ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"items_seen":len(items),"items_published":len(published),"unresolved_specific_links":len(items)-len(published),"errors":errors},ensure_ascii=False))

if __name__=="__main__": run()
