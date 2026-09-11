#!/usr/bin/env python3
"""Check that registered official source URLs resolve over HTTPS."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class HTTPSRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        if urllib.parse.urlsplit(new_url).scheme != "https":
            response.close()
            raise urllib.error.URLError("Source redirects must use HTTPS")
        return super().redirect_request(request, response, code, message, headers, new_url)


def registered_urls(root: Path = ROOT) -> list[tuple[str, str]]:
    sources = json.loads((root / "data" / "sources.json").read_text(encoding="utf-8"))
    return [(tool, source["url"]) for tool, rows in sources.items() for source in rows]


def check_url(url: str, timeout: float, redirects_left: int = 5) -> tuple[bool, str]:
    if urllib.parse.urlsplit(url).scheme != "https":
        return False, "Source URLs must use HTTPS"
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Agent-Command-Atlas source checker",
            "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.1",
        },
    )
    redirects = HTTPSRedirectHandler()
    redirects.max_redirections = redirects_left
    redirects.max_repeats = redirects_left
    opener = urllib.request.build_opener(redirects)
    try:
        with opener.open(request, timeout=timeout) as response:
            if urllib.parse.urlsplit(response.geturl()).scheme != "https":
                return False, "Source responses must use HTTPS"
            response.read(1)
            return 200 <= response.status < 400, f"{response.status} {response.geturl()}"
    except urllib.error.HTTPError as exc:
        exc.close()
        return False, str(exc)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return False, str(exc)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=float, default=15, help="seconds per URL (default: 15)")
    args = parser.parse_args()
    failures = 0
    for tool, url in registered_urls():
        ok, detail = check_url(url, args.timeout)
        print(f"{'OK' if ok else 'FAIL'} {tool}: {url} -> {detail}")
        failures += not ok
    if failures:
        print(f"{failures} source URL(s) failed", file=sys.stderr)
        return 1
    print("All registered source URLs resolved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
