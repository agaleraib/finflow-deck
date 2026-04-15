# Parking Lot

Drop side-quests and unplanned issues here during micro-sessions instead of derailing.

Format: `- [YYYY-MM-DD] <one-line description> (source: micro-session goal X)`

## Open
- [2026-04-12] Refactor `runCrossTenantMatrix()` from ~13 positional params to a named options object (source: commit review, Task 6)
- [2026-04-13] PoC process hangs after run completes when using `--editorial-memory` with Postgres — postgres.js connection not closed. Requires manual kill. Need `closeDb()` call or `process.exit()` after run finishes in index.ts. (source: A/B validation run)
- [2026-04-15] `contradiction-detector` Haiku call returns response where `contradictions` field is `undefined`, failing Zod validation (`expected array, received undefined`). Caught by fallback (empty array), run continues but contradictions are silently dropped on every call. Likely tool_use response shape mismatch or the LLM emitting the tool with no args. Fires ~4-8× per PoC run. (source: fidelity re-run + sequence run)

## Resolved
- [2026-04-13] ~~Bun 100% CPU spin~~ — bypassed by running PoC under Node.js/tsx. Lazy Bun.spawn import in claude-cli.ts, `poc:node*` scripts added. Full --editorial-memory run completed successfully under Node.
- [2026-04-15] ~~"Maximum call stack size exceeded" in `getContext`~~ — infinite recursion in `context-assembler.ts` truncation loop (`slice(-2)` stabilised at length 2, recursed forever). Fixed in 028bdd8 by using `slice(1)` so the array strictly shrinks each call. Validated: 4/4 personas now get memory injected in Stage 6. Affected 3/4 personas, not just northbridge-wealth.
