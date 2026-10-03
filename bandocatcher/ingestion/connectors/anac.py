from .base import Opportunity

SOURCE="anac-bdncp"
OPEN_DATA_PORTAL="https://www.anticorruzione.it/dati-e-open-data"
SEARCH_PORTAL="https://pubblicita.anticorruzione.it/"

def fetch(limit=50):
    # ANAC exposes BDNCP open datasets in CSV/JSON, organized by period.
    # The dataset download endpoint is intentionally kept behind an explicit
    # configuration value until its current published URL/schema is validated.
    # This connector therefore fails closed instead of guessing a download URL.
    raise RuntimeError("ANAC_BDNCP_DATASET_URL_NOT_CONFIGURED")
