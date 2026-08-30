#!/usr/bin/env python3
"""Build deterministic website data from the authored data directory."""

from __future__ import annotations

import json
import re
import shutil
from collections import Counter
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def slugify(value: str, fallback: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return slug or fallback


def add_entry_paths(entries: list[dict]) -> None:
    """Add deterministic, collision-safe website paths to generated entries."""
    raw_slugs = {
        entry["id"]: slugify(entry["name"], entry["id"].rsplit(".", 1)[-1])
        for entry in entries
    }
    counts = Counter((entry["tool"], raw_slugs[entry["id"]]) for entry in entries)
    used: set[str] = set()
    for entry in entries:
        raw = raw_slugs[entry["id"]]
        if counts[(entry["tool"], raw)] == 1:
            slug = raw
        else:
            slug = f"{entry['type']}-{raw}"
        path = f"{entry['tool']}/{slug}/"
        if path in used:
            slug = f"{slug}-{entry['id'].rsplit('.', 1)[-1]}"
            path = f"{entry['tool']}/{slug}/"
        if path in used:
            raise ValueError(f"Could not create a unique website path for {entry['id']}")
        used.add(path)
        entry["path"] = path


def route_page(template: str, route: str, title: str, description: str, depth: int) -> str:
    base = "../" * depth
    page = template.replace(
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f'<meta name="viewport" content="width=device-width, initial-scale=1">\n    <base href="{base}">',
        1,
    )
    page = page.replace("<title>Agent Command Atlas</title>", f"<title>{escape(title)}</title>", 1)
    page = re.sub(
        r'<meta name="description" content="[^"]*">',
        f'<meta name="description" content="{escape(description, quote=True)}">',
        page,
        count=1,
    )
    return page.replace('<body data-route="home">', f'<body data-route="{escape(route, quote=True)}">', 1)


def write_route(path: Path, page: str) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "index.html").write_text(page, encoding="utf-8")


def build_routes(site: Path, tools: list[dict], entries: list[dict], capabilities: list[dict]) -> list[dict]:
    """Generate static shells so tool, entry, and comparison URLs work on static hosts."""
    template = (site / "index.html").read_text(encoding="utf-8")
    for route_root in [tool["id"] for tool in tools] + ["compare"]:
        target = site / route_root
        if target.exists():
            shutil.rmtree(target)

    routes: list[dict] = []
    tool_names = {tool["id"]: tool["name"] for tool in tools}
    for tool in tools:
        description = f"Search documented {tool['name']} commands, flags, shortcuts, configuration, and control surfaces."
        write_route(
            site / tool["id"],
            route_page(template, f"tool:{tool['id']}", f"{tool['name']} Commands | Agent Command Atlas", description, 1),
        )
        routes.append({"path": f"{tool['id']}/", "kind": "tool", "id": tool["id"]})

    for entry in entries:
        description = f"{entry['name']} for {tool_names[entry['tool']]}: {entry['description']}"
        write_route(
            site / entry["path"],
            route_page(
                template,
                f"entry:{entry['id']}",
                f"{entry['name']} — {entry['display_name']} | Agent Command Atlas",
                description,
                2,
            ),
        )
        routes.append({"path": entry["path"], "kind": "entry", "id": entry["id"]})

    write_route(
        site / "compare",
        route_page(
            template,
            "compare",
            "Compare AI Coding Agent Commands | Agent Command Atlas",
            "Compare equivalent and related capabilities across Codex, Claude Code, Gemini CLI, Cursor, and GitHub Copilot CLI.",
            1,
        ),
    )
    routes.append({"path": "compare/", "kind": "compare", "id": None})
    for capability in capabilities:
        capability["path"] = f"compare/{slugify(capability['id'], 'capability')}/"
        write_route(
            site / capability["path"],
            route_page(
                template,
                f"capability:{capability['id']}",
                f"{capability['display_name']} Comparison | Agent Command Atlas",
                capability["description"],
                2,
            ),
        )
        routes.append({"path": capability["path"], "kind": "capability", "id": capability["id"]})
    return routes


def build(root: Path = ROOT) -> int:
    tools = sorted(read_json(root / "data" / "tools.json"), key=lambda item: item["order"])
    tool_order = {tool["id"]: tool["order"] for tool in tools}
    entries: list[dict] = []
    for tool_dir in sorted((root / "data").iterdir()):
        if not tool_dir.is_dir():
            continue
        for path in sorted(tool_dir.glob("*.json")):
            data = read_json(path)
            if isinstance(data, list):
                entries.extend(dict(item) for item in data)
    entries.sort(key=lambda item: (tool_order[item["tool"]], item["type"], item["name"], item["id"]))
    add_entry_paths(entries)
    capabilities = sorted((dict(item) for item in read_json(root / "data" / "capabilities.json")), key=lambda item: item["id"])
    categories = sorted(read_json(root / "data" / "categories.json"), key=lambda item: item["display_name"])

    site = root / "site"
    routes = build_routes(site, tools, entries, capabilities)
    write_json(site / "catalog.json", entries)
    write_json(site / "capabilities.json", capabilities)
    write_json(site / "categories.json", categories)
    write_json(site / "tools.json", tools)
    write_json(site / "routes.json", routes)
    print(f"Built {len(entries)} entries, {len(capabilities)} capabilities, and {len(routes)} routes -> {site}")
    return len(entries)


if __name__ == "__main__":
    build()
