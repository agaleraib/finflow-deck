/**
 * Shared persistence helpers for uniqueness PoC runs.
 *
 * Both the CLI (`index.ts`) and the playground HTTP route (`routes/poc.ts`)
 * call into this module so runs land on disk in `uniqueness-poc-runs/<runId>/`
 * with a consistent structure. Every file written here is human-readable
 * (markdown for prose, pretty-printed JSON for structured data) so the
 * `analyze-uniqueness-run` skill can operate on CLI runs and playground
 * runs interchangeably.
 *
 * Layout:
 *
 *   uniqueness-poc-runs/<runId>/
 *     ├── report.md                  ← markdown rollup (Compare only)
 *     ├── core-analysis.md           ← the Stage 1 Opus FA body
 *     ├── raw-data.json              ← the full RunResult or SoloRunResult
 *     ├── similarity-matrix.json     ← intra-tenant similarities (Compare only)
 *     └── outputs/
 *         ├── <identity>.md                         ← Stage 2 (Compare, 6 files)
 *         ├── stage6_<identity>__<persona>.md       ← Stage 6 cross-pipeline
 *         ├── stage7_{control|treatment}_<identity>__<persona>.md  ← Stage 7
 *         └── solo_<identity>__<persona>.md         ← Solo mode output
 */

import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import type { RunResult, NewsEvent, IdentityOutput, SimilarityResult, ContentPersona } from "./types.js";
import { renderReport } from "./report.js";

// Resolve the runs output root relative to this module so the helper works
// regardless of the caller's cwd. Same layout the CLI has used since v0.
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
export const RUNS_OUTPUT_ROOT =
  process.env["UNIQUENESS_RUNS_DIR"] ??
  join(__dirname, "..", "..", "..", "..", "..", "uniqueness-poc-runs");

function ensureDir(path: string): void {
  if (!existsSync(path)) {
    mkdirSync(path, { recursive: true });
  }
}

/**
 * Write a Compare-mode `RunResult` to disk.
 *
 * Produces `report.md`, `core-analysis.md`, `raw-data.json`,
 * `similarity-matrix.json`, and one file per output under `outputs/`.
 * Returns the absolute path of the run directory.
 */
export function persistRun(result: RunResult): string {
  const runDir = join(RUNS_OUTPUT_ROOT, result.runId);
  ensureDir(runDir);
  ensureDir(join(runDir, "outputs"));

  // The headline artifact
  writeFileSync(join(runDir, "report.md"), renderReport(result), "utf-8");

  writeFileSync(
    join(runDir, "core-analysis.md"),
    `# Core Analysis (FA Agent)\n\n${result.coreAnalysis.body}`,
    "utf-8",
  );

  // Stage 2 — intra-tenant cross-identity (6 different identities)
  for (const output of result.identityOutputs) {
    writeFileSync(
      join(runDir, "outputs", `${output.identityId}.md`),
      `# ${output.identityName}\n\n*${output.wordCount} words*\n\n---\n\n${output.body}`,
      "utf-8",
    );
  }

  // Stage 6 — cross-pipeline matrix (one file per persona)
  if (result.crossTenantMatrix) {
    const ct = result.crossTenantMatrix;
    for (let i = 0; i < ct.outputs.length; i++) {
      const output = ct.outputs[i]!;
      const persona = ct.personas[i]!;
      writeFileSync(
        join(
          runDir,
          "outputs",
          `stage6_${output.identityId}__${output.personaId ?? persona.id}.md`,
        ),
        `# ${output.identityName} — ${persona.name}\n\n` +
          `*${output.wordCount} words · ${persona.regionalVariant} · ${persona.brandVoice}*\n\n` +
          `---\n\n${output.body}`,
        "utf-8",
      );
    }
  }

  // Stage 7 — narrative-state control + treatment
  if (result.narrativeStateTest) {
    const ns = result.narrativeStateTest;
    const writeGroup = (
      group: "control" | "treatment",
      outputs: typeof ns.controlOutputs,
    ): void => {
      for (let i = 0; i < outputs.length; i++) {
        const output = outputs[i]!;
        const personaId = output.personaId ?? `unknown-${i}`;
        const label =
          group === "control"
            ? "CONTROL (no narrative state)"
            : "TREATMENT (with narrative state)";
        writeFileSync(
          join(
            runDir,
            "outputs",
            `stage7_${group}_${output.identityId}__${personaId}.md`,
          ),
          `# ${output.identityName} — ${personaId} — ${label}\n\n` +
            `*${output.wordCount} words · event: ${ns.secondEvent.title}*\n\n` +
            `---\n\n${output.body}`,
          "utf-8",
        );
      }
    };
    writeGroup("control", ns.controlOutputs);
    writeGroup("treatment", ns.treatmentOutputs);
  }

  // Raw structured data for cross-run analysis
  writeFileSync(
    join(runDir, "similarity-matrix.json"),
    JSON.stringify(result.similarities, null, 2),
    "utf-8",
  );
  writeFileSync(
    join(runDir, "raw-data.json"),
    JSON.stringify(result, null, 2),
    "utf-8",
  );

  // Cross-tenant comparison HTML (self-contained, opens in browser from Finder)
  if (result.crossTenantMatrix && result.crossTenantMatrix.outputs.length >= 2) {
    const html = renderComparisonHtml(result);
    writeFileSync(join(runDir, "comparison.html"), html, "utf-8");
  }

  return runDir;
}

/**
 * Solo-mode result shape. Kept as a local interface mirror here (rather than
 * imported from `routes/poc.ts`) so this module stays independent of the
 * HTTP layer. The canonical `SoloRunResult` in `routes/poc.ts` is a
 * structural subtype of this — assignable at the call site via normal
 * TypeScript structural typing.
 */
export interface PersistableSoloRunResult {
  runId: string;
  startedAt: string;
  finishedAt: string;
  event: NewsEvent;
  coreAnalysisBody: string;
  personaId: string;
  output: IdentityOutput;
  totalCostUsd: number;
  totalDurationMs: number;
}

/**
 * Write a Solo-mode run to disk. Different shape than `persistRun` because
 * Solo skips Stage 2 / Stage 6 / Stage 7 and only produces one output.
 */
export function persistSoloRun(result: PersistableSoloRunResult): string {
  const runDir = join(RUNS_OUTPUT_ROOT, result.runId);
  ensureDir(runDir);
  ensureDir(join(runDir, "outputs"));

  // Minimal report: metadata + core analysis + single output
  const reportLines: string[] = [];
  reportLines.push(`# Solo run — ${result.event.title}`);
  reportLines.push("");
  reportLines.push(`**Run id:** \`${result.runId}\``);
  reportLines.push(`**Started:** ${result.startedAt}`);
  reportLines.push(`**Finished:** ${result.finishedAt}`);
  reportLines.push(
    `**Duration:** ${(result.totalDurationMs / 1000).toFixed(1)}s`,
  );
  reportLines.push(`**Cost:** $${result.totalCostUsd.toFixed(4)}`);
  reportLines.push(`**Persona:** ${result.personaId}`);
  reportLines.push(
    `**Identity:** ${result.output.identityName} (\`${result.output.identityId}\`)`,
  );
  reportLines.push("");
  reportLines.push("---");
  reportLines.push("");
  reportLines.push("## Core Analysis (FA Agent)");
  reportLines.push("");
  reportLines.push(result.coreAnalysisBody);
  reportLines.push("");
  reportLines.push("---");
  reportLines.push("");
  reportLines.push(`## ${result.output.identityName} output`);
  reportLines.push("");
  reportLines.push(
    `*${result.output.wordCount} words · ${result.output.model} · ${(result.output.durationMs / 1000).toFixed(1)}s · $${result.output.costUsd.toFixed(4)}*`,
  );
  reportLines.push("");
  reportLines.push(result.output.body);
  reportLines.push("");

  writeFileSync(join(runDir, "report.md"), reportLines.join("\n"), "utf-8");

  writeFileSync(
    join(runDir, "core-analysis.md"),
    `# Core Analysis (FA Agent)\n\n${result.coreAnalysisBody}`,
    "utf-8",
  );

  // Single output file under outputs/
  writeFileSync(
    join(
      runDir,
      "outputs",
      `solo_${result.output.identityId}__${result.personaId}.md`,
    ),
    `# ${result.output.identityName} — ${result.personaId} — SOLO\n\n` +
      `*${result.output.wordCount} words · ${result.output.model} · ${(result.output.durationMs / 1000).toFixed(1)}s · $${result.output.costUsd.toFixed(4)}*\n\n` +
      `---\n\n${result.output.body}`,
    "utf-8",
  );

  writeFileSync(
    join(runDir, "raw-data.json"),
    JSON.stringify(result, null, 2),
    "utf-8",
  );

  return runDir;
}

// ───────────────────────────────────────────────────────────────────
// Self-contained HTML comparison for cross-tenant outputs
// ───────────────────────────────────────────────────────────────────

/** Split markdown into (heading, content) pairs on ## boundaries. */
function parseSections(md: string): Array<{ heading: string; content: string }> {
  const lines = md.trim().split("\n");
  const sections: Array<{ heading: string; content: string }> = [];
  let currentHeading = "";
  let currentLines: string[] = [];

  for (const line of lines) {
    if (line.startsWith("## ")) {
      if (currentHeading || currentLines.length) {
        sections.push({ heading: currentHeading, content: currentLines.join("\n").trim() });
      }
      currentHeading = line.slice(3).trim();
      currentLines = [];
    } else if (line.startsWith("# ") && sections.length === 0) {
      sections.push({ heading: "__title__", content: line.slice(2).trim() });
      currentHeading = "";
      currentLines = [];
    } else {
      currentLines.push(line);
    }
  }
  if (currentHeading || currentLines.length) {
    sections.push({ heading: currentHeading, content: currentLines.join("\n").trim() });
  }
  return sections;
}

/** Find n-gram phrases shared between two texts (min 6 words). */
function findSharedPhrases(textA: string, textB: string): string[] {
  const MIN_WORDS = 6;
  const MAX_N = 14;
  const wordsA = textA.toLowerCase().split(/\s+/);
  const wordsB = textB.toLowerCase().split(/\s+/);
  const shared = new Set<string>();

  for (let n = MIN_WORDS; n <= Math.min(MAX_N, Math.min(wordsA.length, wordsB.length)); n++) {
    const ngramsA = new Set<string>();
    for (let i = 0; i <= wordsA.length - n; i++) {
      ngramsA.add(wordsA.slice(i, i + n).join(" "));
    }
    for (let i = 0; i <= wordsB.length - n; i++) {
      const ng = wordsB.slice(i, i + n).join(" ");
      if (ngramsA.has(ng)) shared.add(ng);
    }
  }

  // Deduplicate: remove substrings of longer matches
  const sorted = [...shared].sort((a, b) => b.length - a.length);
  const filtered: string[] = [];
  for (const s of sorted) {
    if (!filtered.some((longer) => longer.includes(s))) {
      filtered.push(s);
    }
  }
  return filtered.slice(0, 15);
}

/** Very basic markdown → HTML (bold, italic, paragraphs). */
function mdToHtml(text: string): string {
  let out = text.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  out = out.replace(/\*(.+?)\*/g, "<em>$1</em>");
  return out
    .split("\n\n")
    .filter((p) => p.trim())
    .map((p) => `<p>${p.trim()}</p>`)
    .join("");
}

/** Highlight shared phrases in HTML content with <mark>. */
function highlightShared(html: string, phrases: string[]): string {
  let out = html;
  for (const phrase of phrases) {
    const escaped = phrase.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    out = out.replace(new RegExp(escaped, "gi"), `<mark class="shared">${phrase}</mark>`);
  }
  return out;
}

function escHtml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function verdictClass(v: string): string {
  if (v.includes("distinct")) return "distinct";
  if (v.includes("reskinned")) return "reskinned";
  if (v.includes("fabrication")) return "fabrication";
  return "";
}

function scoreClass(value: number, warnAbove: number): string {
  return value > warnAbove ? "warn" : "good";
}

/**
 * Build a self-contained HTML comparison page for cross-tenant outputs.
 * Only uses cross-tenant pairs (persona-vs-persona within the same identity).
 */
function renderComparisonHtml(result: RunResult): string {
  const ct = result.crossTenantMatrix!;
  const event = result.event;
  const identityName = ct.identityName;

  // Build items list from cross-tenant outputs + personas
  interface ComparisonItem {
    name: string;
    brandVoice: string;
    regionalVariant: string;
    companyBackground: string[];
    ctaPolicy: string;
    body: string;
    wordCount: number;
    identityName: string;
  }

  const items: ComparisonItem[] = ct.outputs.map((o, i) => {
    const p = ct.personas[i]!;
    return {
      name: p.name,
      brandVoice: (p as ContentPersona & { brandVoice?: string }).brandVoice ?? "",
      regionalVariant: (p as ContentPersona & { regionalVariant?: string }).regionalVariant ?? "",
      companyBackground: ((p as ContentPersona & { companyBackground?: string[] }).companyBackground) ?? [],
      ctaPolicy: (p as ContentPersona & { ctaPolicy?: string }).ctaPolicy ?? "",
      body: o.body,
      wordCount: o.wordCount,
      identityName: o.identityName,
    };
  });

  // Parse all sections and pre-compute shared phrases per pair
  const allParsed = items.map((item) => parseSections(item.body));

  interface Pair {
    indexA: number;
    indexB: number;
    sim: SimilarityResult | undefined;
    shared: string[];
  }

  const simLookup = new Map<string, SimilarityResult>();
  for (const s of ct.similarities) {
    simLookup.set(`${s.identityA}|${s.identityB}`, s);
    simLookup.set(`${s.identityB}|${s.identityA}`, s);
  }

  const pairs: Pair[] = [];
  for (let i = 0; i < items.length; i++) {
    for (let j = i + 1; j < items.length; j++) {
      const sim =
        simLookup.get(`${items[i]!.name}|${items[j]!.name}`) ??
        simLookup.get(`${ct.outputs[i]!.personaId}|${ct.outputs[j]!.personaId}`);
      pairs.push({
        indexA: i,
        indexB: j,
        sim,
        shared: findSharedPhrases(items[i]!.body, items[j]!.body),
      });
    }
  }

  const singlePair = pairs.length === 1;

  // ── Build HTML ──

  const lines: string[] = [];
  const push = (s: string) => lines.push(s);

  push(`<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Comparison — ${escHtml(event.title.slice(0, 60))}</title>
<style>
[data-theme="dark"]{--bg:#0f1117;--bg-card:#1a1d27;--bg-section:#22252f;--text:#e4e6eb;--text-muted:#8b8fa3;--text-heading:#fff;--border:#2d3040;--accent-blue:#5b8def;--accent-green:#4ade80;--accent-amber:#fbbf24;--accent-red:#f87171;--shared-bg:rgba(251,191,36,.15);--shared-border:rgba(251,191,36,.4);--btn-bg:#22252f;--btn-active:#2d3040;--help-bg:#1e2130;--help-border:#3d4060}
[data-theme="light"]{--bg:#f5f6f8;--bg-card:#fff;--bg-section:#f0f1f4;--text:#1a1d27;--text-muted:#6b7085;--text-heading:#0f1117;--border:#d8dae0;--accent-blue:#3b6fd4;--accent-green:#16a34a;--accent-amber:#d97706;--accent-red:#dc2626;--shared-bg:rgba(217,119,6,.12);--shared-border:rgba(217,119,6,.35);--btn-bg:#e8e9ed;--btn-active:#d8dae0;--help-bg:#f0f1f5;--help-border:#c8cad0}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Inter',-apple-system,BlinkMacSystemFont,sans-serif;background:var(--bg);color:var(--text);line-height:1.6;padding:24px 32px;transition:background .2s,color .2s}
.header{display:flex;justify-content:space-between;align-items:center;margin-bottom:24px;padding-bottom:20px;border-bottom:1px solid var(--border)}
.header-left h1{font-size:20px;font-weight:600;color:var(--text-heading);margin-bottom:4px}
.header-left .meta{font-size:12px;color:var(--text-muted)}
.theme-toggle{background:var(--btn-bg);border:1px solid var(--border);color:var(--text-muted);padding:6px 12px;border-radius:6px;cursor:pointer;font-size:12px;transition:all .2s}
.theme-toggle:hover{border-color:var(--accent-blue);color:var(--text)}
.pair-selector{margin-bottom:20px}
.pair-selector-header{display:flex;align-items:center;gap:8px;margin-bottom:10px}
.pair-selector-header h3{font-size:13px;font-weight:500;color:var(--text-muted);text-transform:uppercase;letter-spacing:.04em}
.help-btn{display:inline-flex;align-items:center;justify-content:center;width:18px;height:18px;border-radius:50%;background:var(--btn-bg);border:1px solid var(--border);color:var(--text-muted);font-size:11px;font-weight:700;cursor:pointer;transition:all .2s;line-height:1}
.help-btn:hover{border-color:var(--accent-blue);color:var(--accent-blue)}
.help-panel{display:none;background:var(--help-bg);border:1px solid var(--help-border);border-radius:8px;padding:14px 18px;margin-bottom:12px;font-size:12px;color:var(--text-muted);line-height:1.7}
.help-panel.visible{display:block}
.help-panel strong{color:var(--text)}
.help-panel ul{padding-left:16px;margin-top:6px}
.pair-btns{display:flex;flex-wrap:wrap;gap:6px}
.pair-btn{background:var(--btn-bg);border:1px solid var(--border);color:var(--text-muted);padding:5px 12px;border-radius:6px;cursor:pointer;font-size:12px;transition:all .15s;white-space:nowrap}
.pair-btn:hover{border-color:var(--accent-blue);color:var(--text)}
.pair-btn.active{background:var(--accent-blue);border-color:var(--accent-blue);color:#fff;font-weight:500}
.verdict-dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:5px}
.verdict-dot.distinct{background:var(--accent-green)}.verdict-dot.reskinned{background:var(--accent-amber)}.verdict-dot.fabrication{background:var(--accent-red)}.verdict-dot.unknown{background:var(--text-muted)}
.scores{display:flex;justify-content:center;gap:16px;margin:16px 0;flex-wrap:wrap}
.score-card{background:var(--bg-card);border:1px solid var(--border);border-radius:8px;padding:10px 16px;text-align:center;min-width:110px}
.score-card .label{font-size:10px;text-transform:uppercase;letter-spacing:.05em;color:var(--text-muted);margin-bottom:2px}
.score-card .value{font-size:20px;font-weight:700}
.good{color:var(--accent-green)}.warn{color:var(--accent-amber)}.bad{color:var(--accent-red)}
.verdict-badge{display:inline-block;padding:4px 12px;border-radius:6px;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.04em}
.verdict-badge.distinct{background:rgba(74,222,128,.15);color:var(--accent-green)}
.verdict-badge.reskinned{background:rgba(251,191,36,.15);color:var(--accent-amber)}
.verdict-badge.fabrication{background:rgba(248,113,113,.15);color:var(--accent-red)}
.structural-note{text-align:center;margin:12px 0;padding:12px;background:var(--bg-card);border:1px solid var(--border);border-radius:8px;font-size:12px;color:var(--text-muted)}
.structural-note strong{color:var(--accent-amber)}
.columns{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-top:20px}
.column{background:var(--bg-card);border:1px solid var(--border);border-radius:10px;overflow:hidden}
.column-header{padding:16px 20px;border-bottom:1px solid var(--border);background:var(--bg-section)}
.column-header h2{font-size:15px;font-weight:600;color:var(--text-heading);margin-bottom:3px}
.column-header .brand-voice{font-size:11px;color:var(--text-muted);line-height:1.5;font-style:italic}
.column-header .meta-row{display:flex;gap:8px;margin-top:6px;font-size:11px;color:var(--text-muted);flex-wrap:wrap}
.column-header .meta-row span{background:rgba(91,141,239,.1);padding:1px 7px;border-radius:4px;border:1px solid rgba(91,141,239,.15)}
.company-bg{padding:10px 20px;border-bottom:1px solid var(--border);background:rgba(91,141,239,.03)}
.company-bg summary{font-size:11px;font-weight:500;color:var(--accent-blue);cursor:pointer}
.company-bg ul{margin-top:6px;padding-left:14px;font-size:11px;color:var(--text-muted);line-height:1.7}
.company-bg-missing{padding:10px 20px;border-bottom:1px solid var(--border);color:var(--accent-amber);font-size:11px;font-style:italic}
.section{padding:14px 20px;border-bottom:1px solid rgba(45,48,64,.4)}
.section:last-child{border-bottom:none}
.section h3{font-size:13px;font-weight:600;color:var(--accent-blue);margin-bottom:6px;padding-bottom:5px;border-bottom:1px solid rgba(91,141,239,.12)}
.section p{font-size:13px;margin-bottom:8px}
.section-title h3{font-size:15px;color:var(--text-heading);border:none;padding:0;margin:0}
mark.shared{background:var(--shared-bg);border-bottom:2px solid var(--shared-border);color:var(--accent-amber);padding:1px 2px;border-radius:2px}
.legend{display:flex;justify-content:center;gap:20px;margin:12px 0;font-size:11px;color:var(--text-muted)}
.legend span{display:flex;align-items:center;gap:5px}
.legend .swatch{display:inline-block;width:12px;height:12px;border-radius:3px}
.judge-reasoning{margin-top:24px;background:var(--bg-card);border:1px solid var(--border);border-radius:10px;padding:20px}
.judge-reasoning h3{font-size:13px;font-weight:600;color:var(--text-heading);margin-bottom:10px}
.judge-reasoning p{font-size:12px;color:var(--text-muted);line-height:1.7;margin-bottom:10px}
.judge-reasoning .rlabel{font-size:10px;text-transform:uppercase;letter-spacing:.05em;color:var(--accent-blue);margin-bottom:3px;font-weight:600}
.pair-view{display:none}.pair-view.active{display:block}
</style>
</head>
<body>`);

  // Header
  push(`<div class="header"><div class="header-left">
<h1>Output Comparison</h1>
<div class="meta">${escHtml(event.title)}<br>
Identity: ${escHtml(identityName)} · Run: ${escHtml(result.runId.slice(0, 40))}</div>
</div>
<button class="theme-toggle" onclick="toggleTheme()">Light / Dark</button>
</div>`);

  // Pair selector (only if more than 1 pair)
  if (!singlePair) {
    push(`<div class="pair-selector">
<div class="pair-selector-header">
<h3>Compare Pair</h3>
<button class="help-btn" onclick="toggleHelp()" title="What is this?">?</button>
</div>
<div class="help-panel" id="helpPanel">
<strong>How to use this comparison:</strong>
<ul>
<li>Each button represents two outputs generated from the <strong>same news event</strong> using the <strong>same writing format</strong> (${escHtml(identityName)}), but shaped for <strong>different broker brands</strong> (personas).</li>
<li>Click a pair to see both outputs <strong>side by side</strong> with shared phrases highlighted in amber.</li>
<li>The colored dot shows the judge's verdict: <span style="color:var(--accent-green)">green = distinct</span> (good — the outputs feel genuinely different), <span style="color:var(--accent-amber)">amber = reskinned</span> (the outputs are too similar — needs work), <span style="color:var(--accent-red)">red = fabrication risk</span> (one output may have invented facts not in the source).</li>
<li><strong>Scores:</strong> Cosine and ROUGE-L measure raw text overlap. Fidelity measures factual accuracy to the source. Presentation similarity measures how alike the two outputs <em>feel</em> — lower is better.</li>
<li><strong>Structural overlap</strong> shows whether both outputs use the same section headings — a sign that the structural backbone from the source analysis is leaking through instead of being reshaped by each persona.</li>
<li>The <strong>amber highlights</strong> in the text mark phrases of 6+ words that appear in both outputs — shared wording that should ideally be different.</li>
</ul>
</div>
<div class="pair-btns">`);

    for (let pi = 0; pi < pairs.length; pi++) {
      const p = pairs[pi]!;
      const vc = p.sim ? verdictClass(p.sim.judgeTrinaryVerdict ?? "") || "unknown" : "unknown";
      const active = pi === 0 ? " active" : "";
      push(`<button class="pair-btn${active}" onclick="showPair(${pi})"><span class="verdict-dot ${vc}"></span>${escHtml(items[p.indexA]!.name)} vs ${escHtml(items[p.indexB]!.name)}</button>`);
    }

    push(`</div></div>`);
  }

  // Each pair view
  for (let pi = 0; pi < pairs.length; pi++) {
    const p = pairs[pi]!;
    const sim = p.sim;
    const a = items[p.indexA]!;
    const b = items[p.indexB]!;
    const active = pi === 0 ? " active" : "";

    push(`<div class="pair-view${active}" id="pair-${pi}">`);

    // Scores
    if (sim) {
      const cos = sim.cosineSimilarity;
      const rouge = sim.rougeL;
      const fid = sim.judgeFactualFidelity ?? 0;
      const pres = sim.judgePresentationSimilarity ?? 0;
      const v = sim.judgeTrinaryVerdict ?? "no data";
      push(`<div class="scores">
<div class="score-card"><div class="label">Cosine</div><div class="value ${scoreClass(cos, 0.85)}">${cos.toFixed(3)}</div></div>
<div class="score-card"><div class="label">ROUGE-L</div><div class="value ${scoreClass(rouge, 0.3)}">${rouge.toFixed(3)}</div></div>
<div class="score-card"><div class="label">Fidelity</div><div class="value good">${fid.toFixed(2)}</div></div>
<div class="score-card"><div class="label">Presentation</div><div class="value ${scoreClass(pres, 0.4)}">${pres.toFixed(2)}</div></div>
<div class="score-card"><div class="label">Verdict</div><div class="verdict-badge ${verdictClass(v)}">${v.replace(/_/g, " ")}</div></div>
</div>`);
    }

    // Structural overlap
    const secsA = allParsed[p.indexA]!;
    const secsB = allParsed[p.indexB]!;
    const headA = secsA.filter((s) => s.heading !== "__title__").map((s) => s.heading);
    const headB = secsB.filter((s) => s.heading !== "__title__").map((s) => s.heading);
    if (headA.length && headB.length) {
      const setA = new Set(headA.map((h) => h.toLowerCase()));
      const setB = new Set(headB.map((h) => h.toLowerCase()));
      const union = new Set([...setA, ...setB]);
      const intersection = [...setA].filter((h) => setB.has(h));
      push(`<div class="structural-note"><strong>Structural overlap:</strong> ${intersection.length}/${union.size} section headings shared<br>
A: ${headA.map(escHtml).join(" &rarr; ")}<br>B: ${headB.map(escHtml).join(" &rarr; ")}</div>`);
    }

    push(`<div class="legend"><span><span class="swatch" style="background:var(--shared-bg);border:1px solid var(--shared-border)"></span>Shared phrase (&ge;6 words)</span></div>`);

    // Two columns
    push(`<div class="columns">`);
    for (const item of [a, b]) {
      const idx = items.indexOf(item);
      const secs = allParsed[idx]!;
      push(`<div class="column"><div class="column-header">
<h2>${escHtml(item.name)}</h2>`);
      if (item.brandVoice) {
        push(`<div class="brand-voice">${escHtml(item.brandVoice.slice(0, 250))}</div>`);
      }
      push(`<div class="meta-row">`);
      if (item.regionalVariant) push(`<span>${escHtml(item.regionalVariant)}</span>`);
      push(`<span>${item.wordCount} words</span>`);
      if (item.ctaPolicy) push(`<span>CTA: ${escHtml(item.ctaPolicy)}</span>`);
      push(`<span>${escHtml(item.identityName)}</span>`);
      push(`</div></div>`);

      if (item.companyBackground.length) {
        push(`<div class="company-bg"><details><summary>Company Background (${item.companyBackground.length})</summary><ul>${item.companyBackground.map((f) => `<li>${escHtml(f)}</li>`).join("")}</ul></details></div>`);
      } else if (item.brandVoice) {
        push(`<div class="company-bg-missing">&#9888; No companyBackground configured</div>`);
      }

      for (const sec of secs) {
        if (sec.heading === "__title__") {
          push(`<div class="section section-title"><h3>${escHtml(sec.content)}</h3></div>`);
        } else {
          const html = highlightShared(mdToHtml(sec.content), p.shared);
          push(`<div class="section"><h3>${escHtml(sec.heading)}</h3>${html}</div>`);
        }
      }
      push(`</div>`);
    }
    push(`</div>`); // columns

    // Judge reasoning
    if (sim?.judgeFactualFidelityReasoning || sim?.judgePresentationSimilarityReasoning) {
      push(`<div class="judge-reasoning"><h3>Judge Reasoning</h3>`);
      if (sim.judgeFactualFidelityReasoning) {
        push(`<div class="rlabel">Factual Fidelity (${sim.judgeFactualFidelity ?? "?"})</div>
<p>${escHtml(sim.judgeFactualFidelityReasoning)}</p>`);
      }
      if (sim.judgePresentationSimilarityReasoning) {
        push(`<div class="rlabel">Presentation Similarity (${sim.judgePresentationSimilarity ?? "?"})</div>
<p>${escHtml(sim.judgePresentationSimilarityReasoning)}</p>`);
      }
      push(`</div>`);
    }

    push(`</div>`); // pair-view
  }

  // JavaScript
  push(`<script>
function showPair(idx){
  document.querySelectorAll('.pair-view').forEach(el=>el.classList.remove('active'));
  document.querySelectorAll('.pair-btn').forEach(el=>el.classList.remove('active'));
  document.getElementById('pair-'+idx).classList.add('active');
  document.querySelectorAll('.pair-btn')[idx].classList.add('active');
  window.scrollTo({top:0,behavior:'smooth'});
}
function toggleTheme(){
  const h=document.documentElement;
  h.dataset.theme=h.dataset.theme==='dark'?'light':'dark';
}
function toggleHelp(){
  document.getElementById('helpPanel').classList.toggle('visible');
}
</script></body></html>`);

  return lines.join("\n");
}
