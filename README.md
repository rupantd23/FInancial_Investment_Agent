# FINN

Financial Investment Agent - a mobile-first investor intelligence prototype.

## Prototype scope

- **Push:** a prioritized portfolio digest with source-backed announcements and market signals.
- **Pull:** research for an NSE ticker using annual reports and earnings-call transcripts.
- **Network:** explainable people suggestions shown inside Push and Pull.

The current implementation uses clearly labeled synthetic demo fixtures so the experience remains reliable while live ingestion is added. Synthetic values are not investment advice and must be replaced with retrieved primary-source data before submission.

## Gemini connection

The backend uses Google's `google-genai` SDK and Gemini's Interactions API. Keep these variables in `api/.env`:

```env
GEMINI_API_KEY=your-key
GEMINI_MODEL=gemini-3.8-flash
```

Install the backend requirements, then run the local smoke test:

```bash
source api/FIAenv/bin/activate
pip install -r api/requirements.txt
PYTHONPATH=api python api/smoke_gemini.py
```

The smoke test uses synthetic text only. FINN's real Pull path must pass only annual-report and earnings-call transcript chunks into `api/llm.py`; the adapter rejects other source types before sending the prompt.

## Supabase connection and seed

After running `supabase/schema.sql` in the Supabase SQL Editor and installing the Python client, check the connection:

```bash
cd api
source FIAenv/bin/activate
PYTHONPATH=. python check_supabase.py
PYTHONPATH=. python seed_supabase.py
```

The seed command uses the service-role key from `api/.env` only on the backend. It inserts the 15 portfolio companies and never prints credentials.

Create a private Supabase Storage bucket named `source-documents`. Then ingest a public annual report or transcript that you have legitimately downloaded:

```bash
PYTHONPATH=. python ingest_documents.py \
  --ticker TCS \
  --annual-report /absolute/path/tcs-annual-report.pdf \
  --annual-report-url https://source.example/annual-report.pdf \
  --provenance verified
```

After ingestion, `GET /research/TCS` retrieves only annual-report and earnings-call transcript chunks from Supabase and sends those chunks to Gemini. Use `GET /research/TCS?demo=true` only when you intentionally want the synthetic demo response.

## Repository layout

```text
web/       Next.js frontend
api/       FastAPI backend
data/      seed-data notes and future ingestion fixtures
docs/      architecture and implementation notes
```

## Run locally

### Backend

```bash
cd api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd web
npm install
npm run dev
```

Open <http://localhost:3000>. The frontend falls back to the included demo fixtures when the API is unavailable, so the UI can be reviewed independently.

## Provenance rules

- **Verified:** retrieved from a primary source and linked.
- **Calculated:** derived deterministically from verified values.
- **Interpreted:** model-generated from retrieved source excerpts.
- **Synthetic demo:** invented only to demonstrate interaction design.
- **Unavailable:** the requested evidence was not found.

Never commit API keys, real private profiles, or unlicensed scraped data. Network profiles in this prototype are synthetic.
