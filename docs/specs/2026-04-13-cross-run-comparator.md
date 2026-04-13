# Cross-Run Comparator — Statistical analysis across uniqueness PoC runs

**Date:** 2026-04-13
**Status:** Draft
**Owners:** Albert Galera (decisions), Claude (drafting + implementation)

## Prior Work
Builds on: [Content Uniqueness](2026-04-07-content-uniqueness.md), [Narrative State Persistence](2026-04-08-narrative-state-persistence.md), [Editorial Memory](2026-04-12-editorial-memory.md)
Assumes: `RunResult` type from `packages/api/src/benchmark/uniqueness-poc/types.ts`; run directory layout from `persist.ts` (`uniqueness-poc-runs/<runId>/raw-data.json`); 13-metric scoring system; two-axis judge verdicts (`distinct_products` / `reskinned_same_article` / `fabrication_risk`)
Depends on: `docs/specs/2026-04-13-run-manifest.md` (adds `setup` metadata to raw-data.json for grouping runs by configuration)
Changes: Nothing overridden — this is a pure analysis tool that reads existing data

---

## 1. Goal

Each uniqueness PoC run is an isolated anecdote. The cross-run comparator turns N anecdotes into evidence by answering two questions:

1. **A/B comparison**: Does setup A (e.g., narrative-state extractor) produce statistically better cross-tenant differentiation than setup B (e.g., editorial-memory with pgvector)? Measured across cosine similarity, ROUGE-L, fabrication rate, and judge verdicts.

2. **Compounding analysis**: Given a chronologically ordered sequence of runs where editorial memory accumulates, does cross-tenant cosine similarity decrease over time while intra-tenant continuity holds? This is the core thesis — editorial memory creates compounding divergence.

**Who it's for:** The FinFlow team, to make data-driven decisions about which memory architecture to ship, and to prove the compounding thesis to prospects.

**What it is not:** A visualization tool. Output is structured markdown and machine-readable JSON. Charts are deferred.

---

## 2. Data Model

No persistent state. The comparator is a pure function: reads run directories, outputs a report.

### Input: RunResult + Setup Metadata

The comparator reads `raw-data.json` from each run directory. The companion run-manifest spec adds a `setup` field:

```typescript
interface RunSetup {
  /** Machine-readable setup identifier, e.g. "narrative-state", "editorial-memory", "baseline" */
  setupId: string;
  /** Human-readable label for reports */
  setupLabel: string;
  /** Free-form tags for filtering, e.g. ["4-persona", "iran-strike", "conformance-on"] */
  tags: string[];
  /** ISO date of when the run was executed (redundant with startedAt, but explicit for filtering) */
  date: string;
  /** Sequence index for compounding analysis — 0-based position within a series */
  sequenceIndex?: number;
  /** Series identifier grouping runs in a compounding sequence */
  seriesId?: string;
}
```

Runs without a `setup` field are classified as `setupId: "unknown"` and excluded from A/B comparisons but included in aggregate statistics.

### Output: ComparisonReport

```typescript
interface ComparisonReport {
  generatedAt: string;
  mode: "ab" | "compounding" | "summary";
  filters: ReportFilters;
  groups: GroupSummary[];
  /** Present only in "ab" mode */
  abDelta?: ABDelta;
  /** Present only in "compounding" mode */
  compoundingTrend?: CompoundingTrend;
}

interface ReportFilters {
  setupIds?: string[];
  fixtureIds?: string[];
  personaIds?: string[];
  dateRange?: { from: string; to: string };
  seriesId?: string;
}

interface GroupSummary {
  setupId: string;
  setupLabel: string;
  runCount: number;
  /** Metrics from crossTenantMatrix (Stage 6) — the load-bearing test */
  crossTenant: MetricDistribution;
  /** Metrics from narrativeStateTest (Stage 7) — treatment group */
  narrativeState?: MetricDistribution;
  /** Judge verdict distribution */
  judgeVerdicts: {
    distinct_products: number;
    reskinned_same_article: number;
    fabrication_risk: number;
    /** Pairs where judge failed and was skipped */
    judge_failures: number;
    total_pairs: number;
  };
  /** Fabrication rate = fabrication_risk / total_pairs */
  fabricationRate: number;
  /** Cost per run */
  costDistribution: { mean: number; min: number; max: number; stddev: number };
}

interface MetricDistribution {
  cosine: { mean: number; min: number; max: number; stddev: number };
  rougeL: { mean: number; min: number; max: number; stddev: number };
  /** Per-pair judge scores (factual fidelity, presentation similarity) */
  judgeFactualFidelity: { mean: number; min: number; max: number; stddev: number };
  judgePresentationSimilarity: { mean: number; min: number; max: number; stddev: number };
}

interface ABDelta {
  setupA: string;
  setupB: string;
  /** Positive = A is better (lower similarity = more unique) */
  cosineDelta: { value: number; direction: "A_better" | "B_better" | "neutral"; significant: boolean };
  rougeLDelta: { value: number; direction: "A_better" | "B_better" | "neutral"; significant: boolean };
  fabricationDelta: { value: number; direction: "A_better" | "B_better" | "neutral" };
  verdictDelta: { distinctRate_A: number; distinctRate_B: number; direction: "A_better" | "B_better" | "neutral" };
  /** Is the delta larger than observed within-group run-to-run variance? */
  significanceMethod: "variance_ratio";
  significanceNote: string;
}

interface CompoundingTrend {
  seriesId: string;
  points: Array<{
    sequenceIndex: number;
    runId: string;
    date: string;
    crossTenantMeanCosine: number;
    crossTenantMeanRougeL: number;
    /** Stage 7 treatment - control delta (positive = memory helping) */
    narrativeStateCosineImprovement?: number;
    fabricationRate: number;
  }>;
  /** Linear regression slope on crossTenantMeanCosine. Negative = improving. */
  cosineTrendSlope: number;
  /** Is the slope significantly different from zero? */
  cosineTrendSignificant: boolean;
  /** Does fabrication rate stay flat or decrease? */
  fabricationTrendSlope: number;
  fabricationStable: boolean;
}
```

---

## 3. CLI Interface

```
bun run packages/api/src/benchmark/uniqueness-poc/compare.ts <mode> [options]
```

### Modes

| Mode | Description | Required options |
|------|-------------|------------------|
| `summary` | Aggregate stats across all runs, grouped by setup | None |
| `ab` | A/B comparison between two setups | `--setup-a <id> --setup-b <id>` |
| `compounding` | Trend analysis for a sequential series | `--series <id>` |

### Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--runs-dir` | string | `uniqueness-poc-runs/` (resolved from project root) | Path to runs directory |
| `--setup-a` | string | — | Setup ID for group A (ab mode) |
| `--setup-b` | string | — | Setup ID for group B (ab mode) |
| `--series` | string | — | Series ID for compounding mode |
| `--fixture` | string | — | Filter to runs using this fixture/event ID |
| `--persona` | string | — | Filter to pairs involving this persona ID |
| `--from` | string | — | ISO date lower bound (inclusive) |
| `--to` | string | — | ISO date upper bound (inclusive) |
| `--out` | string | stdout | Write markdown report to this file |
| `--json` | boolean | false | Also write machine-readable JSON alongside the markdown |
| `--stage` | `"6"` \| `"7"` \| `"both"` | `"6"` | Which stage's metrics to use for cross-tenant comparison |

---

## 4. Requirements

### Phase 1: Core comparison engine

#### Run loader and grouping

Load all `raw-data.json` files from the runs directory, parse them as `RunResult`, extract setup metadata, and group by `setupId`.

**Acceptance criteria:**
- [ ] `loadRuns(runsDir, filters)` returns `Map<setupId, RunResult[]>` with runs grouped by setup
- [ ] Runs without `raw-data.json` are silently skipped (logged to stderr)
- [ ] Runs without a `setup` field are grouped under `setupId: "unknown"`
- [ ] Runs with `setup.tags` matching filter criteria are included; non-matching excluded
- [ ] `--fixture` filter matches on `result.event.id`
- [ ] `--from` / `--to` filters match on `result.startedAt` (ISO comparison)
- [ ] When fewer than 2 runs exist for a setup in ab mode, the tool exits with code 1 and a message: `"Setup '<id>' has <n> run(s), need at least 2 for comparison"`
- [ ] Error case: corrupt JSON in raw-data.json -> skip run, log warning to stderr with path
- [ ] Error case: runs directory does not exist -> exit code 1, message: `"Runs directory not found: <path>"`

#### Metric extraction

Extract the key metrics from each `RunResult` for statistical aggregation.

**Acceptance criteria:**
- [ ] From `crossTenantMatrix`: extract `meanCosine`, `meanRougeL`, `minCosine`, `maxCosine`, per-pair `judgeFactualFidelity`, `judgePresentationSimilarity`, `judgeTrinaryVerdict`
- [ ] From `narrativeStateTest`: extract `treatmentMeanCosine`, `treatmentMeanRougeL`, `controlMeanCosine`, `controlMeanRougeL`, `cosineImprovement`
- [ ] From `narrativeStateTest.treatmentSimilarities` and `controlSimilarities`: extract per-pair judge verdicts
- [ ] Runs missing `crossTenantMatrix` (e.g., solo runs, early runs without Stage 6) are excluded from cross-tenant metrics with a stderr warning
- [ ] Fabrication rate is computed as `count(judgeTrinaryVerdict === "fabrication_risk") / total_judge_pairs` across all pairs in the group
- [ ] Judge failures (`judgeFailures` array) are counted separately and surfaced in the report

#### Statistical aggregation

Compute per-group summary statistics and cross-group deltas.

**Acceptance criteria:**
- [ ] `computeDistribution(values: number[])` returns `{ mean, min, max, stddev }` with stddev as population standard deviation
- [ ] A/B delta: `deltaValue = groupA.mean - groupB.mean`; direction is `"A_better"` when lower similarity (lower cosine) favors A, `"B_better"` otherwise; `"neutral"` when `|delta| < 0.005`
- [ ] Significance test: delta is "significant" when `|delta| > max(stddevA, stddevB)` (the delta exceeds the larger group's within-group variance). This is deliberately simple — not a proper t-test, but sufficient for N<20 PoC runs
- [ ] `significanceNote` field explains the method in plain English: `"Delta of X.XXX exceeds max within-group stddev of X.XXX"` or `"Delta of X.XXX is within noise (max stddev X.XXX)"`

### Phase 2: Compounding analysis

#### Trend computation

For a series of runs ordered by `sequenceIndex`, compute the trend in key metrics.

**Acceptance criteria:**
- [ ] `computeCompoundingTrend(runs: RunResult[], seriesId: string)` returns `CompoundingTrend` with runs sorted by `sequenceIndex`
- [ ] Linear regression slope computed via least-squares on `(sequenceIndex, crossTenantMeanCosine)` pairs
- [ ] `cosineTrendSignificant` is true when `|slope| > 0.01` AND R-squared > 0.5 (the trend explains more than half the variance)
- [ ] `fabricationStable` is true when `fabricationTrendSlope <= 0.01` (fabrication rate not increasing)
- [ ] Error case: series with fewer than 3 runs -> exit code 1, message: `"Series '<id>' has <n> run(s), need at least 3 for trend analysis"`
- [ ] Error case: runs missing `sequenceIndex` in setup -> exit code 1, message: `"Run <runId> in series '<id>' is missing sequenceIndex"`

### Phase 3: Report rendering

#### Markdown output

Render the `ComparisonReport` as a readable markdown document.

**Acceptance criteria:**
- [ ] Summary mode produces a table with one row per setup: `| Setup | Runs | Cosine (mean +/- stddev) | ROUGE-L (mean +/- stddev) | Fabrication Rate | Distinct Rate | Cost (mean) |`
- [ ] AB mode produces: (1) the summary table, (2) a delta section with direction arrows (lower cosine = better), (3) significance assessment in plain language
- [ ] Compounding mode produces: (1) a per-step table `| Step | Date | RunID | Cross-Tenant Cosine | ROUGE-L | Narrative-State Delta | Fabrication | `, (2) trend slope and significance, (3) a plain-language verdict: "Editorial memory shows compounding divergence" / "No clear trend" / "Divergence is degrading"
- [ ] Direction indicators: use `v` (down arrow) for improving metrics (lower similarity), `^` for worsening, `-` for neutral
- [ ] All numbers formatted to 3 decimal places
- [ ] Report header includes generation timestamp, mode, filters applied, and total runs analyzed
- [ ] When `--json` flag is set, write `ComparisonReport` as JSON to `<out-path>.json` (or `comparison-report.json` if `--out` not specified)

---

## 5. Implementation Plan (Sprint Contracts)

### Phase 1

- [ ] **Task 1:** Scaffold CLI entry point and argument parsing
  - **Files:** `packages/api/src/benchmark/uniqueness-poc/compare.ts`
  - **Depends on:** Nothing
  - **Verify:** `bun run packages/api/src/benchmark/uniqueness-poc/compare.ts --help` prints usage without errors

- [ ] **Task 2:** Implement run loader with filtering and grouping
  - **Files:** `packages/api/src/benchmark/uniqueness-poc/compare.ts`
  - **Depends on:** Task 1
  - **Verify:** `bun run packages/api/src/benchmark/uniqueness-poc/compare.ts summary` loads all runs from `uniqueness-poc-runs/`, groups by setup (all "unknown" for pre-manifest runs), prints count per group to stderr

- [ ] **Task 3:** Implement metric extraction from RunResult
  - **Files:** `packages/api/src/benchmark/uniqueness-poc/compare.ts`
  - **Depends on:** Task 2
  - **Verify:** Summary mode outputs a markdown table with correct cosine/ROUGE-L/fabrication stats for the "unknown" group. Verify one row's mean cosine against manual calculation from 2-3 runs.

- [ ] **Task 4:** Implement A/B delta computation with significance
  - **Files:** `packages/api/src/benchmark/uniqueness-poc/compare.ts`
  - **Depends on:** Task 3
  - **Verify:** `bun run ... ab --setup-a narrative-state --setup-b editorial-memory` produces delta table with direction indicators and significance note. (Requires at least 2 runs per setup with manifest metadata — can test with manually tagged runs.)

- [ ] **Task 5:** Add `--json` output mode
  - **Files:** `packages/api/src/benchmark/uniqueness-poc/compare.ts`
  - **Depends on:** Task 3
  - **Verify:** `bun run ... summary --json --out /tmp/test-report.md` writes both `/tmp/test-report.md` and `/tmp/test-report.json`. JSON parses without errors and matches the `ComparisonReport` interface.

### Phase 2

- [ ] **Task 6:** Implement compounding trend analysis
  - **Files:** `packages/api/src/benchmark/uniqueness-poc/compare.ts`
  - **Depends on:** Task 3
  - **Verify:** `bun run ... compounding --series test-series` produces a trend table and slope computation. Test with synthetic data: 5 runs with sequenceIndex 0-4, manually set cosine values to verify slope calculation.

- [ ] **Task 7:** Implement linear regression and R-squared
  - **Files:** `packages/api/src/benchmark/uniqueness-poc/compare.ts`
  - **Depends on:** Task 6
  - **Verify:** Unit-level: `linearRegression([{x:0,y:0.8},{x:1,y:0.7},{x:2,y:0.6}])` returns `slope: -0.1, rSquared: 1.0`. Inline test at bottom of file guarded by `import.meta.main`.

### Phase 3

- [ ] **Task 8:** Markdown report renderer — summary mode
  - **Files:** `packages/api/src/benchmark/uniqueness-poc/compare.ts`
  - **Depends on:** Task 3
  - **Verify:** Output is valid markdown. Table renders correctly when viewed in a markdown previewer. Numbers are 3 decimal places.

- [ ] **Task 9:** Markdown report renderer — AB mode
  - **Files:** `packages/api/src/benchmark/uniqueness-poc/compare.ts`
  - **Depends on:** Tasks 4, 8
  - **Verify:** AB report includes summary table, delta section with arrows, and significance note.

- [ ] **Task 10:** Markdown report renderer — compounding mode
  - **Files:** `packages/api/src/benchmark/uniqueness-poc/compare.ts`
  - **Depends on:** Tasks 6, 8
  - **Verify:** Compounding report includes per-step table, slope, and plain-language verdict.

- [ ] **Task 11:** Typecheck and integration test
  - **Files:** All files from above
  - **Depends on:** Tasks 1-10
  - **Verify:** `bun run typecheck` passes. `bun run packages/api/src/benchmark/uniqueness-poc/compare.ts summary` runs against the real `uniqueness-poc-runs/` directory and produces a valid report.

---

## 6. Constraints

- **Runtime:** Bun. No Node-specific APIs. Import paths use `.js` extensions per project convention.
- **No external stats libraries.** The statistical methods (mean, stddev, linear regression) are trivial to implement inline. Pulling in a dependency for this is not justified.
- **No LLM calls.** The comparator is pure computation over persisted data.
- **Strict TypeScript.** No `any` types. All interfaces defined in the same file or imported from `types.ts`.
- **Single file.** The comparator is a CLI script, not a library. Keep it in one file (`compare.ts`) until it exceeds ~500 lines, then split.
- **Backward compatibility.** Must handle runs from before the run-manifest spec (no `setup` field). These are grouped as "unknown" and excluded from A/B mode but included in summary mode.

---

## 7. Out of Scope

- **Visualization / charts.** ASCII sparklines and proper chart rendering are deferred. The JSON output can feed into external tools (Recharts in the playground, for example).
- **Automated run tagging.** The comparator reads setup metadata; it does not write it. Backfilling old runs with setup metadata is the run-manifest spec's responsibility.
- **Proper statistical tests (t-test, Mann-Whitney).** With N<20 runs per group, proper hypothesis testing adds complexity without adding confidence. The variance-ratio heuristic is honest about its limitations. Upgrade path: when run count exceeds 20, replace with Welch's t-test.
- **Intra-tenant (Stage 2) metrics.** The comparator focuses on cross-tenant differentiation (Stage 6) and narrative-state impact (Stage 7). Stage 2 intra-tenant metrics are noise for the A/B and compounding questions.
- **Per-persona drill-down.** The `--persona` filter restricts which pairs are included, but the report does not break down results per persona. Add this when the persona set stabilizes.
- **Web UI.** This is a CLI tool. A playground integration can consume the `--json` output later.

---

## 8. Open Questions

| # | Question | Impact | Decision needed by |
|---|----------|--------|-------------------|
| 1 | Should the run-manifest spec support retroactive tagging of old runs (backfill command), or should old runs be manually tagged? | Determines whether existing ~15 runs can participate in A/B comparisons immediately | Before Phase 1 Task 4 |
| 2 | What are the actual setup IDs to use? Candidates: `baseline` (no memory), `narrative-state` (filesystem NarrativeStateStore), `editorial-memory` (pgvector editorial memory). Should `conformance-on` / `conformance-off` be a separate setup or a tag? | Affects grouping logic and how many groups we expect | Before Phase 1 Task 4 |
| 3 | For compounding analysis, what constitutes "intra-tenant continuity holds"? The spec checks that fabrication rate stays flat, but should it also verify that the same persona's outputs across the series maintain thematic coherence? That would require an LLM call, which violates the "no LLM" constraint. | Determines whether Phase 2 is purely metric-based or needs a judge | Before Phase 2 |
