# FINN prototype architecture

```text
yfinance / exchange filings / annual reports / transcripts / synthetic profiles
                              |
                         FastAPI ingestion
                              |
                    Supabase PostgreSQL + Storage
                              |
          deterministic rules + source-constrained retrieval
                              |
                         FastAPI JSON API
                              |
                      Next.js mobile-first UI
```

The current repository implements the API contracts and UI with synthetic demo fixtures. The next implementation slice replaces each fixture with a persisted source record, page-aware PDF chunks, and cached analyses. LLM output should be schema-validated and attached to source citations; price calculations and network ranking should remain deterministic.

## Implementation order

1. Replace `api/main.py` fixture reads with Supabase reads.
2. Run `api/ingest.py` from a protected scheduled job and persist market records.
3. Upload annual reports and transcripts to Supabase Storage.
4. Extract page-aware chunks with PyMuPDF.
5. Add embeddings only after keyword retrieval and citation tests pass.
6. Add an LLM adapter that can only see retrieved annual-report and transcript chunks.
