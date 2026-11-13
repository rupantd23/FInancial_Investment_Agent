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
