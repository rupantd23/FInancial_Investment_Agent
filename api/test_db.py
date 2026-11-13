import os
import unittest
from unittest.mock import patch

from db import SupabaseNotConfigured, get_supabase_client


class DatabaseConfigTests(unittest.TestCase):
    def test_admin_client_requires_service_key(self):
        with patch.dict(os.environ, {"SUPABASE_URL": "https://example.supabase.co"}, clear=True):
            with self.assertRaises(SupabaseNotConfigured):
                get_supabase_client(admin=True)

    def test_public_client_requires_anonymous_key(self):
        with patch.dict(os.environ, {"SUPABASE_URL": "https://example.supabase.co"}, clear=True):
            with self.assertRaises(SupabaseNotConfigured):
                get_supabase_client(admin=False)


if __name__ == "__main__":
    unittest.main()
