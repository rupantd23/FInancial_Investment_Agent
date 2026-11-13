import unittest

from research_service import _to_ui_research


class ResearchServiceTests(unittest.TestCase):
    def test_transforms_validated_gemini_output_for_ui(self):
        result = _to_ui_research(
            "TCS",
            {"name": "Tata Consultancy Services"},
            {
                "summary": "Summary",
                "summary_sources": [{"source_id": "chunk-1", "page": 4}],
                "business_snapshot": {"text": "Business", "status": "verified", "source_id": "chunk-1", "page": 4, "metrics": []},
                "financial_snapshot": {"text": "Financial", "status": "unavailable", "source_id": None, "page": None, "metrics": []},
                "trajectory": {"text": "Trajectory", "status": "unavailable", "source_id": None, "page": None, "metrics": []},
                "balance_sheet": {"text": "Balance sheet", "status": "unavailable", "source_id": None, "page": None, "metrics": []},
                "cash_quality": {"text": "Cash quality", "status": "unavailable", "source_id": None, "page": None, "metrics": []},
                "narrative_vs_numbers": {"text": "Narrative", "status": "unavailable", "source_id": None, "page": None, "metrics": []},
                "guidance": {"text": "Guidance", "status": "unavailable", "source_id": None, "page": None, "metrics": []},
                "claims": [{"text": "Claim", "status": "verified", "source_id": "chunk-1", "page": 4}],
                "missing_evidence": ["Guidance"],
                "bull_case": {"text": "Bull", "sources": [{"source_id": "chunk-1", "page": 4}]},
                "bear_case": {"text": "Bear", "sources": []},
                "model": "gemini-3.5-flash-lite",
                "provenance": "Gemini interpretation",
            },
            {"chunk-1": {"title": "Annual report", "source_type": "annual_report", "source_url": "https://example.com", "provenance": "verified"}},
            1,
        )
        self.assertTrue(result["available"])
        self.assertEqual(result["sections"][0]["source"]["page"], "p. 4")
        self.assertEqual(result["sections"][1]["source"]["page"], "p. 4")
        self.assertEqual(result["sections"][1]["label"], "Business snapshot")
        self.assertEqual(result["sections"][-1]["status"], "Unavailable")


if __name__ == "__main__":
    unittest.main()
