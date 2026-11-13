import unittest

from research_service import _to_ui_research


class ResearchServiceTests(unittest.TestCase):
    def test_transforms_validated_gemini_output_for_ui(self):
        result = _to_ui_research(
            "TCS",
            {"name": "Tata Consultancy Services"},
            {
                "summary": "Summary",
                "claims": [{"text": "Claim", "status": "verified", "source_id": "chunk-1", "page": 4}],
                "missing_evidence": ["Guidance"],
                "bull_case": "Bull",
                "bear_case": "Bear",
                "model": "gemini-2.5-flash",
                "provenance": "Gemini interpretation",
            },
            {"chunk-1": {"title": "Annual report", "source_type": "annual_report", "source_url": "https://example.com", "provenance": "verified"}},
            1,
        )
        self.assertTrue(result["available"])
        self.assertEqual(result["sections"][1]["source"]["page"], "p. 4")
        self.assertEqual(result["sections"][-1]["status"], "Unavailable")


if __name__ == "__main__":
    unittest.main()
