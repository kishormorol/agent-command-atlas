const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const entries = JSON.parse(fs.readFileSync(path.join(root, "site/catalog.json"), "utf8"));
const tools = JSON.parse(fs.readFileSync(path.join(root, "site/tools.json"), "utf8"));
const categories = JSON.parse(fs.readFileSync(path.join(root, "site/categories.json"), "utf8"));
const capabilities = JSON.parse(fs.readFileSync(path.join(root, "site/capabilities.json"), "utf8"));
const app = fs.readFileSync(path.join(root, "site/app.js"), "utf8").replace(/\ninit\(\);\s*$/, "");

const context = {
  URL,
  URLSearchParams,
  location: { search: "", pathname: "/" },
  testEntries: entries,
  testTools: tools,
  testCategories: categories,
  testCapabilities: capabilities,
};
vm.runInNewContext(`${app}
  state.entries = testEntries;
  state.tools = new Map(testTools.map((tool) => [tool.id, tool]));
  state.categories = new Map(testCategories.map((category) => [category.id, category]));
  state.capabilities = testCapabilities;
  state.entriesById = new Map(testEntries.map((entry) => [entry.id, entry]));
  prepareSearchIndex();
  globalThis.testSearch = (q, filters = {}) => filteredEntries({ q, tool: "", type: "", category: "", maturity: "", ...filters });
  globalThis.testHomeMarkup = homeView();
  globalThis.testEntryMarkup = entryCard(testEntries[0]);
  globalThis.testCapabilityMarkup = capabilityCard(testCapabilities[0]);
  globalThis.testCoverageMarkup = coverageView();
  globalThis.testDetailMarkup = detailView(testEntries[0].id);
  globalThis.testDetailCoverage = testEntries.map((entry) => ({ id: entry.id, markup: detailView(entry.id) }));
`, context);

const compactIds = new Set(context.testSearch("compact").slice(0, 6).map((entry) => entry.id));
for (const entryId of [
  "codex.slash-command.compact",
  "claude-code.slash-command.compact",
  "gemini-cli.slash-command.compress",
  "cursor.slash-command.summarize",
  "github-copilot.slash-command.compact",
]) {
  assert(compactIds.has(entryId), `compact search should surface ${entryId}`);
}

const resumeTools = new Set(context.testSearch("resume old session").slice(0, 9).map((entry) => entry.tool));
assert.deepEqual(resumeTools, new Set(["codex", "claude-code", "gemini-cli", "cursor", "github-copilot"]));

const copilotPermissionResults = context.testSearch("show all github copilot permission commands").slice(0, 8);
assert(copilotPermissionResults.length > 0);
assert(copilotPermissionResults.every((entry) => entry.tool === "github-copilot"));
assert(copilotPermissionResults.some((entry) => entry.category === "permissions"));

const conditionalClaude = context.testSearch("", { tool: "claude-code", maturity: "conditional" });
assert(conditionalClaude.length > 0);
assert(conditionalClaude.every((entry) => entry.tool === "claude-code" && entry.maturity === "conditional"));

const experimentalCopilot = context.testSearch("", { tool: "github-copilot", maturity: "experimental" });
assert(experimentalCopilot.length > 0);
assert(experimentalCopilot.every((entry) => entry.tool === "github-copilot" && entry.maturity === "experimental"));

const configuration = context.testSearch("", { type: "configuration" });
assert(configuration.length > 0);
assert(configuration.every((entry) => ["config", "config-file", "config-option", "instruction-file", "environment-variable"].includes(entry.type)));

assert(context.testHomeMarkup.includes('class="hero__content"'));
assert(context.testHomeMarkup.includes('class="hero__command-palette"'));
assert(context.testHomeMarkup.includes('class="atlas-stats"'));
assert(context.testHomeMarkup.includes(`${entries.length}</dt><dd>reference entries`));
assert(context.testHomeMarkup.includes('data-query="compact context"'));
assert(app.includes('addEventListener("search", update)'));
assert(app.includes('addEventListener("change", update)'));
assert(app.includes('addEventListener("submit"'));
assert(context.testEntryMarkup.includes(`entry-card--${entries[0].tool}`));
assert(context.testEntryMarkup.includes('class="entry-card__identity"'));
assert(context.testEntryMarkup.includes('class="entry-card__title"'));
assert(context.testEntryMarkup.includes("Open reference"));
assert(context.testCapabilityMarkup.includes('class="capability-card__top"'));
assert(context.testCapabilityMarkup.includes('class="capability-card__coverage"'));
assert(context.testCoverageMarkup.includes('class="coverage-grid"'));
assert(context.testCoverageMarkup.includes("Dataset coverage, not vendor completeness"));
for (const tool of tools) {
  assert(context.testCoverageMarkup.includes(tool.name), `coverage should include ${tool.name}`);
}
assert(context.testCoverageMarkup.includes(`${entries.length}</strong><span>Total records`));
assert(context.testCoverageMarkup.includes("Officially documented"));
assert(context.testDetailMarkup.includes("quick-tutorial"));
assert(context.testDetailMarkup.includes("Quick tutorial"));
assert(context.testDetailMarkup.includes('class="copy-example"'));
assert(context.testDetailMarkup.includes("Guidelines"));
for (const detail of context.testDetailCoverage) {
  assert(detail.markup.includes("Quick tutorial"), `${detail.id} should include a tutorial`);
  assert(detail.markup.includes('class="copy-example"'), `${detail.id} should include a copy-ready example`);
  assert(detail.markup.includes("Guidelines"), `${detail.id} should include usage guidelines`);
}

console.log("Website search and filter behavior: valid");
