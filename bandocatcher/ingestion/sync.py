import json
import sys
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
        key = item.external_id or (item.title.strip().lower(), item.authority.strip().lower())
        if key not in seen:
            seen[key] = item
    return list(seen.values())

def is_publishable(item):
    official_url = (item.official_url or "").strip()
    return bool(item.specific_link and official_url)

def main():
    errors = []
    items = []
    attempted = []

    for name, fn in (("ted", fetch_ted), ("funding-tenders", fetch_ft)):
        attempted.append(name)
        try:
            items.extend(fn())
        except Exception as exc:
            errors.append({"source": name, "error": str(exc)})

    items = dedupe(items)
    published = [item for item in items if is_publishable(item)]
    unresolved = len(items) - len(published)
    now = datetime.now(timezone.utc).isoformat()

    if published:
        payload = (
            "window.BC_OPPORTUNITIES="
            + json.dumps(
                [item.to_dict() for item in published],
                ensure_ascii=False,
                separators=(",", ":"),
            )
            + ";\n"
        )
        DEMO.write_text(payload, encoding="utf-8")

    META.write_text(
        json.dumps(
            {
                "updated_at": now,
                "sources_attempted": attempted,
                "items_seen": len(items),
                "items_published": len(published),
                "unresolved_specific_links": unresolved,
                "errors": errors,
                "mode": "live" if published else "demo",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "items_seen": len(items),
                "items_published": len(published),
                "unresolved_specific_links": unresolved,
                "errors": errors,
            },
            ensure_ascii=False,
        )
    )

if __name__ == "__main__":
    main()
