import os
import unittest
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlparse

from linkedin_service import (
    authorization_url,
    consume_oauth_state,
    create_oauth_state,
    fetch_connections,
)


class LinkedInTests(unittest.TestCase):
    def test_oauth_state_is_single_use(self):
        state = create_oauth_state()
        self.assertTrue(consume_oauth_state(state))
        self.assertFalse(consume_oauth_state(state))

    @patch.dict(
        os.environ,
        {
            "LINKEDIN_CLIENT_ID": "client-123",
            "LINKEDIN_REDIRECT_URI": "http://localhost:8000/auth/linkedin/callback",
            "LINKEDIN_CONNECTIONS_ENABLED": "true",
        },
        clear=False,
    )
    def test_authorization_url_requests_first_degree_scope(self):
        params = parse_qs(urlparse(authorization_url("state-123")).query)
        self.assertEqual(params["client_id"], ["client-123"])
        self.assertIn("r_1st_connections", params["scope"][0])

    @patch("linkedin_service.requests.get")
    def test_connection_response_is_normalized(self, get):
        response = Mock()
        response.ok = True
        response.json.return_value = {
            "elements": [
                {"to~": {"id": "person-1", "firstName": {"localized": {"en_US": "Neha"}}, "lastName": {"localized": {"en_US": "Rao"}}}},
                {"to~": {"id": "person-2", "firstName": {"localized": {"en_US": "Asha"}}, "lastName": {"localized": {"en_US": "Mehta"}}}},
            ]
        }
        get.return_value = response
        contacts = fetch_connections("token")
        self.assertEqual([contact.name for contact in contacts], ["Neha Rao", "Asha Mehta"])


if __name__ == "__main__":
    unittest.main()
