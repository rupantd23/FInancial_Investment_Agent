import unittest

from llm import build_research_prompt


class LlmPromptTests(unittest.TestCase):
    def test_prompt_excludes_non_primary_sources(self):
        prompt = build_research_prompt(
            "tcs.ns",
            [
                {"source_id": "annual-1", "source_type": "annual_report", "page_number": 4, "content": "annual evidence"},
                {"source_id": "news-1", "source_type": "news", "page_number": 1, "content": "news evidence"},
            ],
        )
        self.assertIn("annual evidence", prompt)
        self.assertNotIn("news evidence", prompt)

    def test_prompt_exposes_missing_evidence_when_chunks_are_empty(self):
        prompt = build_research_prompt("INFY", [])
        self.assertIn("NO PERMITTED EVIDENCE WAS RETRIEVED", prompt)


if __name__ == "__main__":
    unittest.main()
