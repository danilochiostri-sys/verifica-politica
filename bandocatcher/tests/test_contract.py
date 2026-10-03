import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ingestion.connectors.base import Opportunity

def test_opportunity_requires_specific_link_flag():
    o = Opportunity(
        id="x", external_id="00176184-2026", type="tender", title="T",
        authority="A", geography=["EU"], status="OPEN", status_label="APERTO",
        deadline=None, deadline_at=None, deadline_precision="UNKNOWN",
        description="D", beneficiaries=[], requirements=[], tags=["TED"],
        source_id="ted", source_name="TED", official_url="https://ted.europa.eu/en/notice/-/detail/00176184-2026",
        last_verified="2026-10-03", specific_link=True)
    assert "/notice/-/detail/00176184-2026" in o.official_url
    assert o.specific_link is True
