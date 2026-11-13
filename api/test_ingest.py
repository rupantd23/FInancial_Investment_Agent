import unittest

from ingest import chunk_pages, compare_periods, normalize_nse_ticker, yfinance_symbol


class IngestTests(unittest.TestCase):
    def test_normalizes_nse_and_bse_suffixes(self):
        self.assertEqual(normalize_nse_ticker(" reliance.ns "), "RELIANCE")
        self.assertEqual(normalize_nse_ticker("TCS.BO"), "TCS")
        self.assertEqual(yfinance_symbol("INFY"), "INFY.NS")

    def test_chunks_keep_page_numbers(self):
        chunks = chunk_pages([{"page_number": 4, "text": "alpha " * 20}], max_chars=20)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(chunk["page_number"] == 4 for chunk in chunks))

    def test_period_comparison_handles_missing_and_zero(self):
        self.assertEqual(compare_periods(110, 100)["value"], 10.0)
        self.assertEqual(compare_periods(110, 0)["status"], "unavailable")
        self.assertEqual(compare_periods(None, 100)["status"], "unavailable")


if __name__ == "__main__":
    unittest.main()
