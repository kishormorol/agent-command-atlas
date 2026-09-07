# Changelog

All notable project changes are documented here.

## Unreleased

### Added

- Cursor's five documented proxy, TLS, and XDG environment variables (`XDG_CONFIG_HOME`, `HTTP_PROXY`, `HTTPS_PROXY`, `NODE_USE_ENV_PROXY`, `NODE_EXTRA_CA_CERTS`), which the configuration reference lists but the dataset had never captured.
- Cursor's `&` prefix command for handing a conversation to a Cloud Agent, the first prefix-command record for an ecosystem that previously had none.

### Fixed

- Removed two Cursor `config-option` records, `Global` and `Project`, that were scrape artifacts of the configuration page's scope table rather than options. Both paths are already recorded correctly as `config-file` entries.
- Recorded the five Gemini CLI entries verified against both the official reference and the 0.58.0 binary as `officially-documented` rather than `manually-tested`, matching the convention already used by the other 176 entries carrying both kinds of evidence. `manually-tested` is now reserved for the two Cursor flags whose only remaining evidence is a binary run, because the vendor parameter reference no longer lists them.

## [0.2.0] - 2026-09-06

### Added

- Meta Muse Code as a sixth covered ecosystem, with 154 official-source-backed records spanning CLI commands and flags, slash commands, shortcuts, bundled skills, permissions and sandbox modes, subagents and observers, workflows, hooks, MCP, configuration, instruction files, and environment variables.
- Muse Code mappings for all 33 cross-tool capabilities, including honest `none` records for code review, Git diff, remote control, plugin management, and agent definitions.
- Expanded the canonical dataset from 508 to more than 2,500 official-source-backed records across all six ecosystems.
- Nested CLI command trees for every ecosystem with an inspectable binary: `claude mcp` and `claude plugin`; `codex mcp`, `plugin`, `features`, `cloud` and `login`; `gemini mcp`, `extensions`, `skills` and `gemma`; and `copilot mcp`, `plugin` and `skill`.
- Complete documented flag, environment-variable, configuration-option, hook-event, shortcut, and structured-control families found in the current official references.
- Structured entries for agents, skills, plugins and extensions, MCP, permission modes, sandbox controls, and project instruction surfaces.
- Eight task capabilities covering hook and plugin management, agent and skill definitions, sandboxing, session naming, usage inspection, and configuration inspection.

### Changed

- Verified entries against the shipping binaries for Claude Code 2.1.261, Codex 0.151.0, Gemini CLI 0.58.0, GitHub Copilot CLI 1.0.83, and Cursor 2026.09.02-c22c1a3, recording a tested version on every entry the sweeps touched.
- Resolved every unknown capability mapping. All 198 mappings across 33 capabilities and six tools are now exact, similar, partial, or an evidence-backed none.
- Widened the capability schema from five to six per-tool mappings and registered Muse Code in the entry schema, validator, source registry, and website tool palette.
- Improved usage guidance for every command-like entry and expanded copy-ready examples throughout the catalog.
- Ranked primary capability implementations above incidental configuration matches in task-oriented website searches.
- Preserved stable clean command URLs when multiple record types share a slug, while generating compatibility aliases for older type-prefixed URLs.
- Extended generated command pages and comparison pages to cover the larger reference catalog.

### Fixed

- Recorded controls that the vendor documentation still lists but the shipping binary no longer has: `gemini update`, `--experimental-zed-integration`, and Cursor's `--background` and `--fullscreen` are marked removed, and `--experimental-acp` deprecated in favour of `--acp`.
- Corrected `codex cloud` to experimental, matching both its documentation and the binary, and recorded its `codex cloud-tasks` alias.
- Taught the validator that a `none` or `unknown` capability mapping cannot contradict a tool's own entries declaring that capability, and that short CLI flags are case-sensitive.
- Made static route metadata generation safe for literal backslashes in documented syntax and examples.
- Added regression coverage for route collisions and metadata containing regular-expression replacement characters.

## [0.1.0] - 2026-08-30

### Added

- A validated GitHub Pages workflow that publishes the generated `site/` directory from `main`.
- Deterministic static routes for tools, commands, and capability comparisons, plus route-integrity tests and website architecture documentation.
- Strict entry and capability schemas with maturity, availability, role, description, examples, parent-command, and capability fields.
- Canonical category and vendor-neutral capability taxonomies.
- Five-tool capability mappings with exact, similar, partial, none, and unknown relationship states.
- Generated website manifests and reference routes.
- Repository integrity tests, optional official-source URL checks, and GitHub Actions validation.
- A task-first cross-tool capability atlas spanning all five ecosystems.
- A generated coverage dashboard with per-tool record, verification, lifecycle, type, and category summaries.
- Copy-ready examples, concise tutorials, and usage guidelines on every generated reference page.
- Current Gemini nested agent, command, MCP, memory, model, permission, plan, skill, statistics, and tool controls.
- Current Claude Code session handoff, remote-control, terminal, theme, keybinding, feedback, and account controls.
- Current GitHub Copilot CLI skill, permission, limit, remote-session, parallel-agent, terminal, account, voice, and CLI command families.

### Changed

- Redesigned the reference website with a command-console visual system, task shortcuts, a filter rail, denser results, responsive layouts, and route-specific social metadata.
- Upgraded the website with task-aware ranked search, combined filters, compact paginated cards, full command details, tool landing pages, and capability comparisons.
- Expanded and clarified the official-source-backed starter dataset across all five supported ecosystems.
- Corrected Claude Code interactive sources to the current official command reference.
- Clarified Gemini CLI `@` as file and directory context inclusion rather than a generic command family.
- Upgraded the static website with tool, type, category, and maturity filters plus richer result details.
- Expanded README, contribution guidance, and architecture documentation.
- Improved generated command pages with stable anchors, precise control types, conditional sections, availability details, and version or replacement notes.
- Expanded the canonical dataset from 342 to 401 official-source-backed records and the capability atlas from 22 to 25 tasks.
- Reclassified cross-tool context, diff, instruction, mode, session, parallel-agent, side-question, and remote-control relationships using evidence-backed semantics.

### Fixed

- Validation now catches malformed JSON, duplicate IDs, names, aliases, and examples; inconsistent folder/tool/type IDs; unknown categories and capabilities; broken cross-references; and unregistered source URLs.
