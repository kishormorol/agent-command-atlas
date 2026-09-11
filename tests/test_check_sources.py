import io
import unittest
import urllib.error
import urllib.request
import urllib.response
from email.message import Message
from unittest.mock import patch

from scripts.check_sources import check_url


class SourceCheckerTests(unittest.TestCase):
    def setUp(self):
        self.responses = {}
        self.requests = []
        self.enterContext(patch.object(urllib.request, "_opener", None))
        for handler, method in ((urllib.request.HTTPSHandler, "https_open"), (urllib.request.HTTPHandler, "http_open")):
            self.enterContext(patch.object(handler, method, side_effect=self.respond))

    def respond(self, request):
        self.requests.append(request.full_url)
        status, location = self.responses[request.full_url]
        headers = Message()
        if location:
            headers["Location"] = location
        response = urllib.response.addinfourl(io.BytesIO(b"source"), headers, request.full_url, status)
        response.msg = "fixture response"
        return response

    def test_direct_https_success(self):
        self.responses["https://example.com/docs"] = (200, None)
        self.assertEqual(check_url("https://example.com/docs", 1), (True, "200 https://example.com/docs"))

    def test_relative_https_redirect(self):
        self.responses = {"https://example.com/old": (302, "/docs"), "https://example.com/docs": (200, None)}
        self.assertEqual(check_url("https://example.com/old", 1), (True, "200 https://example.com/docs"))
        self.assertEqual(self.requests, list(self.responses))

    def test_http_input_is_rejected_without_a_request(self):
        self.responses["http://example.com/docs"] = (200, None)
        ok, detail = check_url("http://example.com/docs", 1)
        self.assertFalse(ok, detail)
        self.assertIn("HTTPS", detail)
        self.assertEqual(self.requests, [])

    def test_https_downgrade_is_rejected_before_http_request(self):
        self.responses = {"https://example.com/old": (302, "http://example.com/docs"), "http://example.com/docs": (200, None)}
        ok, detail = check_url("https://example.com/old", 1)
        self.assertFalse(ok, detail)
        self.assertIn("HTTPS", detail)
        self.assertEqual(self.requests, ["https://example.com/old"])

    def test_final_response_must_still_be_https(self):
        response = urllib.response.addinfourl(io.BytesIO(b"source"), Message(), "http://example.com/docs", 200)
        response.msg = "fixture response"
        with patch.object(urllib.request.HTTPSHandler, "https_open", return_value=response):
            ok, detail = check_url("https://example.com/docs", 1)
        self.assertFalse(ok, detail)

    def test_redirect_budget_stops_before_the_next_request(self):
        self.responses = {
            "https://example.com/a": (302, "/b"),
            "https://example.com/b": (302, "/c"),
            "https://example.com/c": (200, None),
        }
        ok, detail = check_url("https://example.com/a", 1, redirects_left=1)
        self.assertFalse(ok, detail)
        self.assertEqual(self.requests, ["https://example.com/a", "https://example.com/b"])

    def test_redirect_loop_returns_a_failure(self):
        self.responses["https://example.com/loop"] = (302, "/loop")
        ok, detail = check_url("https://example.com/loop", 1)
        self.assertFalse(ok, detail)

    def test_http_error_returns_a_failure(self):
        self.responses["https://example.com/missing"] = (404, None)
        ok, detail = check_url("https://example.com/missing", 1)
        self.assertFalse(ok)
        self.assertIn("404", detail)

    def test_transport_failures_return_diagnostics(self):
        for error in (TimeoutError("timed out"), urllib.error.URLError("unreachable")):
            with self.subTest(error=type(error).__name__):
                with patch.object(urllib.request.HTTPSHandler, "https_open", side_effect=error):
                    ok, detail = check_url("https://example.com/docs", 1)
                self.assertFalse(ok)
                self.assertIn(str(error), detail)
