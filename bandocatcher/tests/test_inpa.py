from ingestion.connectors.inpa import discover, parse_detail

LIST = """
<html><body>
<a href="/bandi-e-avvisi/dettaglio-bando-avviso/?concorso_id=abc123">Avviso di mobilità</a>
<a href="/bandi-e-avvisi/dettaglio-bando-avviso/?concorso_id=abc123">duplicato</a>
<a href="/bandi-e-avvisi/dettaglio-bando-avviso/?concorso_id=def456">Concorso</a>
<a href="/bando-generico">non specifico</a>
</body></html>
"""

DETAIL = """
<html><body>
<h1>Concorso pubblico per 2 posti</h1>
<div>Descrizione: Procedura pubblica per l'assunzione di personale.</div>
<div>Area geografica: Marche</div>
<div>Valutazione: Per titoli ed esami</div>
<div>Stato: Aperto</div>
<div>Data apertura candidature: 01 Ottobre 2026 08:00</div>
<div>Data chiusura candidature: 31 Ottobre 2026 14:00</div>
<div>Numero di posti: 2</div>
<div>Ente di riferimento: Comune di Test</div>
<div>Bando/Avviso e Allegati:</div>
</body></html>
"""

def test_discover_only_specific_detail_links():
    rows = discover(html=LIST)
    assert [x["external_id"] for x in rows] == ["abc123", "def456"]
    assert all("/bandi-e-avvisi/dettaglio-bando-avviso/?concorso_id=" in x["official_url"] for x in rows)

def test_parse_detail():
    item = parse_detail(DETAIL, "abc123", "https://www.inpa.gov.it/bandi-e-avvisi/dettaglio-bando-avviso/?concorso_id=abc123")
    assert item.title == "Concorso pubblico per 2 posti"
    assert item.authority == "Comune di Test"
    assert item.status == "OPEN"
    assert item.deadline == "31 Ottobre 2026 14:00"
    assert item.specific_link is True
    assert item.external_id == "abc123"

from ingestion.connectors.inpa import discover

API = {
  "totalElements": 2,
  "content": [
    {"concorsoId": "abc123", "titolo": "Concorso pubblico"},
    {"concorsoId": "abc123", "titolo": "duplicato"},
    {"concorsoId": "def456", "titolo": "Avviso"}
  ]
}

def test_discover_uses_api_records_and_specific_links():
    rows = discover(api_payload=API)
    assert [x["external_id"] for x in rows] == ["abc123", "def456"]
    assert rows[0]["official_url"].endswith("concorso_id=abc123")
    assert rows[1]["official_url"].endswith("concorso_id=def456")
