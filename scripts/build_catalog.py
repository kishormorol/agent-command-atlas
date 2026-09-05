#!/usr/bin/env python3
"""Build deterministic website data from the authored data directory."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
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
    type_priority = {
        "slash-command": 0,
        "prefix-command": 1,
        "cli-command": 2,
        "cli-subcommand": 3,
        "cli-flag": 4,
        "shortcut": 5,
        "mode": 6,
        "permission": 7,
        "workflow": 8,
        "skill": 9,
        "agent": 10,
        "mcp": 11,
        "hook": 12,
        "plugin": 13,
        "extension": 14,
        "config-file": 15,
        "instruction-file": 16,
        "config-option": 17,
        "environment-variable": 18,
    }
    raw_slugs = {
        entry["id"]: slugify(entry["name"], entry["id"].rsplit(".", 1)[-1])
        for entry in entries
    }
    groups: dict[tuple[str, str], list[dict]] = {}
    for entry in entries:
        groups.setdefault((entry["tool"], raw_slugs[entry["id"]]), []).append(entry)
    primary_ids = {
        min(group, key=lambda entry: (type_priority.get(entry["type"], 99), entry["id"]))["id"]
        for group in groups.values()
    }
    used: set[str] = set()
    for entry in entries:
        raw = raw_slugs[entry["id"]]
        if entry["id"] in primary_ids:
            slug = raw
            group = groups[(entry["tool"], raw)]
            if len(group) > 1 and not any(
                candidate["id"] != entry["id"] and candidate["type"] == entry["type"]
                for candidate in group
            ):
                entry["legacy_paths"] = [f"{entry['tool']}/{entry['type']}-{raw}/"]
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
        lambda _match: f'<meta name="description" content="{escape(description, quote=True)}">',
        page,
        count=1,
    )
    for attribute, name, content in (
        ("property", "og:title", title),
        ("property", "og:description", description),
        ("name", "twitter:title", title),
        ("name", "twitter:description", description),
    ):
        page = re.sub(
            rf'<meta {attribute}="{name}" content="[^"]*">',
            lambda _match, attribute=attribute, name=name, content=content: (
                f'<meta {attribute}="{name}" content="{escape(content, quote=True)}">'
            ),
            page,
            count=1,
        )
    page = re.sub(r'\n\s*<meta property="og:image(?::(?:width|height))?" content="[^"]*">', "", page)
    page = re.sub(r'\n\s*<meta name="twitter:image" content="[^"]*">', "", page)
    return page.replace('<body data-route="home">', f'<body data-route="{escape(route, quote=True)}">', 1)


def write_route(path: Path, page: str) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "index.html").write_text(page, encoding="utf-8")


def asset_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def stamp_asset_caches(site: Path) -> dict[str, str]:
    """Point index.html at content-derived asset queries so a changed file is never served stale."""
    digests = {name: asset_digest(site / name) for name in ("app.js", "styles.css")}
    index = site / "index.html"
    page = index.read_text(encoding="utf-8")
    stamped = re.sub(
        r'<script src="app\.js(?:\?v=[^"]*)?"></script>',
        f'<script src="app.js?v={digests["app.js"]}"></script>',
        page,
        count=1,
    )
    stamped = re.sub(
        r'<link rel="stylesheet" href="styles\.css(?:\?v=[^"]*)?">',
        f'<link rel="stylesheet" href="styles.css?v={digests["styles.css"]}">',
        stamped,
        count=1,
    )
    if stamped != page:
        index.write_text(stamped, encoding="utf-8")
    return digests


def build_routes(site: Path, tools: list[dict], entries: list[dict], capabilities: list[dict]) -> list[dict]:
    """Generate static shells so tool, entry, and comparison URLs work on static hosts."""
    stamp_asset_caches(site)
    template = (site / "index.html").read_text(encoding="utf-8")
    for route_root in [tool["id"] for tool in tools] + ["compare", "coverage"]:
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
        for legacy_path in entry.get("legacy_paths", []):
            write_route(
                site / legacy_path,
                route_page(
                    template,
                    f"entry:{entry['id']}",
                    f"{entry['name']} — {entry['display_name']} | Agent Command Atlas",
                    description,
                    2,
                ),
            )

    write_route(
        site / "compare",
        route_page(
            template,
            "compare",
            "Compare AI Coding Agent Commands | Agent Command Atlas",
            "Compare equivalent and related capabilities across Codex, Claude Code, Gemini CLI, Cursor, GitHub Copilot CLI, and Muse Code.",
            1,
        ),
    )
    routes.append({"path": "compare/", "kind": "compare", "id": None})
    write_route(
        site / "coverage",
        route_page(
            template,
            "coverage",
            "Dataset Coverage | Agent Command Atlas",
            "Inspect record counts, verification, lifecycle states, and structured coverage across all six Agent Command Atlas ecosystems.",
            1,
        ),
    )
    routes.append({"path": "coverage/", "kind": "coverage", "id": None})
    write_route(
        site / "guide",
        route_page(
            template,
            "guide",
            "How to Use the Atlas | Agent Command Atlas",
            "Learn how to search, filter, compare, and verify AI coding-agent commands in Agent Command Atlas.",
            1,
        ),
    )
    routes.append({"path": "guide/", "kind": "guide", "id": None})
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
