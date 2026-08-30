# Website Architecture

The Atlas website is a dependency-free static application. It deliberately uses the generated catalog instead of maintaining command facts in frontend code.

```text
data/ → scripts/validate.py → scripts/build_catalog.py → site/
```

## Authored and generated files

The authored website files are:

- `site/index.html`
- `site/app.js`
- `site/styles.css`

The catalog generator writes the JSON files in `site/` and the static route directories under `site/<tool>/` and `site/compare/`. Do not edit those generated route pages directly. Each route page is a small application shell with route-specific title and description metadata; command facts are still loaded from `site/catalog.json`.

## Routes

The generator assigns every entry a deterministic `path` in the website catalog. A command uses the shortest normalized name that is unique within its tool, such as `codex/compact/`. If two controls normalize to the same name, the entry type is included in the path. The build fails rather than silently emitting a duplicate route.

Generated routes include:

- one landing page per tool;
- one detail page per catalog entry;
- the comparison index;
- one comparison page per capability.

`site/routes.json` is the generated route manifest and is checked by the repository test suite.

## Search

Search indexes each entry once after the static JSON loads. Fields are weighted so names and aliases rank above capability descriptions, tool/category metadata, prose, and examples. A small vendor-neutral synonym set handles common task wording such as “resume old session” without encoding command inventories in JavaScript.

Capability search joins `capabilities.json` to catalog entries at runtime. Cross-tool relationships therefore remain sourced from the canonical capability graph.

The browser renders at most 24 results initially and adds more on request. This keeps DOM size bounded as the catalog grows, while filtering and ranking remain local and immediate.

## Accessibility and resilience

The interface uses labeled native form controls, semantic landmarks, a skip link, visible focus states, an `aria-live` result count, keyboard search focus with `/`, and responsive card/table layouts. Optional record sections are omitted when data is absent.

Run the site locally with:

```bash
python scripts/build_catalog.py
python -m http.server 8000 --directory site
```

Then open `http://localhost:8000`.

## Publishing

`.github/workflows/pages.yml` validates and regenerates the website before uploading `site/` as a GitHub Pages artifact. Its deployment job publishes only after the build job succeeds. The workflow runs on pushes to `main` and can also be started manually.

GitHub Pages must use **GitHub Actions** as its publishing source. Pages sites are public by default even when their source repository is private, and private-repository support depends on the repository owner's GitHub plan.
