# Changelog

All notable project changes are documented here.

## Unreleased

### Added

- A validated GitHub Pages workflow that publishes the generated `site/` directory from `main`.
- Deterministic static routes for tools, commands, and capability comparisons, plus route-integrity tests and website architecture documentation.
- Strict entry and capability schemas with maturity, availability, role, description, examples, parent-command, and capability fields.
- Canonical category and vendor-neutral capability taxonomies.
- Five-tool capability mappings with exact, similar, partial, none, and unknown relationship states.
- Generated website manifests and reference routes.
- Repository integrity tests, optional official-source URL checks, and GitHub Actions validation.
- A task-first cross-tool capability atlas spanning all five ecosystems.

### Changed

- Redesigned the reference website with a command-console visual system, task shortcuts, a filter rail, denser results, responsive layouts, and route-specific social metadata.
- Upgraded the website with task-aware ranked search, combined filters, compact paginated cards, full command details, tool landing pages, and capability comparisons.
- Expanded and clarified the official-source-backed starter dataset across all five supported ecosystems.
- Corrected Claude Code interactive sources to the current official command reference.
- Clarified Gemini CLI `@` as file and directory context inclusion rather than a generic command family.
- Upgraded the static website with tool, type, category, and maturity filters plus richer result details.
- Expanded README, contribution guidance, and architecture documentation.
- Improved generated command pages with stable anchors, precise control types, conditional sections, availability details, and version or replacement notes.

### Fixed

- Validation now catches malformed JSON, duplicate IDs, names, aliases, and examples; inconsistent folder/tool/type IDs; unknown categories and capabilities; broken cross-references; and unregistered source URLs.
