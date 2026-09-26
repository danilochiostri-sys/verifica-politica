import json
from pathlib import Path
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"data"/"sources.json"
CURATED=ROOT/"data"/"curated.json"
OUT=ROOT/"data"/"catalog.js"

def load(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

source=load(SOURCE, {})
cur=load(CURATED, {})
docs=(source.get("documents") or []) + (cur.get("records") or [])
seen=set(); unique=[]
for d in docs:
    key=(d.get("title","").strip(), d.get("authority","").strip(), d.get("reference_code","").strip())
    if key in seen:
        continue
    seen.add(key)
    unique.append(d)

payload={
    "updated_at": source.get("updated_at") or datetime.now(timezone.utc).isoformat(),
    "sources": source.get("sources") or cur.get("sources") or [],
    "documents": unique
}
OUT.write_text("window.VP_CATALOG="+json.dumps(payload,ensure_ascii=False,separators=(",",":"))+";\n",encoding="utf-8")
print("catalog documents:", len(unique))
