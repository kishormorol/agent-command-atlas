const state = {
  entries: [],
  capabilities: [],
  tools: new Map(),
  categories: new Map(),
  entriesById: new Map(),
  capabilitiesByEntry: new Map(),
  primaryCapabilitiesByEntry: new Map(),
  visibleLimit: 24,
};

const TYPE_GROUPS = {
  configuration: new Set(["config", "config-file", "config-option", "instruction-file", "environment-variable"]),
};

const SEARCH_SYNONYMS = {
  agent: ["agents", "subagent", "subagents"],
  agents: ["agent", "subagent", "subagents"],
  auth: ["authenticate", "authentication", "login", "credentials"],
  change: ["select", "switch", "configure"],
  command: ["control", "flag", "shortcut"],
  compact: ["compress", "summarize", "summary", "context"],
  context: ["conversation", "chat", "tokens"],
  old: ["earlier", "previous", "saved", "history", "resume"],
  permission: ["permissions", "approval", "sandbox", "trust", "access"],
  model: ["models", "llm", "select", "switch", "provider"],
  models: ["model", "llm", "select", "switch", "provider"],
  resume: ["continue", "restore", "previous", "history"],
  session: ["conversation", "chat", "thread"],
  shell: ["terminal", "execute", "command", "process"],
};

const STOP_WORDS = new Set(["a", "all", "an", "and", "commands", "does", "features", "for", "have", "how", "is", "of", "show", "the", "to", "what", "which", "with"]);
const MATURITY_ORDER = ["stable", "experimental", "rolling-out", "conditional", "deprecated", "removed", "unknown"];
const $ = (selector, root = document) => root.querySelector(selector);

function escapeHtml(value = "") {
  return String(value).replace(/[&<>\"]/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;",
  })[character]);
}

function label(value = "") {
  return String(value).replaceAll("-", " ").replace(/\b\w/g, (character) => character.toUpperCase());
}

function normalize(value = "") {
  return String(value).toLowerCase().replace(/[^a-z0-9@!/+.-]+/g, " ").trim();
}

function toolName(toolId) {
  return state.tools.get(toolId)?.name || label(toolId);
}

function categoryName(categoryId) {
  return state.categories.get(categoryId)?.display_name || label(categoryId);
}

function sourceHost(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return "Official documentation";
  }
}

function routeHref(path = "") {
  return escapeHtml(path);
}

function verificationLabel(status) {
  return {
    "officially-documented": "Officially documented",
    "manually-tested": "Manually tested",
    "community-verified": "Community verified",
    "needs-verification": "Needs verification",
    unverified: "Unverified",
  }[status] || label(status);
}

function relationshipLabel(relationship) {
  return relationship === "none" ? "No mapped control" : label(relationship);
}

function entryCapabilities(entry) {
  return state.capabilitiesByEntry.get(entry.id) || [];
}

function prepareSearchIndex() {
  state.capabilitiesByEntry = new Map();
  state.primaryCapabilitiesByEntry = new Map();
  state.capabilities.forEach((capability) => {
    capability.mappings.forEach((mapping) => {
      if (!mapping.entry_id) return;
      const rows = state.capabilitiesByEntry.get(mapping.entry_id) || [];
      rows.push(capability);
      state.capabilitiesByEntry.set(mapping.entry_id, rows);
      const primaryRows = state.primaryCapabilitiesByEntry.get(mapping.entry_id) || [];
      primaryRows.push(capability);
      state.primaryCapabilitiesByEntry.set(mapping.entry_id, primaryRows);
    });
  });

  const capabilitiesById = new Map(state.capabilities.map((capability) => [capability.id, capability]));
  state.entries.forEach((entry) => {
    const rows = state.capabilitiesByEntry.get(entry.id) || [];
    (entry.capabilities || []).forEach((capabilityId) => {
      const capability = capabilitiesById.get(capabilityId);
      if (capability && !rows.includes(capability)) rows.push(capability);
    });
    if (rows.length) state.capabilitiesByEntry.set(entry.id, rows);
  });

  state.entries.forEach((entry) => {
    const capabilities = entryCapabilities(entry);
    const primaryCapabilities = state.primaryCapabilitiesByEntry.get(entry.id) || [];
    entry._searchFields = [
      { text: normalize([entry.name, entry.display_name, ...(entry.aliases || []), ...(entry.syntax || [])].join(" ")), weight: 12 },
      { text: normalize(primaryCapabilities.flatMap((item) => [item.id, item.display_name, item.description]).join(" ")), weight: 24 },
      { text: normalize(capabilities.flatMap((item) => [item.id, item.display_name, item.description]).join(" ")), weight: 10 },
      { text: normalize([toolName(entry.tool), state.tools.get(entry.tool)?.vendor, entry.type, categoryName(entry.category), entry.role].join(" ")), weight: 6 },
      { text: normalize([entry.description, ...(entry.when_to_use || []), ...(entry.when_not_to_use || [])].join(" ")), weight: 4 },
      { text: normalize((entry.examples || []).flatMap((item) => [item.command, item.explanation]).join(" ")), weight: 3 },
      { text: normalize([...(entry.notes || []), ...(entry.availability?.conditions || [])].join(" ")), weight: 2 },
    ];
  });
}

function queryGroups(query) {
  return [...new Set(normalize(query).split(/\s+/).filter((term) => term && !STOP_WORDS.has(term)))]
    .map((term) => [...new Set([term, ...(SEARCH_SYNONYMS[term] || [])])]);
}

function searchScore(entry, query) {
  const groups = queryGroups(query);
  if (!groups.length) return 1;
  let matchedGroups = 0;
  let score = 0;
  groups.forEach((variants) => {
    let groupScore = 0;
    entry._searchFields.forEach((field) => {
      variants.forEach((variant, index) => {
        const synonymFactor = index === 0 ? 1 : 0.55;
        if (field.text.includes(variant)) groupScore = Math.max(groupScore, field.weight * synonymFactor);
      });
    });
    if (groupScore) {
      matchedGroups += 1;
      score += groupScore;
    }
  });
  if (!matchedGroups) return 0;
  const coverage = matchedGroups / groups.length;
  const normalizedQuery = normalize(query);
  const normalizedName = normalize(entry.name).replace(/^[^a-z0-9]+/, "");
  const exactName = normalizedName === normalizedQuery || normalize(entry.display_name) === normalizedQuery;
  return score * coverage + (exactName ? 30 : 0);
}

function capabilityScore(capability, query) {
  const groups = queryGroups(query);
  if (!groups.length) return 0;
  const mappingText = capability.mappings.flatMap((mapping) => {
    const entry = mapping.entry_id ? state.entriesById.get(mapping.entry_id) : null;
    return [mapping.notes, entry?.name, toolName(mapping.tool)];
  });
  const text = normalize([capability.id, capability.display_name, capability.description, ...mappingText].join(" "));
  const matched = groups.filter((variants) => variants.some((variant) => text.includes(variant))).length;
  return matched ? matched / groups.length : 0;
}

function option(value, text, selectedValue) {
  return `<option value="${escapeHtml(value)}"${value === selectedValue ? " selected" : ""}>${escapeHtml(text)}</option>`;
}

function currentFilters(toolId = "") {
  const params = new URLSearchParams(location.search);
  return {
    q: params.get("q") || "",
    tool: toolId || params.get("tool") || "",
    type: params.get("type") || "",
    category: params.get("category") || "",
    maturity: params.get("maturity") || "",
  };
}

function toolLinks(activeTool = "") {
  return `<nav class="tool-tabs" aria-label="Browse by tool">
    <a class="tool-tab${activeTool ? "" : " is-active"}" href=""><span class="tool-tab__dot" aria-hidden="true"></span>All tools</a>
    ${[...state.tools.values()].map((tool) => `<a class="tool-tab tool-tab--${escapeHtml(tool.id)}${activeTool === tool.id ? " is-active" : ""}" href="${routeHref(`${tool.id}/`)}"><span class="tool-tab__dot" aria-hidden="true"></span>${escapeHtml(tool.name.replace("OpenAI ", "").replace("GitHub ", ""))}</a>`).join("")}
  </nav>`;
}

function searchBox(filters) {
  return `<form class="search" role="search" id="search-form">
    <label for="q">Search the Atlas</label>
    <div class="search__input-wrap">
      <span aria-hidden="true">⌕</span>
      <input id="q" name="q" type="search" value="${escapeHtml(filters.q)}" placeholder="Search commands, flags, tasks, tools…" autocomplete="off" spellcheck="false">
      <kbd aria-label="Keyboard shortcut: slash">/</kbd>
    </div>
    <p class="search-hint">Type naturally—results update as you type. Try <button class="search-hint__link" type="button" data-query="model">model</button> or <button class="search-hint__link" type="button" data-query="compact context">compact context</button>.</p>
  </form>`;
}

function filterPanel(filters, fixedTool = "") {
  const entryTypes = [...new Set(state.entries.map((entry) => entry.type))].sort((a, b) => label(a).localeCompare(label(b)));
  const typeOptions = [option("", "All types", filters.type), option("configuration", "Configuration (all)", filters.type)]
    .concat(entryTypes.map((type) => option(type, label(type), filters.type)));
  const categoryOptions = [option("", "All categories", filters.category)]
    .concat([...state.categories.values()].map((category) => option(category.id, category.display_name, filters.category)));
  const maturityOptions = [option("", "All maturity states", filters.maturity)]
    .concat(MATURITY_ORDER.filter((value) => state.entries.some((entry) => entry.maturity === value)).map((value) => option(value, label(value), filters.maturity)));
  const toolField = fixedTool ? "" : `<label class="field" for="tool"><span>Tool</span><select id="tool">${[option("", "All tools", filters.tool), ...[...state.tools.values()].map((tool) => option(tool.id, tool.name, filters.tool))].join("")}</select></label>`;
  return `<aside class="filter-panel" aria-label="Reference filters">
    <div class="filter-panel__head"><div><p class="eyebrow">Refine</p><h3>Filter reference</h3></div><span aria-hidden="true">⌘</span></div>
    ${toolField}
    <label class="field" for="type"><span>Type</span><select id="type">${typeOptions.join("")}</select></label>
    <label class="field" for="category"><span>Category</span><select id="category">${categoryOptions.join("")}</select></label>
    <label class="field" for="maturity"><span>Maturity</span><select id="maturity">${maturityOptions.join("")}</select></label>
    <button class="button button--quiet" id="reset" type="button">Clear filters</button>
  </aside>`;
}

function maturityBadge(entry) {
  if (entry.maturity === "stable") return "";
  return `<span class="badge badge--${escapeHtml(entry.maturity)}">${escapeHtml(label(entry.maturity))}</span>`;
}

function entryCard(entry) {
  const example = (entry.examples || []).find((item) => item.level === "practical") || (entry.examples || [])[0];
  const titleId = `entry-${escapeHtml(entry.id)}`;
  return `<article class="entry-card entry-card--${escapeHtml(entry.tool)}" aria-labelledby="${titleId}">
    <div class="entry-card__identity">
      <div class="entry-card__meta">
        <span class="entry-card__tool"><i aria-hidden="true"></i>${escapeHtml(toolName(entry.tool))}</span>
        <span>${escapeHtml(label(entry.type))}</span>
        <span>${escapeHtml(categoryName(entry.category))}</span>
        ${maturityBadge(entry)}
      </div>
      <div class="entry-card__title"><h3 id="${titleId}"><a href="${routeHref(entry.path)}"><code>${escapeHtml(entry.name)}</code></a></h3><span>${escapeHtml(entry.display_name)}</span></div>
      <p class="entry-card__role">${escapeHtml(entry.role)}</p>
    </div>
    <div class="entry-card__usage">
      <div><span>Syntax</span><code>${escapeHtml(entry.syntax[0])}</code></div>
      ${example ? `<div><span>Example</span><code>${escapeHtml(example.command)}</code></div>` : ""}
    </div>
    <div class="entry-card__footer">
      <span class="verification verification--${escapeHtml(entry.verification.status)}">${escapeHtml(verificationLabel(entry.verification.status))}</span>
      <a href="${routeHref(entry.path)}" aria-label="Open the reference for ${escapeHtml(entry.name)}">Open reference <span aria-hidden="true">↗</span></a>
    </div>
  </article>`;
}

function capabilityCard(capability) {
  const mapped = capability.mappings.filter((mapping) => mapping.entry_id).length;
  return `<a class="capability-card" href="${routeHref(capability.path)}">
    <span class="capability-card__top"><span class="capability-card__id">${escapeHtml(capability.id)}</span><span aria-hidden="true">↗</span></span>
    <strong>${escapeHtml(capability.display_name)}</strong>
    <span>${escapeHtml(capability.description)}</span>
    <span class="capability-card__footer"><span class="capability-card__coverage" aria-label="${mapped} of 5 tools mapped">${capability.mappings.map((mapping) => `<i class="${mapping.entry_id ? "is-mapped" : ""}" aria-hidden="true"></i>`).join("")}</span><small>${mapped}/5 mapped</small></span>
  </a>`;
}

function matchesType(entry, type) {
  return !type || entry.type === type || TYPE_GROUPS[type]?.has(entry.type);
}

function filteredEntries(filters) {
  return state.entries.map((entry) => ({ entry, score: searchScore(entry, filters.q) }))
    .filter(({ entry, score }) => score > 0
      && (!filters.tool || entry.tool === filters.tool)
      && matchesType(entry, filters.type)
      && (!filters.category || entry.category === filters.category)
      && (!filters.maturity || entry.maturity === filters.maturity))
    .sort((a, b) => b.score - a.score
      || (state.tools.get(a.entry.tool)?.order || 0) - (state.tools.get(b.entry.tool)?.order || 0)
      || a.entry.name.localeCompare(b.entry.name))
    .map(({ entry }) => entry);
}

function resultsMarkup(filters) {
  const rows = filteredEntries(filters);
  const visible = rows.slice(0, state.visibleLimit);
  const taskMatches = filters.q
    ? state.capabilities.map((capability) => ({ capability, score: capabilityScore(capability, filters.q) })).filter((item) => item.score >= 0.5).sort((a, b) => b.score - a.score).slice(0, 4)
    : [];
  return `<div id="results-region">
    ${taskMatches.length ? `<aside class="task-matches" aria-labelledby="task-match-heading"><div><p class="eyebrow">Task matches</p><h2 id="task-match-heading">Compare this task across tools</h2></div><div class="task-match-links">${taskMatches.map(({ capability }) => `<a href="${routeHref(capability.path)}">${escapeHtml(capability.display_name)} <span aria-hidden="true">→</span></a>`).join("")}</div></aside>` : ""}
    <div class="results-bar">
      <p id="count" role="status" aria-live="polite"><strong>${rows.length}</strong> ${rows.length === 1 ? "entry" : "entries"}${filters.q ? ` for “${escapeHtml(filters.q)}”` : ""}</p>
      <p>Showing ${Math.min(visible.length, rows.length)} of ${rows.length}</p>
    </div>
    <section class="entry-list" aria-label="Reference entries">
      ${visible.length ? visible.map(entryCard).join("") : `<div class="empty"><h2>No entries found</h2><p>Try a broader task, remove a filter, or browse by capability.</p></div>`}
    </section>
    ${visible.length < rows.length ? `<div class="load-more"><button class="button" id="show-more" type="button">Show ${Math.min(24, rows.length - visible.length)} more</button></div>` : ""}
  </div>`;
}

function referenceSection(filters, fixedTool = "") {
  return `<section class="reference-section" aria-labelledby="reference-heading">
    <div class="section-heading section-heading--reference"><div><p class="eyebrow">Complete reference</p><h2 id="reference-heading">Commands and control surfaces</h2></div><p>Search the full verified catalog, then narrow by ecosystem, surface, task, or lifecycle.</p></div>
    <div class="reference-shell">
      ${filterPanel(filters, fixedTool)}
      <div class="reference-results">${resultsMarkup(filters)}</div>
    </div>
  </section>`;
}

function homeView() {
  const filters = currentFilters();
  const verifiedDates = state.entries.map((entry) => entry.verification.last_verified).filter(Boolean).sort();
  return `<section class="hero">
      <div class="hero__content">
        <div class="hero__copy"><p class="eyebrow">Agent Command Atlas · Verified reference</p><h1>Find the right<br><span>agent command.</span></h1><p>Search commands, flags, shortcuts, and control surfaces across Codex, Claude Code, Gemini CLI, Cursor, and GitHub Copilot CLI.</p><a class="hero__star" href="https://github.com/kishormorol/agent-command-atlas" target="_blank" rel="noreferrer"><span aria-hidden="true">★</span> Star this project on GitHub <span aria-hidden="true">↗</span></a></div>
        <div class="hero__command-palette">
          <div class="command-palette__bar"><span></span><span></span><span></span><strong>atlas / search</strong></div>
          ${searchBox(filters)}
          <div class="quick-searches" aria-label="Suggested searches"><span>Try</span><button class="quick-search" data-query="model" type="button">model</button><button class="quick-search" data-query="compact context" type="button">compact context</button><button class="quick-search" data-query="resume old session" type="button">resume session</button><button class="quick-search" data-query="configure permissions" type="button">permissions</button></div>
        </div>
      </div>
      <div class="hero__footer">
        <dl class="atlas-stats"><div><dt>${state.entries.length}</dt><dd>reference entries</dd></div><div><dt>${state.tools.size}</dt><dd>ecosystems</dd></div><div><dt>${state.capabilities.length}</dt><dd>cross-tool tasks</dd></div><div><dt>${escapeHtml(verifiedDates.at(-1) || "Undated")}</dt><dd>latest verification</dd></div></dl>
        ${toolLinks(filters.tool)}
      </div>
    </section>
    <section class="capability-section" aria-labelledby="capability-heading">
      <div class="section-heading"><div><p class="eyebrow">Cross-tool atlas</p><h2 id="capability-heading">Start with the task</h2></div><a href="compare/">Explore all ${state.capabilities.length} tasks <span aria-hidden="true">→</span></a></div>
      <div class="capability-grid">${state.capabilities.slice(0, 8).map(capabilityCard).join("")}</div>
    </section>
    ${referenceSection(filters)}`;
}

function breakdown(entries, key, getName) {
  const counts = new Map();
  entries.forEach((entry) => counts.set(entry[key], (counts.get(entry[key]) || 0) + 1));
  return [...counts.entries()].sort((a, b) => b[1] - a[1] || getName(a[0]).localeCompare(getName(b[0])));
}

function toolView(toolId) {
  const tool = state.tools.get(toolId);
  if (!tool) return notFoundView();
  const entries = state.entries.filter((entry) => entry.tool === toolId);
  const filters = currentFilters(toolId);
  const allTypes = breakdown(entries, "type", label);
  const allCategories = breakdown(entries, "category", categoryName);
  const types = allTypes.slice(0, 5);
  const categories = allCategories.slice(0, 5);
  const dates = entries.map((entry) => entry.verification.last_verified).filter(Boolean).sort();
  const sources = [...new Map(entries.flatMap((entry) => entry.sources).map((source) => [source.url, source])).values()].slice(0, 4);
  return `<div class="page-head page-head--${escapeHtml(toolId)}">
      <nav class="breadcrumbs" aria-label="Breadcrumb"><a href="">Atlas</a><span aria-hidden="true">/</span><span>${escapeHtml(tool.name)}</span></nav>
      <p class="eyebrow">Tool reference</p><h1>${escapeHtml(tool.name)} commands</h1>
      <p>Search ${entries.length} documented commands and control surfaces for ${escapeHtml(tool.name)}, derived from the canonical Atlas dataset and official ${escapeHtml(tool.vendor)} sources.</p>
      ${searchBox(filters)}
      ${toolLinks(toolId)}
    </div>
    <section class="tool-summary" aria-label="Dataset summary">
      <div class="metric"><strong>${entries.length}</strong><span>reference entries</span></div>
      <div class="metric"><strong>${allTypes.length}</strong><span>entry types</span></div>
      <div class="metric"><strong>${allCategories.length}</strong><span>categories</span></div>
      <div class="metric"><strong>${escapeHtml(dates.at(-1) || "Undated")}</strong><span>latest verification</span></div>
      <div class="summary-list"><h2>Top types</h2>${types.map(([type, count]) => `<span>${escapeHtml(label(type))}<strong>${count}</strong></span>`).join("")}</div>
      <div class="summary-list"><h2>Top categories</h2>${categories.map(([category, count]) => `<span>${escapeHtml(categoryName(category))}<strong>${count}</strong></span>`).join("")}</div>
      <div class="summary-list summary-list--sources"><h2>Official documentation</h2>${sources.map((source) => `<a href="${escapeHtml(source.url)}" target="_blank" rel="noreferrer">${escapeHtml(sourceHost(source.url))} <span aria-hidden="true">↗</span></a>`).join("")}</div>
    </section>
    ${referenceSection(filters, toolId)}`;
}

function codeList(values) {
  return `<pre><code>${values.map(escapeHtml).join("\n")}</code></pre>`;
}

function bulletSection(title, values) {
  if (!values?.length) return "";
  return `<section class="detail-section"><h2>${escapeHtml(title)}</h2><ul>${values.map((value) => `<li>${escapeHtml(value)}</li>`).join("")}</ul></section>`;
}

function tutorialSteps(entry, example) {
  const channels = (entry.availability?.channels || []).map(label).join(", ");
  const conditions = entry.availability?.conditions || [];
  const useInstruction = entry.type === "shortcut"
    ? `Focus the relevant ${channels || "interactive"} surface, then press ${example.command}.`
    : `Use the documented form: ${example.command}`;
  return [
    `Check availability${channels ? ` for ${channels}` : ""} and note the ${label(entry.maturity)} lifecycle state.`,
    useInstruction,
    `Confirm the result matches the documented role: ${entry.role}.`,
    ...(conditions.length ? [`Account for this condition: ${conditions[0]}`] : []),
  ];
}

function guidelines(entry) {
  return [
    ...(entry.when_to_use || []).map((value) => ({ label: "Use when", value })),
    ...(!(entry.when_to_use || []).length ? [{ label: "Use for", value: entry.description }] : []),
    ...(entry.when_not_to_use || []).map((value) => ({ label: "Avoid when", value })),
    ...(entry.availability?.conditions || []).map((value) => ({ label: "Check first", value })),
    ...(entry.maturity !== "stable" ? [{ label: "Lifecycle", value: `This control is ${label(entry.maturity).toLowerCase()}; confirm it is available in your installed release and account.` }] : []),
  ];
}

function relationshipTable(capability, activeEntryId = "") {
  return `<div class="comparison-table-wrap"><table class="comparison-table" aria-label="${escapeHtml(capability.display_name)} comparison">
    <thead><tr><th scope="col">Tool</th><th scope="col">Control</th><th scope="col">Relationship</th><th scope="col">Notes</th></tr></thead><tbody>
    ${capability.mappings.map((mapping) => {
      const entry = mapping.entry_id ? state.entriesById.get(mapping.entry_id) : null;
      const isActive = entry?.id === activeEntryId;
      return `<tr${isActive ? ' class="is-active"' : ""}>
        <th scope="row" data-label="Tool">${escapeHtml(toolName(mapping.tool))}</th>
        <td data-label="Control">${entry ? `<a href="${routeHref(entry.path)}"><code>${escapeHtml(entry.name)}</code></a>` : "—"}</td>
        <td data-label="Relationship"><span class="relationship relationship--${escapeHtml(mapping.relationship)}">${escapeHtml(relationshipLabel(mapping.relationship))}</span></td>
        <td data-label="Notes">${escapeHtml(mapping.notes || (isActive ? "Current entry." : "Mapped to the vendor-neutral capability."))}</td>
      </tr>`;
    }).join("")}
    </tbody></table></div>`;
}

function detailView(entryId) {
  const entry = state.entriesById.get(entryId);
  if (!entry) return notFoundView();
  const examples = entry.examples?.length ? entry.examples : [{ command: entry.syntax[0], explanation: "Use the documented form shown in the canonical Atlas entry.", level: "reference" }];
  const primaryExample = examples.find((example) => example.level === "practical") || examples[0];
  const steps = tutorialSteps(entry, primaryExample);
  const guidance = guidelines(entry);
  const related = (entry.related_commands || []).map((id) => state.entriesById.get(id)).filter(Boolean);
  const capabilities = entryCapabilities(entry);
  const availability = entry.availability || {};
  const version = entry.version || {};
  const versionRows = [["Introduced", version.introduced], ["Deprecated", version.deprecated], ["Removed", version.removed], ["Replacement", version.replacement]].filter(([, value]) => value);
  return `<article class="detail-page detail-page--${escapeHtml(entry.tool)}">
    <nav class="breadcrumbs" aria-label="Breadcrumb"><a href="">Atlas</a><span aria-hidden="true">/</span><a href="${routeHref(`${entry.tool}/`)}">${escapeHtml(toolName(entry.tool))}</a><span aria-hidden="true">/</span><span>${escapeHtml(entry.name)}</span></nav>
    <header class="detail-head">
      <div class="detail-head__meta"><span>${escapeHtml(toolName(entry.tool))}</span><span>${escapeHtml(label(entry.type))}</span><span>${escapeHtml(categoryName(entry.category))}</span>${maturityBadge(entry)}</div>
      <h1><code>${escapeHtml(entry.name)}</code></h1>
      <p class="detail-role">${escapeHtml(entry.role)}</p>
      <p>${escapeHtml(entry.description)}</p>
      ${(entry.aliases || []).length ? `<p class="aliases"><strong>Aliases:</strong> ${entry.aliases.map((alias) => `<code>${escapeHtml(alias)}</code>`).join(" ")}</p>` : ""}
    </header>
    <div class="detail-layout">
      <div class="detail-main">
        <section class="detail-section"><h2>Syntax</h2>${codeList(entry.syntax)}</section>
        <section class="detail-section"><div class="section-heading"><div><p class="eyebrow">Copy-ready</p><h2>Examples</h2></div><span class="section-note">Use only in the documented surface and availability conditions.</span></div><div class="examples">${examples.map((example) => `<div><div class="example-head"><h3>${escapeHtml(label(example.level))} example</h3><button class="copy-example" type="button" data-copy="${escapeHtml(example.command)}" aria-label="Copy example: ${escapeHtml(example.command)}">Copy</button></div><pre><code>${escapeHtml(example.command)}</code></pre><p>${escapeHtml(example.explanation)}</p></div>`).join("")}</div></section>
        <section class="detail-section quick-tutorial" aria-labelledby="tutorial-heading"><p class="eyebrow">Guided use</p><h2 id="tutorial-heading">Quick tutorial</h2><ol>${steps.map((step, index) => `<li><span>${index + 1}</span><p>${escapeHtml(step)}</p></li>`).join("")}</ol></section>
        <section class="detail-section guidelines"><h2>Guidelines</h2><dl>${guidance.map((item) => `<div><dt>${escapeHtml(item.label)}</dt><dd>${escapeHtml(item.value)}</dd></div>`).join("")}</dl></section>
        ${bulletSection("When to use", entry.when_to_use)}
        ${bulletSection("When not to use", entry.when_not_to_use)}
        ${related.length ? `<section class="detail-section"><h2>Related commands</h2><div class="related-links">${related.map((item) => `<a href="${routeHref(item.path)}"><code>${escapeHtml(item.name)}</code><span>${escapeHtml(item.display_name)}</span></a>`).join("")}</div></section>` : ""}
        ${capabilities.map((capability) => `<section class="detail-section"><div class="section-heading"><div><p class="eyebrow">Equivalent capabilities</p><h2>${escapeHtml(capability.display_name)}</h2></div><a href="${routeHref(capability.path)}">Open comparison <span aria-hidden="true">→</span></a></div><p>${escapeHtml(capability.description)}</p>${relationshipTable(capability, entry.id)}</section>`).join("")}
        ${bulletSection("Notes", entry.notes)}
      </div>
      <aside class="detail-aside" aria-label="Availability and verification">
        <section><h2>Availability</h2><dl><div><dt>Maturity</dt><dd>${escapeHtml(label(entry.maturity))}</dd></div><div><dt>Channels</dt><dd>${escapeHtml((availability.channels || []).map(label).join(", "))}</dd></div>${availability.platforms?.length ? `<div><dt>Platforms</dt><dd>${escapeHtml(availability.platforms.map(label).join(", "))}</dd></div>` : ""}${availability.plans?.length ? `<div><dt>Plans</dt><dd>${escapeHtml(availability.plans.join(", "))}</dd></div>` : ""}</dl>${availability.conditions?.length ? `<ul>${availability.conditions.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>` : ""}</section>
        ${versionRows.length ? `<section><h2>Version</h2><dl>${versionRows.map(([key, value]) => `<div><dt>${key}</dt><dd>${escapeHtml(value)}</dd></div>`).join("")}</dl></section>` : ""}
        <section><h2>Verification</h2><p class="verification verification--${escapeHtml(entry.verification.status)}">${escapeHtml(verificationLabel(entry.verification.status))}</p><dl><div><dt>Last verified</dt><dd><time datetime="${escapeHtml(entry.verification.last_verified || "")}">${escapeHtml(entry.verification.last_verified || "Not dated")}</time></dd></div>${entry.verification.tested_version ? `<div><dt>Tested version</dt><dd>${escapeHtml(entry.verification.tested_version)}</dd></div>` : ""}</dl>${entry.sources.map((source) => `<a class="official-link" href="${escapeHtml(source.url)}" target="_blank" rel="noreferrer">Official ${escapeHtml(label(source.kind))} <span aria-hidden="true">↗</span></a>`).join("")}</section>
      </aside>
    </div>
  </article>`;
}

function compareView(capabilityId = "") {
  const capability = capabilityId ? state.capabilities.find((item) => item.id === capabilityId) : null;
  if (capabilityId && !capability) return notFoundView();
  if (!capability) {
    return `<div class="page-head"><nav class="breadcrumbs" aria-label="Breadcrumb"><a href="">Atlas</a><span aria-hidden="true">/</span><span>Compare</span></nav><p class="eyebrow">Cross-tool atlas</p><h1>Compare capabilities</h1><p>Start with a developer task, then inspect each tool’s mapped control and the evidence-backed relationship. Unknown is not treated as none.</p></div>
      <section class="capability-section"><div class="capability-grid">${state.capabilities.map(capabilityCard).join("")}</div></section>`;
  }
  return `<div class="page-head"><nav class="breadcrumbs" aria-label="Breadcrumb"><a href="">Atlas</a><span aria-hidden="true">/</span><a href="compare/">Compare</a><span aria-hidden="true">/</span><span>${escapeHtml(capability.display_name)}</span></nav><p class="eyebrow">Cross-tool comparison</p><h1>${escapeHtml(capability.display_name)}</h1><p>${escapeHtml(capability.description)}</p></div>
    <section class="comparison-page"><div class="comparison-note"><strong>How to read this:</strong> relationships compare each control with the vendor-neutral task—not with a command that merely has a similar name.</div>${relationshipTable(capability)}<p class="comparison-legend"><strong>Relationship labels:</strong> Exact, Similar, Partial, None, and Unknown. Unknown means the dataset does not yet support a conclusion.</p></section>`;
}

function coverageView() {
  const officiallyDocumented = state.entries.filter((entry) => entry.verification.status === "officially-documented").length;
  const lifecycleFlagged = state.entries.filter((entry) => entry.maturity !== "stable").length;
  const mappedRelationships = state.capabilities.flatMap((capability) => capability.mappings).filter((mapping) => mapping.entry_id).length;
  const totalRelationships = state.capabilities.length * state.tools.size;
  const toolCards = [...state.tools.values()].map((tool) => {
    const entries = state.entries.filter((entry) => entry.tool === tool.id);
    const types = new Set(entries.map((entry) => entry.type)).size;
    const categories = new Set(entries.map((entry) => entry.category)).size;
    const documented = entries.filter((entry) => entry.verification.status === "officially-documented").length;
    const flagged = entries.filter((entry) => entry.maturity !== "stable").length;
    const dates = entries.map((entry) => entry.verification.last_verified).filter(Boolean).sort();
    const documentedPercent = entries.length ? Math.round((documented / entries.length) * 100) : 0;
    return `<article class="coverage-card coverage-card--${escapeHtml(tool.id)}">
      <div class="coverage-card__head"><span aria-hidden="true"></span><div><p>${escapeHtml(tool.vendor)}</p><h2><a href="${routeHref(`${tool.id}/`)}">${escapeHtml(tool.name)}</a></h2></div><strong>${entries.length}</strong></div>
      <dl><div><dt>Officially documented</dt><dd>${documentedPercent}%</dd></div><div><dt>Entry types</dt><dd>${types}</dd></div><div><dt>Categories</dt><dd>${categories}</dd></div><div><dt>Lifecycle flagged</dt><dd>${flagged}</dd></div></dl>
      <div class="coverage-meter" aria-label="${documentedPercent} percent of Atlas records for ${escapeHtml(tool.name)} are officially documented"><i style="width:${documentedPercent}%"></i></div>
      <p>Latest verification <time datetime="${escapeHtml(dates.at(-1) || "")}">${escapeHtml(dates.at(-1) || "Not dated")}</time></p>
    </article>`;
  }).join("");
  return `<div class="page-head"><nav class="breadcrumbs" aria-label="Breadcrumb"><a href="">Atlas</a><span aria-hidden="true">/</span><span>Coverage</span></nav><p class="eyebrow">Trust and scope</p><h1>Dataset coverage</h1><p>See what the canonical Atlas data contains, how it is verified, and where lifecycle caveats are recorded.</p></div>
    <section class="coverage-page" aria-labelledby="coverage-heading">
      <div class="coverage-note"><strong>Dataset coverage, not vendor completeness.</strong><span>These figures describe records currently maintained by Atlas. Vendors change quickly, and a record count is not a claim that every private, conditional, or newly released surface has been captured.</span></div>
      <h2 id="coverage-heading" class="visually-hidden">Coverage summary</h2>
      <div class="coverage-totals">
        <div><strong>${state.entries.length}</strong><span>Total records</span></div>
        <div><strong>${officiallyDocumented}</strong><span>Officially documented</span></div>
        <div><strong>${lifecycleFlagged}</strong><span>Lifecycle flagged</span></div>
        <div><strong>${mappedRelationships}/${totalRelationships}</strong><span>Capability mappings</span></div>
      </div>
      <div class="section-heading"><div><p class="eyebrow">By ecosystem</p><h2>Structured coverage at a glance</h2></div><p>Counts, breadth, verification, and non-stable lifecycle records.</p></div>
      <div class="coverage-grid">${toolCards}</div>
      <div class="coverage-method"><div><p class="eyebrow">Method</p><h2>What these numbers mean</h2></div><dl><div><dt>Officially documented</dt><dd>The entry cites official vendor documentation or an official source repository and has a verification date.</dd></div><div><dt>Lifecycle flagged</dt><dd>The entry is experimental, rolling out, conditional, deprecated, removed, or unknown instead of broadly stable.</dd></div><div><dt>Capability mapping</dt><dd>A vendor-neutral task has an evidence-backed command relationship. Unmapped does not automatically mean unsupported.</dd></div></dl></div>
    </section>`;
}

function guideView() {
  return `<div class="page-head"><nav class="breadcrumbs" aria-label="Breadcrumb"><a href="">Atlas</a><span aria-hidden="true">/</span><span>How to use</span></nav><p class="eyebrow">Quick start</p><h1>Find an answer in seconds.</h1><p>Use the Atlas when you know the task but not the vendor-specific command. Search by intent, filter the results, then open a command page for examples and verification details.</p></div>
    <section class="guide-page" aria-labelledby="guide-heading">
      <div class="section-heading"><div><p class="eyebrow">Three steps</p><h2 id="guide-heading">A simple way to use the Atlas</h2></div><p>Everything is generated from the canonical dataset and linked to official sources.</p></div>
      <div class="guide-grid">
        <article class="guide-card"><span>01</span><h2>Search by goal</h2><p>Type what you want to accomplish, not only the exact command. Try <code>model</code>, <code>resume old session</code>, or <code>compact context</code>.</p><a href="?q=model">Try a model search →</a></article>
        <article class="guide-card"><span>02</span><h2>Narrow the list</h2><p>Use tool, type, category, and maturity filters together. This is useful when you need only stable Codex flags or experimental Copilot controls.</p><a href="">Browse the full reference →</a></article>
        <article class="guide-card"><span>03</span><h2>Open the evidence</h2><p>Command pages include copy-ready syntax, minimal and practical examples, usage guidelines, lifecycle status, and a direct official source.</p><a href="compare/">Compare capabilities →</a></article>
      </div>
      <div class="guide-callout"><strong>Tip:</strong> matching names do not guarantee equivalent behavior. Read the relationship label—Exact, Similar, Partial, None, or Unknown—before translating a workflow between tools.</div>
    </section>`;
}

function notFoundView() {
  document.title = "Not found | Agent Command Atlas";
  return `<div class="not-found"><p class="eyebrow">404</p><h1>Reference page not found</h1><p>This route is not present in the generated Atlas catalog.</p><a class="button" href="">Return to the reference</a></div>`;
}

function syncUrl(filters, fixedTool = "") {
  const params = new URLSearchParams();
  if (filters.q) params.set("q", filters.q);
  if (!fixedTool && filters.tool) params.set("tool", filters.tool);
  if (filters.type) params.set("type", filters.type);
  if (filters.category) params.set("category", filters.category);
  if (filters.maturity) params.set("maturity", filters.maturity);
  history.replaceState(null, "", `${location.pathname}${params.size ? `?${params}` : ""}`);
}

function bindReference(fixedTool = "") {
  const getFilters = () => ({
    q: $("#q")?.value.trim() || "",
    tool: fixedTool || $("#tool")?.value || "",
    type: $("#type")?.value || "",
    category: $("#category")?.value || "",
    maturity: $("#maturity")?.value || "",
  });
  let updateTimer;
  const update = () => {
    state.visibleLimit = 24;
    const filters = getFilters();
    syncUrl(filters, fixedTool);
    $("#results-region").outerHTML = resultsMarkup(filters);
    bindShowMore(filters);
  };
  const updateFromTyping = () => {
    window.clearTimeout(updateTimer);
    updateTimer = window.setTimeout(update, 90);
  };
  ["tool", "type", "category", "maturity"].forEach((id) => {
    $(`#${id}`)?.addEventListener("change", update);
  });
  $("#q")?.addEventListener("input", updateFromTyping);
  $("#q")?.addEventListener("search", update);
  $("#search-form")?.addEventListener("submit", (event) => {
    event.preventDefault();
    window.clearTimeout(updateTimer);
    update();
    $("#q")?.focus();
  });
  $("#reset")?.addEventListener("click", () => {
    ["q", "tool", "type", "category", "maturity"].forEach((id) => { if ($(`#${id}`)) $(`#${id}`).value = ""; });
    update();
    $("#q")?.focus();
  });
  document.querySelectorAll(".quick-search, .search-hint__link").forEach((button) => button.addEventListener("click", () => {
    if (!$("#q")) return;
    $("#q").value = button.dataset.query || "";
    update();
    $("#reference-heading")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }));
  bindShowMore(getFilters());
}

function bindShowMore(filters) {
  $("#show-more")?.addEventListener("click", () => {
    state.visibleLimit += 24;
    $("#results-region").outerHTML = resultsMarkup(filters);
    bindShowMore(filters);
  });
}

function bindCopyExamples() {
  document.querySelectorAll(".copy-example").forEach((button) => button.addEventListener("click", async () => {
    const original = button.textContent;
    try {
      await navigator.clipboard.writeText(button.dataset.copy || "");
      button.textContent = "Copied";
    } catch {
      button.textContent = "Select code";
    }
    window.setTimeout(() => { button.textContent = original; }, 1600);
  }));
}

function renderRoute() {
  const route = document.body.dataset.route || "home";
  const [kind, ...parts] = route.split(":");
  let markup;
  if (kind === "tool") markup = toolView(parts.join(":"));
  else if (kind === "entry") markup = detailView(parts.join(":"));
  else if (kind === "compare") markup = compareView();
  else if (kind === "capability") markup = compareView(parts.join(":"));
  else if (kind === "coverage") markup = coverageView();
  else if (kind === "guide") markup = guideView();
  else markup = homeView();
  $("#main-content").innerHTML = markup;
  bindCopyExamples();
  if (kind === "home") bindReference();
  if (kind === "tool") bindReference(parts.join(":"));
}

function bindGlobalShortcuts() {
  document.addEventListener("keydown", (event) => {
    const target = event.target;
    const isEditing = target instanceof HTMLInputElement || target instanceof HTMLSelectElement || target instanceof HTMLTextAreaElement;
    if (event.key === "/" && !isEditing && $("#q")) {
      event.preventDefault();
      $("#q").focus();
    }
  });
}

async function init() {
  try {
    const [entries, tools, categories, capabilities] = await Promise.all([
      fetch("catalog.json").then((response) => {
        if (!response.ok) throw new Error(`Catalog request failed: ${response.status}`);
        return response.json();
      }),
      fetch("tools.json").then((response) => response.json()),
      fetch("categories.json").then((response) => response.json()),
      fetch("capabilities.json").then((response) => response.json()),
    ]);
    state.entries = entries;
    state.tools = new Map(tools.map((tool) => [tool.id, tool]));
    state.categories = new Map(categories.map((category) => [category.id, category]));
    state.capabilities = capabilities;
    state.entriesById = new Map(entries.map((entry) => [entry.id, entry]));
    prepareSearchIndex();
    renderRoute();
    bindGlobalShortcuts();
  } catch (error) {
    $("#main-content").innerHTML = `<div class="not-found"><p class="eyebrow">Load error</p><h1>The reference could not be loaded</h1><p>Serve the <code>site/</code> directory over HTTP and try again.</p></div>`;
    console.error(error);
  }
}

init();
