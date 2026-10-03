import json, sys
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ingestion.connectors.ted import fetch as fetch_ted
from ingestion.connectors.funding_tenders import fetch as fetch_ft

DEMO = ROOT / "data" / "opportunities.js"
META = ROOT / "data" / "sync-status.json"

def dedupe(items):
    seen = {}
    for item in items:
        key = (item.external_id or "", item.title.strip().lower(), item.authority.strip().lower())
        if key not in seen:
            seen[key] = item
    return list(seen.values())

def main():
    errors = []
    items = []
    for name, fn in (("ted", fetch_ted), ("funding-tenders", fetch_ft)):
        try:
            items.extend(fn())
        except Exception as exc:
            errors.append({"source": name, "error": str(exc)})

    items = dedupe(items)
    now = datetime.now(timezone.utc).isoformat()
    payload = "window.BC_OPPORTUNITIES=" + json.dumps([x.to_dict() for x in items], ensure_ascii=False, separators=(",",":")) + ";\n"
    if items:
        DEMO.write_text(payload, encoding="utf-8")

    META.write_text(json.dumps({
        "updated_at": now,
        "sources_attempted": ["ted", "funding-tenders"],
        "items": len(items),
        "errors": errors,
        "mode": "live" if items else "demo"
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({"items": len(items), "errors": errors, "mode": "live" if items else "demo"}, ensure_ascii=False))

if __name__ == "__main__":
    main()
