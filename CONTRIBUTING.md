# Contributing

Agent Command Atlas prioritizes accuracy over volume. A smaller official-source-backed contribution is more useful than a large inferred inventory.

## Before editing

1. Read [the data model](docs/DATA_MODEL.md).
2. Find the current official documentation or official source repository.
3. Check the existing tool file, related entries, and capability mappings.
4. Confirm whether the feature is stable, experimental, rolling out, conditional, deprecated, or removed.

## Entry requirements

- Use a stable ID in the form `<tool>.<type>.<slug>`.
- Make `tool` match the containing `data/<tool>/` directory.
- Use a registered `type`, `category`, and `maturity` value.
- Explain the entry's role and behavior in original, concise language.
- Include at least one syntax form and one minimal example for commands and controls.
- Record constraints in `availability.conditions` rather than hiding them in prose.
- Link every entry to a URL registered for that tool in `data/sources.json`.
- Record the verification method and ISO date.
- Use `parent_id` for a nested subcommand that deserves its own searchable entry.
- Reference related entries by ID; the validator rejects broken references.

Do not invent missing behavior. Use `needs-verification`, `unverified`, `unknown`, or a null capability mapping when official material does not support a stronger claim.

## Cross-tool mappings

Capability mappings compare each implementation with a vendor-neutral task:

- `exact`: implements the defined capability without a material semantic gap;
- `similar`: pursues the same outcome with a meaningful behavioral difference;
- `partial`: implements only part of the capability;
- `none`: official research supports that no corresponding control exists;
- `unknown`: research or dataset coverage is not yet sufficient.

Never classify commands as exact equivalents merely because their names match. Each capability in `data/capabilities.json` must include one mapping for every supported tool.

## Official sources

Prefer, in order:

1. official product documentation;
2. official source repositories;
3. official release notes;
4. a clearly described manual test when documentation is incomplete.

Register new authoritative pages in `data/sources.json`. Do not use third-party blogs as authority when an official source exists, and do not copy long passages from vendor documentation.

## Validation and generated files

Run all checks before opening a pull request:

```bash
python scripts/validate.py
python -m unittest discover -s tests
python scripts/build_catalog.py
git diff --check
git diff --exit-code -- site/catalog.json site/capabilities.json site/categories.json site/tools.json
```

The last command should be run after generation; no output means generated files are current. The optional network check `python scripts/check_sources.py` verifies that registered official URLs still resolve.

Do not edit files under `site/*.json` or generated `site/<tool>/` and `site/compare/` route directories by hand.
