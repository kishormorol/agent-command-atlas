#!/usr/bin/env python3
"""Validate authored Atlas data and all cross-file references."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

try:
    import jsonschema
except ImportError:
    print("Install requirements: python -m pip install -r requirements.txt")
    raise SystemExit(2)


ROOT = Path(__file__).resolve().parents[1]
TOOL_IDS = {"codex", "claude-code", "gemini-cli", "cursor", "github-copilot"}


def load_json(path: Path, errors: list[str], root: Path = ROOT) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{path.relative_to(root)}: invalid JSON: {exc}")
        return None


def schema_errors(instance: Any, schema: dict[str, Any], label: str) -> list[str]:
    validator = jsonschema.Draft202012Validator(
        schema, format_checker=jsonschema.FormatChecker()
    )
    result = []
    for error in sorted(validator.iter_errors(instance), key=lambda item: tuple(map(str, item.path))):
        location = ".".join(str(part) for part in error.path)
        result.append(f"{label}{':' + location if location else ''}: {error.message}")
    return result


def load_entries(root: Path, errors: list[str]) -> list[tuple[Path, int, dict[str, Any]]]:
    entries = []
    for tool_dir in sorted((root / "data").iterdir()):
        if not tool_dir.is_dir():
            continue
        for path in sorted(tool_dir.glob("*.json")):
            data = load_json(path, errors, root)
            if data is None:
                continue
            if not isinstance(data, list):
                errors.append(f"{path.relative_to(root)}: expected a JSON array")
                continue
            for index, item in enumerate(data):
                if not isinstance(item, dict):
                    errors.append(f"{path.relative_to(root)}:{index}: expected an object")
                    continue
                entries.append((path, index, item))
    return entries


def validate_repository(root: Path = ROOT) -> tuple[list[str], int, int]:
    errors: list[str] = []
    entry_schema = load_json(root / "schema" / "entry.schema.json", errors, root)
    capability_schema = load_json(root / "schema" / "capability.schema.json", errors, root)
    tools = load_json(root / "data" / "tools.json", errors, root)
    categories = load_json(root / "data" / "categories.json", errors, root)
    capabilities = load_json(root / "data" / "capabilities.json", errors, root)
    sources = load_json(root / "data" / "sources.json", errors, root)
    if any(value is None for value in (entry_schema, capability_schema, tools, categories, capabilities, sources)):
        return errors, 0, 0
    expected_types = (
        (entry_schema, dict, "schema/entry.schema.json", "object"),
        (capability_schema, dict, "schema/capability.schema.json", "object"),
        (tools, list, "data/tools.json", "array"),
        (categories, list, "data/categories.json", "array"),
        (capabilities, list, "data/capabilities.json", "array"),
        (sources, dict, "data/sources.json", "object"),
    )
    for value, expected_type, label, expected_name in expected_types:
        if not isinstance(value, expected_type):
            errors.append(f"{label}: expected a JSON {expected_name}")
    if errors:
        return errors, 0, 0

    tool_ids = [tool.get("id") for tool in tools if isinstance(tool, dict)]
    for index, tool in enumerate(tools):
        if not isinstance(tool, dict) or not all(tool.get(key) is not None for key in ("id", "name", "vendor", "order", "status")):
            errors.append(f"data/tools.json:{index}: id, name, vendor, order, and status are required")
        elif tool["status"] not in {"active", "deprecated", "removed"}:
            errors.append(f"data/tools.json:{index}: unsupported status {tool['status']!r}")
    if len(tool_ids) != len(set(tool_ids)):
        errors.append("data/tools.json: duplicate tool id")
    if set(tool_ids) != TOOL_IDS:
        errors.append(f"data/tools.json: expected tool ids {sorted(TOOL_IDS)}, got {sorted(tool_ids)}")
    orders = [tool.get("order") for tool in tools if isinstance(tool, dict)]
    if len(orders) != len(set(orders)):
        errors.append("data/tools.json: duplicate tool order")

    category_ids = [item.get("id") for item in categories if isinstance(item, dict)]
    for index, category in enumerate(categories):
        if not isinstance(category, dict) or not all(category.get(key) for key in ("id", "display_name", "description")):
            errors.append(f"data/categories.json:{index}: id, display_name, and description are required")
    if len(category_ids) != len(set(category_ids)):
        errors.append("data/categories.json: duplicate category id")
    category_set = set(category_ids)

    if set(sources) != set(tool_ids):
        errors.append("data/sources.json: source registry keys must exactly match tool ids")
    registered_sources: dict[str, dict[str, str]] = {}
    for tool_id, rows in sources.items():
        if not isinstance(rows, list) or not rows:
            errors.append(f"data/sources.json:{tool_id}: expected a non-empty array")
            continue
        registry: dict[str, str] = {}
        for index, row in enumerate(rows):
            if not isinstance(row, dict) or not all(row.get(key) for key in ("url", "kind", "scope")):
                errors.append(f"data/sources.json:{tool_id}.{index}: url, kind, and scope are required")
                continue
            if not row["url"].startswith("https://"):
                errors.append(f"data/sources.json:{tool_id}.{index}: URL must use HTTPS")
            if row["kind"] not in {"official-docs", "official-source", "release-notes", "manual-test"}:
                errors.append(f"data/sources.json:{tool_id}.{index}: unsupported source kind {row['kind']!r}")
            if row["url"] in registry:
                errors.append(f"data/sources.json:{tool_id}: duplicate URL {row['url']}")
            registry[row["url"]] = row["kind"]
        registered_sources[tool_id] = registry

    entries = load_entries(root, errors)
    by_id: dict[str, dict[str, Any]] = {}
    names: dict[tuple[str, str, str], str] = {}
    aliases: dict[tuple[str, str, str], str] = {}
    for path, index, entry in entries:
        label = f"{path.relative_to(root)}:{index}"
        errors.extend(schema_errors(entry, entry_schema, label))
        entry_id = entry.get("id")
        if entry_id in by_id:
            errors.append(f"{label}: duplicate id {entry_id}")
        elif isinstance(entry_id, str):
            by_id[entry_id] = entry

        tool_id = entry.get("tool")
        entry_type = entry.get("type")
        if tool_id != path.parent.name:
            errors.append(f"{label}: tool {tool_id!r} does not match folder {path.parent.name!r}")
        if isinstance(entry_id, str) and isinstance(tool_id, str) and isinstance(entry_type, str):
            expected_prefix = f"{tool_id}.{entry_type}."
            if not entry_id.startswith(expected_prefix):
                errors.append(f"{label}: id must start with {expected_prefix!r}")
        if entry.get("category") not in category_set:
            errors.append(f"{label}: unknown category {entry.get('category')!r}")

        name = entry.get("name")
        if isinstance(name, str):
            key = (tool_id, entry_type, name.casefold())
            if key in names or key in aliases:
                owner = names.get(key) or aliases.get(key)
                errors.append(f"{label}: duplicate command name {name!r}; first used by {owner}")
            names[key] = entry_id
        for alias in entry.get("aliases", []):
            key = (tool_id, entry_type, alias.casefold())
            if alias.casefold() == str(name).casefold():
                errors.append(f"{label}: alias duplicates the canonical name {alias!r}")
            if key in names or key in aliases:
                owner = names.get(key) or aliases.get(key)
                errors.append(f"{label}: duplicate alias {alias!r}; first used by {owner}")
            aliases[key] = entry_id

        example_commands = [example.get("command") for example in entry.get("examples", [])]
        if len(example_commands) != len(set(example_commands)):
            errors.append(f"{label}: duplicate example command")
        if entry_type in {"slash-command", "cli-command", "cli-subcommand", "cli-flag", "shortcut", "prefix-command", "skill"} and not entry.get("examples"):
            errors.append(f"{label}: interactive and CLI entries require at least one example")

        registry = registered_sources.get(tool_id, {})
        for source in entry.get("sources", []):
            if source.get("url") not in registry:
                errors.append(f"{label}: source URL is not registered for {tool_id}: {source.get('url')}")
            elif registry[source["url"]] != source.get("kind"):
                errors.append(f"{label}: source kind does not match data/sources.json for {source['url']}")

        verification = entry.get("verification", {})
        if verification.get("status") not in {"needs-verification", "unverified"} and not verification.get("last_verified"):
            errors.append(f"{label}: verified entries require last_verified")

    for path, index, entry in entries:
        label = f"{path.relative_to(root)}:{index}"
        parent_id = entry.get("parent_id")
        if parent_id:
            parent = by_id.get(parent_id)
            if parent is None:
                errors.append(f"{label}: unknown parent_id {parent_id}")
            elif parent.get("tool") != entry.get("tool"):
                errors.append(f"{label}: parent must use the same tool")
            elif entry.get("type") == "cli-subcommand" and parent.get("type") not in {"cli-command", "cli-subcommand"}:
                errors.append(f"{label}: CLI subcommand parent must be a CLI command or subcommand")
            elif entry.get("type") != "cli-subcommand" and parent.get("type") != entry.get("type"):
                errors.append(f"{label}: parent must use the same type")
        for related_id in entry.get("related_commands", []):
            if related_id == entry.get("id"):
                errors.append(f"{label}: an entry cannot relate to itself")
            elif related_id not in by_id:
                errors.append(f"{label}: unknown related command {related_id}")
        for equivalent in entry.get("equivalent_commands", []):
            equivalent_id = equivalent.get("entry_id")
            if equivalent_id is not None and equivalent_id not in by_id:
                errors.append(f"{label}: unknown equivalent command {equivalent_id}")
            elif equivalent_id is not None and by_id[equivalent_id].get("tool") != equivalent.get("tool"):
                errors.append(f"{label}: equivalent command {equivalent_id} belongs to another tool")

    capability_ids: set[str] = set()
    for index, capability in enumerate(capabilities):
        label = f"data/capabilities.json:{index}"
        errors.extend(schema_errors(capability, capability_schema, label))
        capability_id = capability.get("id")
        if capability_id in capability_ids:
            errors.append(f"{label}: duplicate capability id {capability_id}")
        capability_ids.add(capability_id)
        mappings = capability.get("mappings", [])
        mapped_tools = [mapping.get("tool") for mapping in mappings]
        if set(mapped_tools) != set(tool_ids) or len(mapped_tools) != len(set(mapped_tools)):
            errors.append(f"{label}: mappings must contain each tool exactly once")
        for mapping in mappings:
            entry_id = mapping.get("entry_id")
            relationship = mapping.get("relationship")
            if relationship in {"exact", "similar", "partial"} and not entry_id:
                errors.append(f"{label}: {relationship} mapping for {mapping.get('tool')} requires entry_id")
            if relationship == "none" and entry_id is not None:
                errors.append(f"{label}: none mapping for {mapping.get('tool')} must not have entry_id")
            if entry_id:
                mapped_entry = by_id.get(entry_id)
                if mapped_entry is None:
                    errors.append(f"{label}: unknown mapped entry {entry_id}")
                elif mapped_entry.get("tool") != mapping.get("tool"):
                    errors.append(f"{label}: mapped entry {entry_id} belongs to another tool")
                elif capability_id not in mapped_entry.get("capabilities", []):
                    errors.append(f"{label}: mapped entry {entry_id} does not declare {capability_id}")

    for path, index, entry in entries:
        for capability_id in entry.get("capabilities", []):
            if capability_id not in capability_ids:
                errors.append(f"{path.relative_to(root)}:{index}: unknown capability {capability_id}")

    return errors, len(entries), len(capabilities)


def main() -> int:
    errors, entry_count, capability_count = validate_repository()
    if errors:
        print("\n".join(errors))
        return 1
    print(f"OK: {entry_count} entries and {capability_count} capabilities validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
