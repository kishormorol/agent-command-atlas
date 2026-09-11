import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.validate import validate_repository


ROOT = Path(__file__).resolve().parents[1]
ENTRY_SCHEMA = json.loads((ROOT / "schema" / "entry.schema.json").read_text(encoding="utf-8"))
CAPABILITY_SCHEMA = json.loads(
    (ROOT / "schema" / "capability.schema.json").read_text(encoding="utf-8")
)


TOOLS = [
    {"id": tool_id, "name": tool_id, "vendor": "Test", "order": index, "status": "active"}
    for index, tool_id in enumerate(
        ("codex", "claude-code", "gemini-cli", "cursor", "github-copilot", "muse-code"),
        start=1,
    )
]
CATEGORIES = [{"id": "help", "display_name": "Help", "description": "Help information."}]
CAPABILITIES = [
    {
        "id": "context.compact",
        "display_name": "Compact context",
        "description": "Reduce the active context.",
        "mappings": [
            {"tool": tool["id"], "entry_id": None, "relationship": "unknown"}
            for tool in TOOLS
        ],
    }
]
SOURCES = {
    tool["id"]: [
        {
            "url": "https://example.com/reference",
            "kind": "official-docs",
            "scope": "Test reference.",
        }
    ]
    for tool in TOOLS
}


def entry(entry_id: str = "codex.slash-command.test", name: str = "/test") -> dict:
    return {
        "id": entry_id,
        "tool": "codex",
        "name": name,
        "display_name": "Test command",
        "type": "slash-command",
        "category": "help",
        "role": "Test command.",
        "description": "A test command.",
        "syntax": [name],
        "examples": [{"command": name, "explanation": "Run it.", "level": "minimal"}],
        "maturity": "stable",
        "availability": {"channels": ["interactive"], "conditions": ["Always available."]},
        "sources": [{"url": "https://example.com/reference", "kind": "official-docs"}],
        "verification": {
            "status": "needs-verification",
            "last_verified": None,
            "tested_version": None,
            "verified_by": [],
        },
    }


class ValidationErrorTests(unittest.TestCase):
    def validate(self, *, entries=None, tools=None, categories=None, capabilities=None, sources=None):
        root = ROOT / "validation-fixture"
        values = {
            "entry.schema.json": ENTRY_SCHEMA,
            "capability.schema.json": CAPABILITY_SCHEMA,
            "tools.json": copy.deepcopy(TOOLS if tools is None else tools),
            "categories.json": copy.deepcopy(CATEGORIES if categories is None else categories),
            "capabilities.json": copy.deepcopy(CAPABILITIES if capabilities is None else capabilities),
            "sources.json": copy.deepcopy(SOURCES if sources is None else sources),
        }
        fixture_entries = [entry_item for entry_item in (entries or [entry()])]
        fixture_path = root / "data" / "codex" / "fixture.json"

        def load_json(path, errors, root=ROOT):
            return values[path.name]

        with patch("scripts.validate.load_json", side_effect=load_json), patch(
            "scripts.validate.load_entries",
            return_value=[(fixture_path, index, item) for index, item in enumerate(fixture_entries)],
        ):
            return validate_repository(root)

    def test_invalid_entry_collections_report_schema_errors_without_crashing(self):
        aliases = entry("codex.slash-command.aliases", "/aliases")
        aliases["aliases"] = None
        examples = entry("codex.slash-command.examples", "/examples")
        examples["examples"] = ["invalid"]
        capabilities = entry("codex.slash-command.capabilities", "/capabilities")
        capabilities["capabilities"] = [None]
        valid = entry("codex.slash-command.valid", "/valid")
        valid["capabilities"] = ["missing.capability"]

        errors, entry_count, capability_count = self.validate(
            entries=[aliases, examples, capabilities, valid]
        )

        self.assertEqual(entry_count, 4)
        self.assertEqual(capability_count, 1)
        self.assertTrue(any("aliases" in error for error in errors), errors)
        self.assertTrue(any("examples" in error for error in errors), errors)
        self.assertTrue(any("capabilities" in error for error in errors), errors)
        self.assertTrue(any("unknown capability missing.capability" in error for error in errors), errors)

    def test_invalid_capability_rows_report_schema_errors_without_crashing(self):
        valid_capability = copy.deepcopy(CAPABILITIES[0])
        valid_capability["mappings"][0] = {
            "tool": "codex",
            "entry_id": "codex.slash-command.missing",
            "relationship": "exact",
        }
        errors, entry_count, capability_count = self.validate(
            capabilities=[None, valid_capability]
        )

        self.assertEqual(entry_count, 1)
        self.assertEqual(capability_count, 2)
        self.assertTrue(any("data/capabilities.json:0" in error for error in errors), errors)
        self.assertTrue(
            any(
                "data/capabilities.json:1: unknown mapped entry codex.slash-command.missing" in error
                for error in errors
            ),
            errors,
        )

    def test_unhashable_tool_ids_report_errors_without_crashing(self):
        tools = copy.deepcopy(TOOLS)
        tools[0]["id"] = ["codex"]

        errors, _, _ = self.validate(tools=tools)

        self.assertTrue(any("data/tools.json:0" in error for error in errors), errors)

    def test_wrong_tool_field_shapes_report_errors_without_crashing(self):
        tools = copy.deepcopy(TOOLS)
        tools[0]["name"] = {"name": "codex"}
        tools[0]["order"] = [1]

        errors, _, _ = self.validate(tools=tools)

        self.assertTrue(any("name must be a string" in error for error in errors), errors)
        self.assertTrue(any("order must be an integer" in error for error in errors), errors)

    def test_unhashable_category_ids_report_errors_without_crashing(self):
        categories = copy.deepcopy(CATEGORIES)
        categories[0]["id"] = {"id": "help"}

        errors, _, _ = self.validate(categories=categories)

        self.assertTrue(any("data/categories.json:0" in error for error in errors), errors)

    def test_wrong_category_field_shapes_report_errors_without_crashing(self):
        categories = copy.deepcopy(CATEGORIES)
        categories[0]["description"] = ["Help information."]

        errors, _, _ = self.validate(categories=categories)

        self.assertTrue(any("description must be a string" in error for error in errors), errors)

    def test_invalid_source_fields_report_errors_without_crashing(self):
        sources = copy.deepcopy(SOURCES)
        sources["codex"][0]["url"] = ["https://example.com/reference"]
        sources["claude-code"][0]["kind"] = ["official-docs"]

        errors, _, _ = self.validate(sources=sources)

        self.assertTrue(any("data/sources.json:codex.0" in error for error in errors), errors)
        self.assertTrue(any("data/sources.json:claude-code.0" in error for error in errors), errors)

    def test_invalid_nested_reference_rows_report_errors_without_crashing(self):
        parent = entry("codex.cli-command.parent", "parent")
        parent["type"] = []
        child = entry("codex.cli-subcommand.child", "child")
        child["type"] = "cli-subcommand"
        child["parent_id"] = parent["id"]
        capabilities = copy.deepcopy(CAPABILITIES)
        capabilities[0]["mappings"][0]["relationship"] = []

        errors, _, _ = self.validate(entries=[parent, child], capabilities=capabilities)

        self.assertTrue(any("type" in error for error in errors), errors)
        self.assertTrue(any("mappings.0.relationship" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
