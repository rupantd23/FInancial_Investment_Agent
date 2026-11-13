# FINN

Financial Investment Agent - a mobile-first investor intelligence prototype.

## Prototype scope

- **Push:** a prioritized portfolio digest with source-backed announcements and market signals.
- **Pull:** research for an NSE ticker using annual reports and earnings-call transcripts.
- **Network:** explainable people suggestions shown inside Push and Pull.

The current implementation uses clearly labeled synthetic demo fixtures so the experience remains reliable while live ingestion is added. Synthetic values are not investment advice and must be replaced with retrieved primary-source data before submission.

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
