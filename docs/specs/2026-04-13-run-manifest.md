# Run Manifest — Capture exact setup/configuration for every uniqueness PoC run

## Overview

Every uniqueness PoC run produces a `report.md` and `raw-data.json`, but neither records the configuration that produced the result. This makes it impossible to compare runs, reproduce results, or understand what changed between two runs months apart.

This spec adds a `RunManifest` object that captures the full environment and configuration of each run. It is embedded in `raw-data.json` as `result.manifest` and rendered as a human-readable "Setup" section in `report.md` between the header and the verdict.

## Prior Work

Builds on: [Content Uniqueness](2026-04-07-content-uniqueness.md), [Narrative State Persistence](2026-04-08-narrative-state-persistence.md), [Editorial Memory](2026-04-12-editorial-memory.md)
Assumes: existing `RunResult` type, `persistRun()` flow, `renderReport()` layout, CLI flag parsing in `index.ts`
Changes: extends `RunResult` with a `manifest` field; inserts a section in `report.md`

## Data Model

### Entity: RunManifest (Zod schema, not DB entity)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| version | `1` (literal) | NOT NULL | Schema version for forward compat |
| timestamp | string (ISO 8601) | NOT NULL | Run start time |
| gitCommitHash | string \| null | — | Short hash from `git rev-parse --short HEAD`, null if not a git repo |
| source | `"cli"` \| `"dashboard"` | NOT NULL | How the run was triggered |
| runtime | `{ name: string; version: string }` | NOT NULL | e.g. `{ name: "bun", version: "1.2.9" }` |
| memoryBackend | `"editorial-memory-postgres"` \| `"editorial-memory-inmemory"` \| `"narrative-state"` \| `"none"` | NOT NULL | Which memory system was active |
| editorialMemoryState | `{ articleCountByTenant: Record<string, number> }` \| null | — | Snapshot of editorial memory at run start; null when memoryBackend is not editorial-memory |
| stagesEnabled | `{ stage1: true; stage2: true; stage3: true; stage4: boolean; stage5: boolean; stage6: boolean; stage7: boolean }` | NOT NULL | Which stages actually ran |
| cliFlags | string[] | NOT NULL | Raw flags passed, e.g. `["--full", "--editorial-memory"]` |
| fixtureId | string | NOT NULL | Fixture filename stem or sequence step id |
| eventIds | string[] | NOT NULL | All event ids consumed (1 for single, 2+ for sequence) |
| personaIds | string[] | NOT NULL | Persona ids used in Stage 5/6/7 (empty if stages skipped) |
| identityIds | string[] | NOT NULL | Identity ids used in Stage 2 |
| sequenceId | string \| null | — | Non-null when run is part of a `--sequence` |
| sequenceStep | number \| null | — | 1-indexed step within the sequence |
| sequenceStepCount | number \| null | — | Total steps in the sequence |

## Requirements

### Phase 1: Manifest schema + collection + persistence

#### R-1: Zod schema in types.ts
**Acceptance criteria:**
- [ ] `RunManifestSchema` is exported from `types.ts` as a `z.object(...)` with all fields above
- [ ] `RunManifest` type is exported as `z.infer<typeof RunManifestSchema>`
- [ ] `bun run typecheck` passes with the new type

#### R-2: Manifest collection at run start
**Acceptance criteria:**
- [ ] `runUniquenessPoc()` in `runner.ts` receives manifest data via `RunOptions` and attaches it to the returned `RunResult`
- [ ] The CLI entry point (`index.ts`) constructs the manifest before calling `runUniquenessPoc()`, populating all fields from the parsed args, loaded fixtures, and runtime introspection
- [ ] `gitCommitHash` is collected via `execSync("git rev-parse --short HEAD")` wrapped in try/catch (null on failure)
- [ ] `runtime.name` is `"bun"` when `typeof Bun !== "undefined"`, `"node"` otherwise; `runtime.version` is `process.version`
- [ ] `editorialMemoryState` queries the store's article count per tenant at run start (when editorial memory is active); does not add a new method to the store interface -- uses existing `getContext` or a count query
- [ ] Error case: if git is unavailable, `gitCommitHash` is null (no crash)
- [ ] Edge case: `--sequence` runs set `sequenceId`, `sequenceStep`, `sequenceStepCount` on each step's manifest

#### R-3: Manifest in raw-data.json
**Acceptance criteria:**
- [ ] `RunResult.manifest` field is typed as `RunManifest` (required, not optional)
- [ ] `raw-data.json` written by `persistRun()` includes the manifest (automatic, since it serializes the full `RunResult`)
- [ ] Existing raw-data.json files without a manifest field do not break the `analyze-uniqueness-run` skill (the skill should handle missing manifest gracefully)

#### R-4: Human-readable Setup section in report.md
**Acceptance criteria:**
- [ ] `renderReport()` renders a `## Setup` section immediately after the header block (run ID, timestamps, cost) and before the verdict banner
- [ ] The Setup section includes: git commit, runtime, memory backend, stages enabled (as a comma-separated list of stage numbers), fixture id, persona ids, CLI flags
- [ ] For `--sequence` runs, the Setup section also shows sequence id and step position
- [ ] The section is a compact key-value block (not a table), no longer than 15 lines

### Phase 2: Dashboard source support

#### R-5: Playground/dashboard manifest population
**Acceptance criteria:**
- [ ] The playground HTTP route (`routes/poc.ts`) populates `source: "dashboard"` when triggering runs
- [ ] CLI flags field is `[]` for dashboard-triggered runs (no CLI involved)
- [ ] All other manifest fields are populated identically to CLI runs

## Implementation Plan (Sprint Contracts)

### Phase 1

- [ ] **Task 1:** Add `RunManifestSchema` and `RunManifest` type to types.ts
  - **Files:** `packages/api/src/benchmark/uniqueness-poc/types.ts`
  - **Depends on:** Nothing
  - **Verify:** `bun run typecheck` passes; `RunManifestSchema.parse({...})` validates a well-formed object and rejects a malformed one

- [ ] **Task 2:** Add `manifest` field to `RunResult` interface
  - **Files:** `packages/api/src/benchmark/uniqueness-poc/types.ts`
  - **Depends on:** Task 1
  - **Verify:** `bun run typecheck` fails until all call sites constructing `RunResult` supply a manifest (this is the forcing function)

- [ ] **Task 3:** Add `manifest` to `RunOptions` and wire it through `runUniquenessPoc()`
  - **Files:** `packages/api/src/benchmark/uniqueness-poc/runner.ts`
  - **Depends on:** Task 2
  - **Verify:** `bun run typecheck` passes; the returned `RunResult` includes the manifest from options

- [ ] **Task 4:** Build manifest in CLI entry point and pass to runner
  - **Files:** `packages/api/src/benchmark/uniqueness-poc/index.ts`
  - **Depends on:** Task 3
  - **Verify:** Run `bun run packages/api/src/benchmark/uniqueness-poc/index.ts iran-strike --full --editorial-memory` (dry: just check typecheck). Inspect the resulting `raw-data.json` -- it contains a `manifest` object with all fields populated. `gitCommitHash` is a 7-char hex string.

- [ ] **Task 5:** Render Setup section in `renderReport()`
  - **Files:** `packages/api/src/benchmark/uniqueness-poc/report.ts`
  - **Depends on:** Task 2
  - **Verify:** The generated `report.md` contains a `## Setup` section between the header and the verdict, listing git commit, runtime, memory backend, stages, fixture, personas, and CLI flags

- [ ] **Task 6:** Handle sequence runs -- propagate sequence metadata into per-step manifests
  - **Files:** `packages/api/src/benchmark/uniqueness-poc/index.ts`
  - **Depends on:** Task 4
  - **Verify:** `bun run typecheck` passes; in a sequence run, each step's `raw-data.json` has `sequenceId`, `sequenceStep` (1-indexed), and `sequenceStepCount` populated

### Phase 2

- [ ] **Task 7:** Populate manifest in playground HTTP route
  - **Files:** `packages/api/src/routes/poc.ts`
  - **Depends on:** Task 3
  - **Verify:** `bun run typecheck` passes; playground-triggered runs produce `raw-data.json` with `source: "dashboard"` and `cliFlags: []`

## Constraints

- No new dependencies. `execSync` from `node:child_process` is sufficient for git hash.
- The manifest schema must be forward-compatible: version field allows future schema changes. Old consumers ignore unknown fields; new consumers check `version`.
- Must not slow down run startup by more than 50ms (git hash + memory count are the only async/exec operations).

## Out of Scope

- Manifest-based run comparison tooling (future: a CLI command that diffs two manifests side by side)
- Migrating existing raw-data.json files to include a manifest retroactively
- Adding manifest to the `SoloRunResult` type (can be added later if solo mode survives)

## Open Questions

| # | Question | Impact | Decision needed by |
|---|----------|--------|-------------------|
| 1 | Should `editorialMemoryState` include per-tenant article counts or just a boolean "has prior articles"? | Determines how much we query at startup. Counts are more useful for analysis but require a store method. | Phase 1 -- before Task 4 |
| 2 | Should the `analyze-uniqueness-run` skill auto-diff manifests when comparing two runs? | Would make cross-run analysis much more actionable. | Phase 2 |
