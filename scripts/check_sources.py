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


def registered_urls(root: Path = ROOT) -> list[tuple[str, str]]:
    sources = json.loads((root / "data" / "sources.json").read_text(encoding="utf-8"))
    return [(tool, source["url"]) for tool, rows in sources.items() for source in rows]


def check_url(url: str, timeout: float, redirects_left: int = 5) -> tuple[bool, str]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Agent-Command-Atlas source checker",
            "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.1",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response.read(1)
            return 200 <= response.status < 400, f"{response.status} {response.geturl()}"
    except urllib.error.HTTPError as exc:
        location = exc.headers.get("Location")
        if 300 <= exc.code < 400 and location and redirects_left:
            target = urllib.parse.urljoin(url, location)
            ok, detail = check_url(target, timeout, redirects_left - 1)
            return ok, f"{exc.code} {target} -> {detail}"
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
