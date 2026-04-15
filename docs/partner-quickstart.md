# Partner Quickstart — wordwideAI

One-page onboarding. Read this first, then read [`docs/co-vibe-protocol.md`](https://github.com/agaleraib/claude-harness/blob/v0.1-co-vibe/docs/co-vibe-protocol.md) for the full protocol.

---

## Your assignment

**Spec:** [`docs/specs/2026-04-15-sources-rss-mvp.md`](./specs/2026-04-15-sources-rss-mvp.md) — `@wfx/ingest` RSS Adapter MVP
**Parent spec (read §1–§5 only):** [`docs/specs/2026-04-07-data-sources.md`](./specs/2026-04-07-data-sources.md)
**Workstream:** B (`@wfx/sources`)
**Package you will build in:** `packages/sources/` (new, isolated — no imports into `packages/api/`, `packages/web/`, or `packages/playground/`)
**Integrator (review + merge):** Albert
**Escalation channel:** Telegram — contact Albert at `<!-- FILL: @albert-telegram-handle -->` (replace before sending this doc).

---

## One-time setup

Run these in order. All commands copy-paste verbatim.

### 1. Clone the project repo

```bash
git clone https://github.com/agaleraib/wordwideAI.git wordwideAI
cd wordwideAI
```

### 2. Install Claude Code

If not already installed: https://claude.com/product/claude-code

### 3. Install claude-harness pinned to the shared tag

```bash
cd ~
git clone https://github.com/agaleraib/claude-harness.git
cd claude-harness
git checkout v0.1-co-vibe
```

Install user-level agents and skills from the tag:

```bash
mkdir -p ~/.claude/agents
cp .claude/agents/code-reviewer.md ~/.claude/agents/
cp .claude/agents/spec-planner.md ~/.claude/agents/
cp .claude/agents/project-tracker.md ~/.claude/agents/

for skill in session-start session-end micro park commit project-init \
             setup-harness deploy-check api-smoke-test migration-check a11y-check; do
  mkdir -p ~/.claude/skills/$skill
  cp skills/$skill/SKILL.md ~/.claude/skills/$skill/
done
```

**Do not `git pull` in `~/claude-harness` afterwards.** Stay on tag `v0.1-co-vibe` until Albert ships a new tag.

### 4. Verify project-level harness files are already in the repo

The following are **committed to the repo** — you already have them after cloning. **Do not** run `/setup-harness` or `/project-init`; they would overwrite files Albert has tuned.

Verify they exist:

```bash
cd ~/wordwideAI
ls .harness-profile CLAUDE.md criteria/ procedures/
```

All four should be present. If anything is missing, ping Albert on Telegram before continuing.

### 5. Create your branch

```bash
cd ~/wordwideAI
git checkout master
git pull
git checkout -b workstream-b-sources-rss-mvp master
```

**Do not branch off any existing `workstream-b-*` branch.** Start from `master`.

### 6. Create your personal plan file

Create `docs/plan-workstream-b.md` on your branch. This is your working plan file.
**Do not edit `docs/plan.md`** (that's the shared plan on master — integrator-only).

Commit the new file:

```bash
git add docs/plan-workstream-b.md
git commit -m "chore: add workstream-b plan file"
```

### 7. Read before coding

- [`docs/specs/2026-04-15-sources-rss-mvp.md`](./specs/2026-04-15-sources-rss-mvp.md) — full assignment
- [`docs/specs/2026-04-07-data-sources.md`](./specs/2026-04-07-data-sources.md) — §1–§5 only (frozen contracts)
- [`CLAUDE.md`](../CLAUDE.md) at repo root — TypeScript strict, no `any`, staging discipline, no `git add -A`
- [`docs/co-vibe-protocol.md`](https://github.com/agaleraib/claude-harness/blob/v0.1-co-vibe/docs/co-vibe-protocol.md) — full protocol

### 8. Gate with Albert

Screen-share your first `/session-start` + `/micro` on Telegram. If that works, you're cleared to work solo.

---

## Daily loop

```bash
cd ~/wordwideAI
git checkout master && git pull
git checkout workstream-b-sources-rss-mvp
git merge master
```

Then in Claude Code:

1. `/session-start` — sets today's goal from your plan file.
2. `/micro` — 30–60 min focused block on one task from the spec.
3. Write code → run `bun run typecheck` and `bun test`.
4. `/commit` — runs code-reviewer automatically. **If it flags an issue: fix or park. Never dismiss.**
5. When a spec section's "Done when" (§11) is satisfied: push and open a PR.
6. `/session-end`.

### Push and open PR

```bash
git push -u origin workstream-b-sources-rss-mvp
```

Then fill the PR body template below into a scratch file (e.g. `/tmp/pr-body.md` — don't commit it), and open the PR:

```bash
gh pr create --base master \
  --title "workstream-b: <spec section name>" \
  --body-file /tmp/pr-body.md
```

---

## PR body template

```markdown
## Spec
[`docs/specs/2026-04-15-sources-rss-mvp.md`](./docs/specs/2026-04-15-sources-rss-mvp.md) — <section name>

## Done when
<paste the exact "Done when" line from the spec>

## What changed
- <2–3 plain-language bullets>

## How I tested
- [ ] `bun run typecheck` clean
- [ ] `bun test` passes (integration skipped with `WFX_SKIP_LIVE_TESTS=1` if no network)
- [ ] CLI smoke: `bun run src/cli/fetch.ts fixtures/rss/bbc-business.json --limit 3` prints 3 well-formed Documents

## Parking lot items surfaced
- <anything you parked during this work, or "none">

## Unknowns / questions for reviewer
- <anything you're unsure about, or "none">
```

---

## Hard rules — do not break

- **Never `git push origin master`.** Only your own branch.
- **Never force-push.**
- **Never merge your own PR.** Albert merges.
- **Never edit** `docs/plan.md`, `parking_lot.md`, or `.harness-profile` on master. Park in the PR body; Albert transcribes.
- **Never run `/deploy-check`.**
- **Never touch `playground-live`** — that's the promotion branch.
- **Stuck more than 20 minutes?** Park it, ping Albert on Telegram, move on to another task.

---

## Stop and ping Albert on Telegram before you

- Add a database migration or schema change.
- Add any new npm/bun dependency beyond those named in spec §7 (e.g. `rss-parser`, `fast-xml-parser`, `cheerio`, `sanitize-html`, `turndown` — choose one per category and document the choice).
- Change anything in `.harness-profile`, `package.json` (outside adding your new package to the workspace list), CI files, or anything under `infra/`.
- Delete or skip a test.
- See a `code-reviewer` finding you don't understand.

---

## Definition of done (copied from spec §11)

A reviewer can cold-clone the repo and run:

```bash
cd packages/sources
bun install
bun run src/cli/fetch.ts fixtures/rss/bbc-business.json --limit 3
```

And see three well-formed `Document` objects in stdout. Then:

```bash
bun run typecheck      # no errors
bun test               # unit + integration (integration skipped if WFX_SKIP_LIVE_TESTS=1)
```

All pass. `packages/sources/` builds standalone — no imports into `packages/api/`, `packages/web/`, or `packages/playground/`.

---

## Communication rhythm

- **Start of day:** Telegram message to Albert — what task, any blockers. ~2 lines.
- **End of day:** PR link if opened, or "still in progress, here's where I am."
- **Async questions:** Telegram. Don't wait for a sync if you're blocked > 20 min — park and message.
