import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ingestion.connectors.base import Opportunity
from ingestion.connectors.ted import build_official_url as ted_url, fetch as ted_fetch
from ingestion.connectors.funding_tenders import build_official_url as ft_url, fetch as ft_fetch
from ingestion.sync import is_publishable


def test_base_defaults_to_fail_closed():
    o = Opportunity(
        id="x",
        type="tender",
        title="T",
        authority="A",
        geography=["EU"],
        status="OPEN",
        status_label="APERTO",
        deadline=None,
        deadline_at=None,
        deadline_precision="UNKNOWN",
        description="D",
        beneficiaries=[],
        requirements=[],
        tags=[],
        source_id="x",
        source_name="X",
        official_url="https://example.invalid/home",
        last_verified="2026-10-03",
    )
    assert o.specific_link is False
    assert is_publishable(o) is False


def test_ted_specific_link_requires_publication_number():
    url, specific = ted_url("123456-2026")
    assert url == "https://ted.europa.eu/en/notice/-/detail/123456-2026"
    assert specific is True

    url, specific = ted_url(None)
    assert url is None
    assert specific is False


def test_funding_tenders_uses_current_topic_details_path():
    url, specific = ft_url("HORIZON-CL3-2026-01-INFRA-03")
    assert url == (
        "https://ec.europa.eu/info/funding-tenders/opportunities/portal/"
        "screen/opportunities/topic-details/HORIZON-CL3-2026-01-INFRA-03"
    )
    assert "/topic-details-tr/" not in url
    assert specific is True


def test_ted_fetch_marks_missing_publication_as_not_publishable(monkeypatch):
    monkeypatch.setattr(
        "ingestion.connectors.ted._post",
        lambda payload: {
            "notices": [
                {
                    "notice-title": {"eng": "Notice without id"},
                    "buyer-name": {"eng": "Buyer"},
                    "buyer-country": "IT",
                }
            ]
        },
    )
    item = ted_fetch(limit=1)[0]
    assert item.official_url is None
    assert item.specific_link is False
    assert is_publishable(item) is False


def test_funding_tenders_fetch_marks_identifier_as_specific(monkeypatch):
    monkeypatch.setattr(
        "ingestion.connectors.funding_tenders._post",
        lambda form: {
            "results": [
                {
                    "identifier": "HORIZON-TEST-2026-01",
                    "title": {"en": "Test topic"},
                    "status": "31094501",
                    "caName": {"en": "European Commission"},
                    "deadlineDate": "31/12/2026",
                }
            ]
        },
    )
    item = ft_fetch(limit=1)[0]
    assert item.specific_link is True
    assert item.official_url.endswith("/topic-details/HORIZON-TEST-2026-01")
    assert is_publishable(item) is True
