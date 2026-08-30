# Agent Command Atlas

**The living reference for AI coding agent commands.**

Agent Command Atlas is an open-source, source-linked reference for commands, flags, shortcuts, configuration, and control surfaces across leading AI coding agents:

1. OpenAI Codex
2. Anthropic Claude Code
3. Google Gemini CLI
4. Cursor
5. GitHub Copilot CLI

The project turns one canonical dataset into two complementary outputs:

- an open GitHub command and capability database;
- a fast, searchable documentation website.

Browse the live reference at [kishormorol.github.io/agent-command-atlas](https://kishormorol.github.io/agent-command-atlas/). The website includes task-aware search, permanent command pages, cross-tool comparisons, copy-ready examples, guided usage, and a transparent dataset coverage dashboard.

## What the atlas covers

- Slash and interactive commands
- CLI commands and flags
- Keyboard shortcuts and prefix commands such as `@` and `!`
- Configuration files and environment variables
- Permissions, sandboxing, and modes
- MCP, skills, hooks, agents, and subagents
- Sessions, models, Git, and worktrees

Accuracy takes priority over command count. Entries link to official documentation or official source repositories, record verification state and date, and preserve experimental, conditional, rolling-out, deprecated, or removed status.

## Data is the source of truth

```text
data/ ──▶ validated catalog ──▶ website
  │
  └──────────────────────────▶ cross-tool capability atlas
```

Do not manually maintain large command inventories in this README or the website. Edit the authored JSON under `data/`, then regenerate the derived files.

## Repository layout

```text
data/        canonical entries, taxonomies, tools, and source registry
schema/      JSON Schemas for entries and capabilities
scripts/     validation and deterministic generators
site/        static search interface and generated catalogs
tests/       repository integrity tests
docs/        architecture notes and roadmap
```

See [the data model](docs/DATA_MODEL.md) for field semantics and cross-tool relationship rules, and [the website architecture](docs/WEBSITE.md) for generated routes and search behavior.

## Local development

```bash
python -m pip install -r requirements.txt
python scripts/validate.py
python -m unittest discover -s tests
node --check site/app.js
node tests/test_site_search.js
python scripts/build_catalog.py
python -m http.server 8000 --directory site
```

Open `http://localhost:8000`. To check that registered official URLs still resolve, run `python scripts/check_sources.py`; this optional check requires internet access.

The `Publish Atlas website` workflow validates and regenerates `site/` before deploying it to GitHub Pages. See [the website architecture](docs/WEBSITE.md#publishing) for publishing requirements.

## Contributing entries

1. Choose the file for the relevant ecosystem under `data/<tool>/`.
2. Verify behavior against an official source.
3. Add or update the structured entry, including maturity, availability, source, and verification metadata.
4. Add capability mappings only after comparing semantics, not names.
5. Run validation, tests, and the catalog generator.
6. Include generated output changes in the same pull request.

Read [CONTRIBUTING.md](CONTRIBUTING.md) for detailed requirements.

## Project status

The atlas now covers interactive commands, nested subcommands, CLI flags, configuration, environment variables, shortcuts, hooks, permissions, MCP, skills, and agent controls across all five ecosystems. It remains a living reference rather than a claim that fast-changing vendor surfaces can ever be permanently complete. See [the roadmap](docs/ROADMAP.md).
