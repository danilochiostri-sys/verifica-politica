# Ingestion contract

Ogni connector deve produrre un Opportunity DTO compatibile con schema/opportunity.schema.json.

Pipeline:
1. discover
2. fetch
3. raw snapshot
4. parse
5. normalize
6. validate
7. deduplicate
8. change detection
9. publish

La V1 usa un dataset statico per il frontend. La pipeline live verrà aggiunta in ingestion/connectors/ senza cambiare il contratto UI.
