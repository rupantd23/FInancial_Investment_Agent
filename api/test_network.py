import unittest

from network_service import parse_csv_bytes


class NetworkImportTests(unittest.TestCase):
    def test_parses_aliases_and_skill_lists(self):
        result = parse_csv_bytes(
            b"full_name,title,employer,industry,expertise\n"
            b"Neha Rao,Technology executive,TCS,Technology,delivery; cloud\n"
        )
        self.assertEqual(len(result["valid_rows"]), 1)
        self.assertEqual(result["valid_rows"][0]["name"], "Neha Rao")
        self.assertEqual(result["valid_rows"][0]["skills"], ["delivery", "cloud"])
        self.assertEqual(result["errors"], [])

    def test_reports_invalid_rows_without_discarding_valid_rows(self):
        result = parse_csv_bytes(
            b"name,role\n"
            b"Valid Person,Analyst\n"
            b",Missing name\n"
        )
        self.assertEqual(len(result["valid_rows"]), 1)
        self.assertEqual(len(result["errors"]), 1)

    def test_requires_name_header(self):
        result = parse_csv_bytes(b"role,company\nAnalyst,TCS\n")
        self.assertEqual(result["valid_rows"], [])
        self.assertIn("name column", result["errors"][0])


if __name__ == "__main__":
    unittest.main()
