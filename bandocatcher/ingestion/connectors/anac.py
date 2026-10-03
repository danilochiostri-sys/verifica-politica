from .base import Opportunity

SOURCE="anac-bdncp"

def fetch(limit=50):
    # BDNCP publishes open CSV/JSON datasets and an Analytics search.
    # The exact downloadable dataset URLs are intentionally not hard-coded here:
    # they must be discovered/validated against the current ANAC open-data portal
    # before automated ingestion is enabled.
    raise RuntimeError("ANAC_BDNCP_PENDING_DATASET_VALIDATION")
