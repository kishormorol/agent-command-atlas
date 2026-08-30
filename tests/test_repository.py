import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.build_catalog import route_page
from scripts.validate import validate_repository


ROOT = Path(__file__).resolve().parents[1]


class RepositoryTests(unittest.TestCase):
    def test_route_page_treats_metadata_backslashes_as_literal_text(self):
        template = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
        page = route_page(
            template,
            "entry:test.windows-path",
            "Windows path",
            r"Configure C:\Program Files\Agent without interpreting replacement escapes.",
            2,
        )
        self.assertIn(r"C:\Program Files\Agent", page)

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
        self.assertEqual(len(routes), len(catalog) + len(capabilities) + len(tools) + 3)
        self.assertIn({"path": "coverage/", "kind": "coverage", "id": None}, routes)
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

    def test_clean_routes_stay_with_the_primary_control_when_slugs_collide(self):
        catalog = json.loads((ROOT / "site" / "catalog.json").read_text(encoding="utf-8"))
        by_id = {entry["id"]: entry for entry in catalog}
        self.assertEqual(by_id["claude-code.slash-command.advisor"]["path"], "claude-code/advisor/")
        self.assertEqual(by_id["cursor.cli-command.agent"]["path"], "cursor/agent/")
        self.assertEqual(by_id["claude-code.cli-flag.version"]["path"], "claude-code/version/")
        self.assertEqual(by_id["claude-code.cli-flag.advisor"]["path"], "claude-code/cli-flag-advisor/")
        legacy_page = ROOT / "site" / "claude-code" / "slash-command-advisor" / "index.html"
        self.assertTrue(legacy_page.is_file())
        self.assertIn('data-route="entry:claude-code.slash-command.advisor"', legacy_page.read_text(encoding="utf-8"))

    def test_social_metadata_is_specific_to_shareable_pages(self):
        homepage = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
        self.assertIn('<meta property="og:title" content="Agent Command Atlas">', homepage)
        self.assertIn('<meta property="og:image" content="https://kishormorol.github.io/agent-command-atlas/og.png">', homepage)
        self.assertTrue((ROOT / "site" / "og.png").is_file())

        detail = (ROOT / "site" / "codex" / "compact" / "index.html").read_text(encoding="utf-8")
        self.assertIn('<meta property="og:title" content="/compact — Compact context | Agent Command Atlas">', detail)
        self.assertIn('<meta name="twitter:title" content="/compact — Compact context | Agent Command Atlas">', detail)
        self.assertNotIn('property="og:image"', detail)
        self.assertNotIn('name="twitter:image"', detail)

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

    def test_site_has_keyboard_and_responsive_accessibility_guards(self):
        homepage = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
        styles = (ROOT / "site" / "styles.css").read_text(encoding="utf-8")
        app = (ROOT / "site" / "app.js").read_text(encoding="utf-8")
        for expected in ('class="skip-link"', 'aria-label="Primary navigation"', 'id="main-content"'):
            self.assertIn(expected, homepage)
        for expected in (":focus-visible", "prefers-reduced-motion", "@media (max-width: 680px)"):
            self.assertIn(expected, styles)
        for expected in ('role="status"', 'aria-live="polite"', 'aria-label="Reference filters"'):
            self.assertIn(expected, app)


if __name__ == "__main__":
    unittest.main()
