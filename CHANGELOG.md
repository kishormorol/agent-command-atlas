# Changelog

All notable project changes are documented here.

## Unreleased

### Added

- Meta Muse Code as a sixth covered ecosystem, with 154 official-source-backed records spanning CLI commands and flags, slash commands, shortcuts, bundled skills, permissions and sandbox modes, subagents and observers, workflows, hooks, MCP, configuration, instruction files, and environment variables.
- Muse Code mappings for all 33 cross-tool capabilities, including honest `none` and `unknown` records for code review, Git diff, remote control, plugin management, and agent definitions.
- Expanded the canonical dataset from 508 to more than 2,200 official-source-backed records across all five ecosystems.
- Complete documented flag, environment-variable, configuration-option, hook-event, shortcut, and structured-control families found in the current official references.
- Structured entries for agents, skills, plugins and extensions, MCP, permission modes, sandbox controls, and project instruction surfaces.
- Eight task capabilities covering hook and plugin management, agent and skill definitions, sandboxing, session naming, usage inspection, and configuration inspection.

### Changed

- Widened the capability schema from five to six per-tool mappings and registered Muse Code in the entry schema, validator, source registry, and website tool palette.
- Improved usage guidance for every command-like entry and expanded copy-ready examples throughout the catalog.
- Ranked primary capability implementations above incidental configuration matches in task-oriented website searches.
- Preserved stable clean command URLs when multiple record types share a slug, while generating compatibility aliases for older type-prefixed URLs.
- Extended generated command pages and comparison pages to cover the larger reference catalog.

### Fixed

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
