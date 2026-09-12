import re
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urljoin

from scripts.build_catalog import add_entry_paths, build_routes


class BuildRoutesTests(unittest.TestCase):
    TEMPLATE = """<!doctype html>
<html><head><meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body data-route="home"><a class="skip-link" href="#main-content">Skip</a><main id="main-content"></main></body></html>
"""

    def make_site(self, root: Path) -> Path:
        site = root / "site"
        site.mkdir()
        (site / "index.html").write_text(self.TEMPLATE, encoding="utf-8")
        (site / "app.js").write_text("app", encoding="utf-8")
        (site / "styles.css").write_text("styles", encoding="utf-8")
        return site

    def test_entry_alias_collision_fails_before_site_mutation(self):
        entries = [
            {
                "id": "codex.slash-command.route-collision-demo",
                "tool": "codex",
                "type": "slash-command",
                "name": "/route-collision-demo",
                "description": "Slash command fixture.",
                "display_name": "Route collision demo",
            },
            {
                "id": "codex.config-option.route-collision-demo",
                "tool": "codex",
                "type": "config-option",
                "name": "route-collision-demo",
                "description": "Configuration option fixture.",
                "display_name": "Route collision demo option",
            },
            {
                "id": "codex.config-option.slash-command-route-collision-demo",
                "tool": "codex",
                "type": "config-option",
                "name": "slash-command-route-collision-demo",
                "description": "Configuration option collision fixture.",
                "display_name": "Route collision alias match",
            },
        ]
        add_entry_paths(entries)

        with TemporaryDirectory() as temporary_directory:
            site = self.make_site(Path(temporary_directory))
            sentinel = site / "codex" / "sentinel" / "index.html"
            sentinel.parent.mkdir(parents=True)
            sentinel.write_text("keep", encoding="utf-8")
            template_before = (site / "index.html").read_text(encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "route collision.*codex/slash-command-route-collision-demo/"):
                build_routes(site, [{"id": "codex", "name": "Codex"}], entries, [])

            self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")
            self.assertEqual((site / "index.html").read_text(encoding="utf-8"), template_before)
            self.assertFalse((site / "codex" / "route-collision-demo").exists())

    def test_capability_slug_collision_fails_before_site_mutation(self):
        capabilities = [
            {"id": "context.foo-bar", "display_name": "Foo bar", "description": "First fixture."},
            {"id": "context.foo.bar", "display_name": "Foo bar two", "description": "Second fixture."},
        ]

        with TemporaryDirectory() as temporary_directory:
            site = self.make_site(Path(temporary_directory))
            sentinel = site / "compare" / "sentinel" / "index.html"
            sentinel.parent.mkdir(parents=True)
            sentinel.write_text("keep", encoding="utf-8")
            template_before = (site / "index.html").read_text(encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "route collision.*compare/context-foo-bar/"):
                build_routes(site, [{"id": "codex", "name": "Codex"}], [], capabilities)

            self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")
            self.assertEqual((site / "index.html").read_text(encoding="utf-8"), template_before)
            self.assertFalse((site / "compare" / "context-foo-bar").exists())
            self.assertNotIn("path", capabilities[0])
            self.assertNotIn("path", capabilities[1])

    def test_skip_links_target_each_generated_route_under_root_and_project_prefix(self):
        entries = [
            {
                "id": "codex.slash-command.demo",
                "tool": "codex",
                "type": "slash-command",
                "name": "/demo",
                "description": "Entry fixture.",
                "display_name": "Demo",
                "legacy_paths": ["codex/legacy-demo/"],
            }
        ]
        add_entry_paths(entries)
        capabilities = [{"id": "context.demo", "display_name": "Demo context", "description": "Capability fixture."}]
        tools = [{"id": "codex", "name": "Codex"}]

        with TemporaryDirectory() as temporary_directory:
            site = self.make_site(Path(temporary_directory))
            build_routes(site, tools, entries, capabilities)

            route_paths = [
                "codex/",
                entries[0]["path"],
                "codex/legacy-demo/",
                "compare/",
                "coverage/",
                "guide/",
                capabilities[0]["path"],
            ]
            for route_path in route_paths:
                page = (site / route_path / "index.html").read_text(encoding="utf-8")
                base = re.search(r'<base href="([^"]+)">', page).group(1)
                href = re.search(r'class="skip-link" href="([^"]+)"', page).group(1)
                self.assertEqual(href, f"{route_path}#main-content")
                for prefix in ("", "agent-command-atlas/"):
                    document = f"https://example.test/{prefix}{route_path}"
                    target = urljoin(urljoin(document, base), href)
                    self.assertEqual(target, f"https://example.test/{prefix}{route_path}#main-content")


if __name__ == "__main__":
    unittest.main()
