import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.validate import validate_repository


ROOT = Path(__file__).resolve().parents[1]


class RepositoryTests(unittest.TestCase):
    def test_repository_data_is_valid(self):
        errors, entry_count, capability_count = validate_repository(ROOT)
        self.assertEqual(errors, [])
        self.assertGreaterEqual(entry_count, 70)
        self.assertGreaterEqual(capability_count, 15)

    def test_generated_catalog_matches_authored_entries(self):
        authored = []
        for path in sorted((ROOT / "data").glob("*/*.json")):
            value = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(value, list):
                authored.extend(value)
        generated = json.loads((ROOT / "site" / "catalog.json").read_text(encoding="utf-8"))
        self.assertEqual({entry["id"] for entry in authored}, {entry["id"] for entry in generated})

    def test_duplicate_ids_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            copy_root = Path(temporary_directory) / "atlas"
            shutil.copytree(ROOT, copy_root, ignore=shutil.ignore_patterns(".git", "__pycache__"))
            path = copy_root / "data" / "codex" / "slash-commands.json"
            entries = json.loads(path.read_text(encoding="utf-8"))
            entries.append(entries[0])
            path.write_text(json.dumps(entries), encoding="utf-8")
            errors, _, _ = validate_repository(copy_root)
            self.assertTrue(any("duplicate id" in error for error in errors), errors)

    def test_cli_subcommand_can_reference_cli_command_parent(self):
        errors, _, _ = validate_repository(ROOT)
        self.assertFalse(
            any("CLI subcommand parent" in error for error in errors),
            errors,
        )

    def test_expanded_control_types_are_present(self):
        entries = []
        for path in sorted((ROOT / "data").glob("*/*.json")):
            value = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(value, list):
                entries.extend(value)
        types = {entry["type"] for entry in entries}
        for entry_type in (
            "cli-subcommand",
            "config-file",
            "environment-variable",
            "instruction-file",
        ):
            self.assertIn(entry_type, types)

    def test_capabilities_cover_all_five_tools(self):
        tools = {tool["id"] for tool in json.loads((ROOT / "data" / "tools.json").read_text(encoding="utf-8"))}
        capabilities = json.loads((ROOT / "data" / "capabilities.json").read_text(encoding="utf-8"))
        for capability in capabilities:
            with self.subTest(capability=capability["id"]):
                self.assertEqual(tools, {mapping["tool"] for mapping in capability["mappings"]})

    def test_website_exposes_requested_filters(self):
        app = (ROOT / "site" / "app.js").read_text(encoding="utf-8")
        for filter_id in ("tool", "type", "category", "maturity"):
            self.assertIn(f'id="{filter_id}"', app)

    def test_generated_website_routes_are_unique_and_complete(self):
        routes = json.loads((ROOT / "site" / "routes.json").read_text(encoding="utf-8"))
        catalog = json.loads((ROOT / "site" / "catalog.json").read_text(encoding="utf-8"))
        capabilities = json.loads((ROOT / "site" / "capabilities.json").read_text(encoding="utf-8"))
        tools = json.loads((ROOT / "site" / "tools.json").read_text(encoding="utf-8"))

        paths = [route["path"] for route in routes]
        self.assertEqual(len(paths), len(set(paths)))
        self.assertEqual(len(routes), len(catalog) + len(capabilities) + len(tools) + 1)
        self.assertEqual({entry["path"] for entry in catalog}, {route["path"] for route in routes if route["kind"] == "entry"})
        self.assertEqual({capability["path"] for capability in capabilities}, {route["path"] for route in routes if route["kind"] == "capability"})

        for route in routes:
            with self.subTest(route=route["path"]):
                page = ROOT / "site" / route["path"] / "index.html"
                self.assertTrue(page.is_file(), page)
                contents = page.read_text(encoding="utf-8")
                self.assertIn("<base href=", contents)
                expected_route = route["kind"] if route["id"] is None else f"{route['kind']}:{route['id']}"
                self.assertIn(f'data-route="{expected_route}"', contents)

    def test_generated_catalog_paths_handle_common_command_names(self):
        catalog = json.loads((ROOT / "site" / "catalog.json").read_text(encoding="utf-8"))
        by_id = {entry["id"]: entry for entry in catalog}
        self.assertEqual(by_id["codex.slash-command.compact"]["path"], "codex/compact/")
        self.assertEqual(by_id["claude-code.slash-command.compact"]["path"], "claude-code/compact/")
        self.assertEqual(by_id["gemini-cli.slash-command.compress"]["path"], "gemini-cli/compress/")

    def test_pages_workflow_publishes_validated_site_directory(self):
        workflow = (ROOT / ".github" / "workflows" / "pages.yml").read_text(encoding="utf-8")
        for expected in (
            "pages: write",
            "id-token: write",
            "python scripts/validate.py",
            "python scripts/build_catalog.py",
            "node tests/test_site_search.js",
            "actions/configure-pages@v5",
            "actions/upload-pages-artifact@v4",
            "actions/deploy-pages@v4",
            "path: site",
        ):
            self.assertIn(expected, workflow)
        self.assertTrue((ROOT / "site" / ".nojekyll").is_file())


if __name__ == "__main__":
    unittest.main()
