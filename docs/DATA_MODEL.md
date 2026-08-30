# Data Model

The JSON files under `data/` are the canonical source for the website and cross-tool atlas.

## Entry identity

Every entry uses a stable ID: `<tool>.<type>.<slug>`. The first segment must match both `tool` and the containing directory; the second must match `type`. IDs are references and should not be renamed casually.

`name` is the literal command or control, while `display_name` is a short human-readable label. `type` describes the product surface (`slash-command`, `cli-subcommand`, `config-file`, `config-option`, `shortcut`, and so on). `category` groups related entries for browsing. These concepts are intentionally separate. Use `config` only for a configuration surface that is neither a file nor an individual option; prefer the precise types for new records.

## Description and usage

`role` is a compact functional label. `description` answers what the entry is and does. Syntax is an array because one control can have multiple valid forms. Examples distinguish minimal, practical, and workflow invocations.

`when_to_use` and `when_not_to_use` record decision guidance. `related_commands` stores stable entry IDs. A nested command can use `parent_id` while retaining its own searchable record.

## Status and availability

`maturity` uses one of: `stable`, `experimental`, `rolling-out`, `conditional`, `deprecated`, `removed`, or `unknown`. When a control is superseded, `version.replacement` records the documented replacement without requiring it to be an Atlas ID.

`availability` describes channels, platforms, plans, and free-text conditions. Version milestones belong in `version`; verification method, tested version, and date belong in `verification`. These fields are separate because a stable feature can still have conditional availability, and an officially documented feature may not have been manually tested.

## Sources

Every entry has at least one source registered for its tool in `data/sources.json`. The registry is both an authority allowlist and a concise description of what each page supports. Normal validation checks source fields and registry membership; `scripts/check_sources.py` performs the optional network-resolution check.

## Capability graph

`data/capabilities.json` defines vendor-neutral tasks such as `context.compact` and `session.resume`. Every capability includes exactly one mapping for each supported tool. A mapping points to a concrete entry when one is known and classifies the relationship as `exact`, `similar`, `partial`, `none`, or `unknown`.

`none` is an evidence-backed conclusion. `unknown` is the safe default when research or dataset coverage is incomplete. This prevents absence from the starter dataset from being mistaken for absence from the product.

## Generated outputs

`scripts/build_catalog.py` creates the static website JSON and route files. Generated files are checked in for simple static hosting and reviewable diffs, but must never become an independent source of truth.
