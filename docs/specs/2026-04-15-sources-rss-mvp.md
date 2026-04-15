# `@wfx/ingest` — RSS Adapter MVP

**Date:** 2026-04-15
**Status:** Ready to build — scoped for a collaborator with no prior context on the rest of the repo.
**Parent spec:** [`2026-04-07-data-sources.md`](./2026-04-07-data-sources.md) — read §1–§5 for package goals, terminology, and the full `Document` / `Source` / `SourceConfig` contracts this MVP implements against.
**Workstream:** B — `@wfx/sources`
**Owners:** Albert (review), collaborator (build)

---

## 1. Goal

Stand up `packages/sources/` with a **working RSS adapter**, just enough shared scaffolding to host it, and a test harness that proves it against real public feeds. Nothing else.

This MVP is deliberately narrow so the package gets a real first shape without committing to the full parent spec's surface. Once the RSS adapter ships, the HTML / YouTube / Reddit / Playwright / Apify adapters can land as independent PRs against the same scaffolding.

---

## 2. In scope

- Create `packages/sources/` workspace package (TypeScript, Bun).
- Implement shared types from the parent spec §5.1–§5.2: `Document`, `Provenance`, `Source`, `FetchContext`, `HealthStatus`. **Do not change the shapes** — copy them verbatim from the parent.
- Implement one adapter: `RssAdapter`, conforming to `Source<RssConfig>`.
- Zod schema for `RssConfig` (adapter-specific), validated at construction.
- Minimal `FetchContext` stub for local use — `alreadySeen` always returns `false`, `log` is a thin console wrapper, `signal` is passed through.
- A CLI test harness: `bun run src/cli/fetch.ts <sourceConfig.json>` that loads a JSON config, runs the adapter, prints `Document[]` as JSON.
- 3–5 real public RSS feeds as fixtures in `packages/sources/fixtures/rss/`.
- Unit tests: parse a known-good XML payload → assert `Document` fields.
- Integration test: hit one real feed → assert ≥1 document, all with required fields populated.

## 3. Explicitly out of scope

Everything else in the parent spec. Do **not** build these — they land in follow-up specs:

- HTML, YouTube, Reddit, Playwright, Apify adapters.
- `DocumentStore` (SQLite, dedup memory, TTL garbage collection).
- `SourceConfigStore` interface + implementations.
- `runSource()` top-level entry point (rate-limiting / retry / robots.txt primitives wrapping the adapter).
- Cross-run dedup persistence.
- Multi-tenant scope handling (tenantId routing — for MVP always `scope: "shared"`, `tenantId: undefined`).
- Consumer integration with FinFlow or Robuust.
- Any `@wfx/sources` → npm publishing setup.

If the collaborator is tempted to build any of these "while they're there", **don't** — each is its own PR against a future sub-spec.

---

## 4. Package layout

```
packages/sources/
├── package.json                    # name: @wfx/sources, private: true
├── tsconfig.json                   # extends the api package's strict config
├── src/
│   ├── types.ts                    # Document, Provenance, Source, FetchContext, HealthStatus
│   ├── adapters/
│   │   └── rss.ts                  # RssAdapter + RssConfig (Zod schema)
│   ├── context/
│   │   └── stub-fetch-context.ts   # StubFetchContext — local-use only
│   └── cli/
│       └── fetch.ts                # CLI entry: bun run src/cli/fetch.ts <config.json>
├── fixtures/
│   └── rss/
│       ├── ft-markets.json         # real public feed configs
│       ├── bbc-business.json
│       ├── ecb-press.json
│       └── sample-atom.xml         # captured XML payload for unit tests
└── test/
    ├── rss-parser.test.ts          # unit: parse captured XML → Document
    └── rss-live.test.ts            # integration: hit real feed, assert shape
```

No other files. If something doesn't fit these paths, raise it — don't invent new directories.

---

## 5. Frozen contracts from the parent spec

Copy these shapes verbatim into `src/types.ts`. Do not modify. If something needs to change, stop and raise it before diverging.

### 5.1 `Document` (parent spec §5.1)

All fields as specified. For MVP scope, always set:
- `tenantId: undefined`
- `bodyFormat: "markdown"` (or `"text"` — RSS content is usually HTML; cleaning is §7 below)
- `provenance.adapter: "rss"`
- `provenance.method: "GET"`
- `provenance.rawHash` computed via SHA-256 of the raw XML response body

### 5.2 `Source<TConfig>` (parent spec §5.2)

The `RssAdapter` implements this interface. For MVP:
- `scope: "shared"` hardcoded.
- `tenantId: undefined` always.
- `healthCheck()` not required (skip; parent spec marks it optional).

### 5.3 `FetchContext` (parent spec §5.2)

The stub provides:
- `alreadySeen(): boolean` → always `false` (real dedup lives in the future `DocumentStore`).
- `log`: `{ debug, info, warn, error }` — each maps to `console.*` with a `[adapter:rss]` prefix.
- `signal`: passed through from the CLI (fresh `AbortController` if none provided).

---

## 6. `RssConfig` (adapter-specific)

```ts
import { z } from "zod";

export const RssConfigSchema = z.object({
  /** RSS 2.0 / Atom feed URL. */
  url: z.string().url(),

  /**
   * Minimum body length (characters) after cleaning. Items below this
   * are dropped rather than yielded — some feeds publish headlines-only.
   * Default 0 (keep everything).
   */
  minBodyLength: z.number().int().nonnegative().default(0),

  /**
   * When the feed only provides a summary, some consumers need the full
   * article. For MVP: always false. Full-article extraction lands with
   * the HTML adapter MVP. This field is accepted for forward compat
   * but MUST be false in MVP; reject otherwise.
   */
  extractFullArticle: z.literal(false).default(false),

  /**
   * User-Agent string sent with the GET. Default respects the parent
   * spec's default identity.
   */
  userAgent: z
    .string()
    .default("wfx-ingest/0.1 (+https://wordwidefx.com/bot)"),
});

export type RssConfig = z.infer<typeof RssConfigSchema>;
```

The full shared envelope (`rateLimit`, `retry`, `retention`, `robotsTxt`) from parent spec §5.3 is **not** validated in MVP — the adapter works standalone without a runner. Those primitives land with the `runSource()` entry point in a later sub-spec.

---

## 7. Parsing behaviour

- **Parser:** use a well-maintained library (e.g. [`rss-parser`](https://www.npmjs.com/package/rss-parser) or `fast-xml-parser` + custom mapping). Collaborator's choice — stick with one across both RSS 2.0 and Atom. Document the choice in `src/adapters/rss.ts` top-comment.
- **HTML cleaning:** feed items almost always contain HTML. Use `cheerio` or `sanitize-html` to strip tags into plain text for `body`, or convert to markdown via [`turndown`](https://www.npmjs.com/package/turndown) if `bodyFormat: "markdown"`. Pick one, document the choice. No raw HTML in `body`.
- **`externalId` resolution order:** `<guid isPermaLink="false">` → `<guid>` → `<link>` → hash of (`title` + `pubDate`). Document the fallback the item actually took in `meta.externalIdSource` for debugging.
- **`publishedAt`:** parse `<pubDate>` (RSS) or `<published>` / `<updated>` (Atom). Fallback to `new Date()` at fetch time *only* if the feed provides none — log a warning when that happens.
- **`authors`:** parse `<author>` / `<dc:creator>` / Atom `<author><name>`. Empty array acceptable.
- **`tags`:** parse `<category>` items. Empty array acceptable.
- **`language`:** if the feed root declares it (`<language>` or `xml:lang`), use it; otherwise leave undefined.
- **Size limit:** if the body after cleaning > 1 MB, truncate to 1 MB and set `meta.truncated: true`. Document in the log.

---

## 8. CLI harness

`packages/sources/src/cli/fetch.ts`:

```bash
bun run src/cli/fetch.ts fixtures/rss/ft-markets.json
```

Reads the JSON config, instantiates `RssAdapter`, runs `fetch()`, prints the yielded `Document[]` as pretty JSON to stdout. Errors go to stderr; exit code 1 on failure.

Minimal flags:
- `--limit N` — yield at most N documents and stop.
- `--no-body` — omit `body` and `provenance.raw` from the output (readability when piping to `jq`).
- `--signal-timeout-ms N` — abort fetch after N ms (default 30000).

No other flags. If the collaborator wants more, raise it.

---

## 9. Fixtures — test feeds

Pick 3–5 real **financial** public feeds. All of the suggestions below are public, no auth required, and cover the format + edge cases the adapter needs to handle.

1. **FT Markets** (RSS) — `https://www.ft.com/markets?format=rss` — finance, often has paywalled summary-only bodies (good edge case for `minBodyLength` handling).
2. **BBC Business** (RSS) — `https://feeds.bbci.co.uk/news/business/rss.xml` — clean, reliable, full-text bodies.
3. **ECB Press Releases** (RSS) — `https://www.ecb.europa.eu/press/pr/html/index.en.rss` — central bank, slow cadence, tests the "feed with few items, dense text" path.
4. **Federal Reserve Board — Press Releases** (RSS) — `https://www.federalreserve.gov/feeds/press_all.xml` — US central bank counterpart to ECB.
5. **SEC EDGAR — Latest Filings** (Atom) — `https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=&company=&dateb=&owner=include&count=40&output=atom` — proves the **Atom** code path, genuinely financial, high cadence (good for `--limit` testing).

**URL verification is mandatory.** These URLs were captured at spec-write time (2026-04-15) and feeds move or break. Before committing any fixture JSON, run the CLI against it and confirm a 200 with parseable payload. If a URL 404s or changes shape, swap for an equivalent — log the substitution in the fixture's JSON `description` field.

Each fixture is a `SourceConfig` JSON (parent spec §5.3 shared envelope, with `config` filled from §6 above). Also capture **one** feed's raw XML payload into `fixtures/rss/sample-atom.xml` (~50 KB) — preferably the SEC EDGAR response to ensure the Atom path is exercised — as the unit test's input, to avoid network dependency for unit tests.

---

## 10. Tests

### 10.1 Unit — `test/rss-parser.test.ts`
- Load `fixtures/rss/sample-atom.xml`.
- Parse via the adapter's internal parser function (expose it from `rss.ts` for testing).
- Assert: exactly-expected number of items, each with required `Document` fields populated and correct types.
- Assert: `externalId` fallback order behaves correctly when `<guid>` is absent (test with a hand-edited variant).
- Assert: `body` contains no raw HTML tags.

### 10.2 Integration — `test/rss-live.test.ts`
- Skip if `WFX_SKIP_LIVE_TESTS=1` (for CI without network).
- Fetch one of the fixture configs.
- Assert: ≥1 document yielded; each passes a `Document` Zod schema; `provenance.rawHash` is a 64-char hex string; `provenance.status` is 200.
- Assert: all `externalId` values in the yielded batch are unique.

### 10.3 Runner
- Use `bun test`. No vitest / jest — match the rest of the repo (check `packages/api` for the pattern).

---

## 11. Acceptance criteria (definition of done)

A reviewer can cold-clone the repo and run:

```bash
cd packages/sources
bun install
bun run src/cli/fetch.ts fixtures/rss/bbc-business.json --limit 3
```

And see three well-formed `Document` objects printed to stdout, each with:
- Non-empty `title`, `body` (≥ `minBodyLength` chars, no HTML tags), `externalId`, `publishedAt` (valid Date), `provenance.fetchedAt`, `provenance.rawHash`.
- `sourceId: "bbc-business"` matching the config `id`.
- `provenance.adapter: "rss"`, `provenance.method: "GET"`, `provenance.status: 200`.

All checks pass:
```bash
bun run typecheck      # no errors, strict mode, no `any`
bun test               # unit + integration (integration skipped if WFX_SKIP_LIVE_TESTS=1)
```

Repo-wide:
- `packages/sources/` builds standalone — no imports into `packages/api/` or `packages/web/` or `packages/playground/`.
- No changes to any file outside `packages/sources/` except a single line addition to the root workspace list if there is one (check `package.json` / `bun.lockb` at repo root first).

---

## 12. Non-technical notes for the collaborator

- **If in doubt, keep it out.** The parent spec is long for a reason — there's a lot of forward-planning in it. Your job is to ship the MVP only; everything else is someone else's problem. When a feature feels like "well, while I'm here I could also…", stop.
- **Don't change frozen contracts.** If `Document` / `Source` / `FetchContext` feel wrong for RSS, raise it before diverging. The whole point of the parent spec is that these shapes hold across adapters.
- **Don't introduce new dependencies without flagging.** RSS-parser choice, HTML-clean choice, markdown-convert choice — all noted in this doc. Beyond those, ask.
- **Strict TS, no `any`.** Repo-wide rule; see root `CLAUDE.md`.
- **No emojis in code/comments/commit messages** unless explicitly requested.
- **Commits:** one commit per logical step (scaffolding / types / adapter / CLI / fixtures / tests), staged file-by-file. `git add -A` is prohibited by repo conventions (root `CLAUDE.md`). Never merge with `--ff`; use `--no-ff`.

---

## 13. Hand-off checklist

Before first commit:
- [ ] Read parent spec §1–§5 ([`2026-04-07-data-sources.md`](./2026-04-07-data-sources.md)).
- [ ] Read root `CLAUDE.md` (repo conventions — TypeScript strict, no `any`, staging discipline).
- [ ] Confirm Bun is installed (`bun --version`) and `bun test` works against `packages/api/`.
- [ ] Skim one existing `packages/api/src/routes/*.ts` and one `packages/api/src/pipeline/*.ts` to see the house style (naming, error handling, type narrowing, Zod usage). The RSS adapter should feel like it belongs next to them.

Before opening a PR:
- [ ] All acceptance criteria from §11 pass.
- [ ] `docs/specs/2026-04-07-data-sources.md` is **unmodified** (this MVP spec is the working doc; the parent stays frozen for reference).
- [ ] PR description links to this MVP spec and the parent spec.

---

## 14. Parent spec alignment

Every decision in this MVP traces to a section in the parent. If anything here contradicts the parent, the parent wins — flag the conflict for resolution before building.

| This MVP section | Parent spec reference |
|---|---|
| §5 frozen contracts | Parent §5.1 `Document`, §5.2 `Source` / `FetchContext` / `HealthStatus` |
| §6 `RssConfig` | Parent §5.3 shared envelope — `config` field only in MVP |
| §7 parsing behaviour | Parent §3 terminology (`Document` definition) + parent §5.1 field semantics |
| §3 out-of-scope list | Parent §2 non-goals + parent §4 architecture (DocumentStore, primitives, runner) |
| §11 acceptance criteria | Parent §1 goal (emit normalized documents for downstream consumption) |

See the full parent spec for the long-term vision: [`docs/specs/2026-04-07-data-sources.md`](./2026-04-07-data-sources.md).
