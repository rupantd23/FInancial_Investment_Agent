"""Local Gemini connection check.

Run this only after setting GEMINI_API_KEY in api/.env. The supplied text is a
synthetic smoke-test excerpt, not company research.
"""

from __future__ import annotations

import json
import os

from dotenv import load_dotenv

from llm import generate_research


load_dotenv()


result = generate_research(
    "TCS",
    [
        {
            "source_id": "smoke-test-annual-report",
            "source_type": "annual_report",
            "page_number": 1,
            "content": "Synthetic smoke-test excerpt: management describes diversified enterprise demand.",
        },
        {
            "source_id": "smoke-test-transcript",
            "source_type": "earnings_call_transcript",
            "page_number": 2,
            "content": "Synthetic smoke-test excerpt: management says execution remains a priority.",
        },
    ],
)
print(json.dumps(result, indent=2))
