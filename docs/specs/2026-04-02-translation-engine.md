# Translation Engine MVP --- Objective Quality Scoring for Financial Translation

## Problem Statement

Financial translation is subjective by default. Two expert translators will produce different versions of the same report, and "quality" becomes a matter of opinion. For WordwideFX, this is a business problem: clients expect consistent brand voice, accurate terminology, and regulatory compliance across every document, every language, every time.

The Translation Engine solves this by decomposing translation quality into discrete, measurable metrics --- each scored 0-100 --- with configurable thresholds per client. A document either passes or it does not. Subjectivity becomes objectivity.

## System Overview

The engine operates in two modes:

1. **Profile Extraction** --- Feed (base document, client-translated version) pairs into the system. It analyzes differences and extracts a client personalization profile: glossary, tone, formality, sentence structure, regional preferences, and more. This is how we onboard new clients without manual configuration.

2. **Translation + Scoring** --- Given a new base document and a client profile, produce a personalized translation, then score it against every metric in the profile. Each metric must meet its minimum threshold (X). The aggregate score must meet the overall threshold (Y). If either fails, the translation enters a revision loop.

## Metric Taxonomy

Metrics are organized into four categories. Each metric is scored 0-100. Default thresholds are listed but are overridable per client.

### Category 1: Terminology Accuracy

| Metric | What it measures | Extraction method | Scoring method | Default threshold |
|--------|-----------------|-------------------|----------------|-------------------|
| **glossary_compliance** | % of glossary terms correctly translated | Diff source terms against client version to build glossary | Count matched vs. expected terms in output | 95 |
| **term_consistency** | Same source term always maps to same target term | Track all translations of each source term across doc pairs | Flag instances where the same term gets different translations | 90 |
| **untranslated_terms** | Financial terms left in source language without justification | Compare against known-translatable term list | Count unjustified untranslated terms (proper nouns excluded) | 95 |

### Category 2: Style & Voice

| Metric | What it measures | Extraction method | Scoring method | Default threshold |
|--------|-----------------|-------------------|----------------|-------------------|
| **formality_level** | Register match (1=casual, 5=institutional) | Classify register of client reference docs | Classify register of output; penalize deviation from target | 85 |
| **sentence_length_ratio** | Avg sentence length vs. client's preferred range | Compute mean/stddev sentence length from reference docs | Score based on distance from client's mean | 80 |
| **passive_voice_ratio** | % passive constructions vs. client preference | Measure passive voice % in reference docs | Compare output passive % to client's baseline | 80 |
| **brand_voice_adherence** | Compliance with explicit brand rules | Extract brand rules from `_brand_rules` field + reference patterns | Check each rule is followed (e.g., "OANDA" not "Oanda") | 95 |

### Category 3: Structural Fidelity

| Metric | What it measures | Extraction method | Scoring method | Default threshold |
|--------|-----------------|-------------------|----------------|-------------------|
| **formatting_preservation** | Headers, bullets, numbering survive translation | Parse structure of source document | Compare structure of output to source | 90 |
| **numerical_accuracy** | All numbers, prices, percentages preserved exactly | Extract all numeric values from source | Verify each appears in output unchanged | 100 |
| **paragraph_alignment** | Output paragraph count matches source proportionally | Count paragraphs in reference pairs | Compare ratio to expected ratio | 85 |

### Category 4: Linguistic Quality

| Metric | What it measures | Extraction method | Scoring method | Default threshold |
|--------|-----------------|-------------------|----------------|-------------------|
| **fluency** | Natural reading flow in target language | Baseline from reference docs (LLM-judged) | LLM judges fluency of output on 0-100 scale | 85 |
| **meaning_preservation** | Semantic equivalence to source | Align source/target sentences in reference pairs | LLM compares source meaning vs. output meaning | 90 |
| **regional_variant** | Correct Spanish variant (ES-ES vs. ES-LATAM vs. ES-MX) | Detect variant markers in reference docs (vosotros/ustedes, vocabulary) | Check output uses correct variant consistently | 90 |

### Scoring Example

```
Document: EUR/USD Daily Analysis for OANDA (EN -> ES)

  Terminology Accuracy:
    glossary_compliance:      97/100  (threshold: 95) PASS
    term_consistency:         92/100  (threshold: 90) PASS
    untranslated_terms:       98/100  (threshold: 95) PASS

  Style & Voice:
    formality_level:          88/100  (threshold: 85) PASS
    sentence_length_ratio:    82/100  (threshold: 80) PASS
    passive_voice_ratio:      78/100  (threshold: 80) FAIL  <--
    brand_voice_adherence:    100/100 (threshold: 95) PASS

  Structural Fidelity:
    formatting_preservation:  95/100  (threshold: 90) PASS
    numerical_accuracy:       100/100 (threshold: 100) PASS
    paragraph_alignment:      90/100  (threshold: 85) PASS

  Linguistic Quality:
    fluency:                  91/100  (threshold: 85) PASS
    meaning_preservation:     93/100  (threshold: 90) PASS
    regional_variant:         95/100  (threshold: 90) PASS

  AGGREGATE: 92.2/100  (threshold: 88)  PASS
  FAILED METRICS: 1 (passive_voice_ratio: 78 < 80)
  VERDICT: FAIL --- revision required for passive_voice_ratio
```

## Scoring System

### Pass/Fail Logic

1. Compute each metric score (0-100).
2. Check each metric against its per-client threshold X_i.
3. Compute aggregate score: weighted average of all metric scores. Weights are configurable per client; default is equal weight.
4. Check aggregate against overall threshold Y.
5. **PASS** requires: ALL metrics >= their X_i AND aggregate >= Y.
6. **FAIL** triggers: route to specialist correction pipeline (see below).

### Multi-Agent Correction Architecture

#### Why not re-loop the same agent?

Re-prompting a translation agent with "fix your passive voice ratio" produces near-identical output. LLMs anchor to their own text. The same generalist that produced the error lacks the specialized focus to fix it. Instead, failed metrics are routed to specialist agents --- each an expert in one quality domain --- orchestrated by a Quality Arbiter.

#### Agent Roster

| Agent | Model | Role | When invoked |
|-------|-------|------|-------------|
| **Translation Agent** | Opus | Produces the initial translation with full client profile context | Always (first pass) |
| **Scoring Agent** | Opus | Evaluates all 13 metrics, produces structured scorecard | Always (after translation, after each correction) |
| **Quality Arbiter** | Haiku | Reads scorecard, determines correction sequence, detects conflicts between specialists | When any metric fails |
| **Terminology Specialist** | Opus | Deep expertise in glossary compliance, term consistency, untranslated terms, financial terminology across regional variants | When Category 1 metrics fail |
| **Style & Voice Specialist** | Opus | Rewrites for tone, formality, sentence structure, passive/active balance, brand voice adherence | When Category 2 metrics fail |
| **Structural Specialist** | Opus | Fixes formatting preservation, numerical accuracy, paragraph alignment while preserving linguistic quality | When Category 3 metrics fail |
| **Linguistic Specialist** | Opus | Polishes fluency, validates meaning preservation, enforces regional variant correctness --- the "native speaker" pass | When Category 4 metrics fail |

**Model rationale**: The Quality Arbiter uses Haiku because its job is structured classification and routing --- it outputs a JSON routing plan, no rewriting. Every specialist uses Opus because each requires deep linguistic judgment within its domain. The Scoring Agent uses Opus because accurate evaluation of subjective metrics (fluency, meaning, formality) demands the highest reasoning capability.

#### Correction Flow

```
Translation Agent (Opus)
       │
       ▼
Scoring Agent (Opus)
  Evaluates all 13 metrics → structured scorecard
       │
       ▼
  ALL pass? ──YES──► DONE (return translation + scores)
       │
       NO
       ▼
Quality Arbiter (Haiku)
  Reads scorecard, outputs:
  {
    "failed_categories": ["terminology", "style"],
    "correction_sequence": ["terminology", "style"],
    "rationale": "Fix terms first (mechanical), then style (depends on final wording)",
    "conflict_risks": ["style rewrite may re-introduce non-glossary terms"]
  }
       │
       ▼
  Route to specialists IN SEQUENCE
       │
       ├──► Terminology Specialist (Opus)
       │      Receives: source, current translation, glossary, failed term metrics
       │      Returns: corrected translation (terminology only)
       │      │
       ├──► Style & Voice Specialist (Opus)
       │      Receives: source, current translation, tone profile, failed style metrics
       │      Returns: corrected translation (style only, preserve terminology fixes)
       │      │
       ├──► Structural Specialist (Opus)
       │      Receives: source, current translation, structure metrics
       │      Returns: corrected translation (structure only, preserve all prior fixes)
       │      │
       └──► Linguistic Specialist (Opus)
              Receives: source, current translation, linguistic metrics
              Returns: polished translation (fluency/meaning/variant, preserve all prior fixes)
       │
       ▼
Scoring Agent (Opus) — re-score
       │
       ▼
  ALL pass? ──YES──► DONE
       │
       NO
       ▼
Quality Arbiter (Haiku)
  Analyzes: what improved, what regressed, what's stuck
  Decides: one more targeted pass OR escalate to HITL
       │
       ├──► If improvement detected + specific fixable failures remain:
       │      Route to relevant specialist(s) for ONE more pass
       │      │
       └──► If no improvement OR regression OR 2 correction rounds complete:
              Escalate to HITL with full audit trail:
              - Original translation + score
              - Each specialist's correction + reasoning
              - Final score + what remains unfixed
```

#### Specialist Design Principles

1. **Each specialist receives the output of the previous specialist**, not the original translation. Corrections compound; they don't compete.

2. **Each specialist is instructed to preserve domains outside its scope.** The Style Specialist's system prompt explicitly states: "Do NOT change glossary terms, numbers, or formatting. Your scope is tone, formality, sentence structure, and voice only."

3. **The Arbiter sequences intelligently.** Default order is Terminology → Style → Structural → Linguistic (most mechanical first, most nuanced last). The Arbiter can reorder if the scorecard suggests a different priority.

4. **Max 2 correction rounds total.** After the initial translation + 2 specialist correction rounds, if thresholds aren't met, the system escalates to HITL. This prevents infinite loops while giving the specialists enough room to converge.

5. **Full audit trail.** Every specialist pass is logged: input text, output text, which metrics it targeted, reasoning. This audit trail ships with HITL escalations so the human reviewer sees exactly what the system tried and where it got stuck.

6. **Selective invocation.** If only Category 1 (terminology) fails, only the Terminology Specialist runs. No unnecessary passes through agents whose categories already pass.

### Threshold Configuration

```json
{
  "client": "oanda",
  "language": "es",
  "metric_thresholds": {
    "glossary_compliance": 95,
    "term_consistency": 90,
    "untranslated_terms": 95,
    "formality_level": 85,
    "sentence_length_ratio": 80,
    "passive_voice_ratio": 80,
    "brand_voice_adherence": 95,
    "formatting_preservation": 90,
    "numerical_accuracy": 100,
    "paragraph_alignment": 85,
    "fluency": 85,
    "meaning_preservation": 90,
    "regional_variant": 90
  },
  "aggregate_threshold": 88,
  "metric_weights": {},
  "max_revision_attempts": 2
}
```

Empty `metric_weights` means equal weighting. Override individual weights as floats (they are normalized to sum to 1.0).

## Client Profile Schema

A client profile is the full personalization layer. It is produced by Profile Extraction or built manually.

```json
{
  "client_id": "oanda",
  "client_name": "OANDA",
  "created_at": "2026-04-02T10:00:00Z",
  "updated_at": "2026-04-02T10:00:00Z",
  "source_language": "en",

  "languages": {
    "es": {
      "regional_variant": "es-ES",
      "glossary": {
        "support level": "nivel de soporte",
        "resistance level": "nivel de resistencia"
      },
      "tone": {
        "formality_level": 4,
        "description": "professional, conservative, institutional",
        "passive_voice_target_pct": 25,
        "avg_sentence_length": 22,
        "sentence_length_stddev": 6
      },
      "brand_rules": [
        "Always write 'OANDA' in uppercase",
        "Refer to platform as 'plataforma de trading de OANDA'"
      ],
      "scoring": {
        "metric_thresholds": { "glossary_compliance": 95 },
        "aggregate_threshold": 88,
        "metric_weights": {}
      }
    }
  },

  "reference_pairs": [
    {
      "id": "pair_001",
      "source_hash": "sha256:abc...",
      "added_at": "2026-04-02T10:00:00Z",
      "language": "es",
      "metrics_extracted": ["glossary", "tone", "regional_variant"]
    }
  ]
}
```

## Pipeline Architecture

### Mode 1: Translation + Scoring + Specialist Correction

```
Input: base_document + client_id + target_language
  │
  ▼
[1. Load Client Profile]
  Load glossary, tone, brand rules, scoring thresholds
  │
  ▼
[2. Translate] ─── Translation Agent (Opus)
  Enriched system prompt: glossary, tone, brand rules, regional variant
  │
  ▼
[3. Score] ─── Scoring Agent (Opus)
  Evaluate all 13 metrics → structured scorecard
  │
  ▼
[4. Gate]
  ALL metrics >= threshold AND aggregate >= threshold?
  │          │
  YES        NO
  │          │
  ▼          ▼
[5a. PASS] [5b. Quality Arbiter] ─── (Haiku)
  Return     Reads scorecard, determines which specialists needed
  result     Sequences: Terminology → Style → Structural → Linguistic
             │
             ▼
           [5c. Specialist Correction Pass]
             Only invoke specialists for FAILED categories
             Each receives prior specialist's output (corrections compound)
             Each preserves domains outside its scope
             │
             ▼
           [5d. Re-Score] ─── Scoring Agent (Opus)
             │
             ▼
           [5e. Gate]
             Pass? → DONE
             Fail + improvement? → Arbiter routes ONE more targeted pass
             Fail + no improvement OR round 2 complete? → HITL escalation
             (Full audit trail: every specialist pass logged with reasoning)
```

### Mode 2: Profile Extraction

```
Input: (base_document, client_translated_version) pairs + client_id + language
  |
  v
[1. Align]
  Sentence-level alignment between source and client version
  |
  v
[2. Extract Glossary]
  Identify financial terms in source
  Map to client's chosen translations
  Flag inconsistencies across pairs
  |
  v
[3. Extract Style Metrics]
  Formality level, sentence length stats, passive voice ratio
  Brand rule patterns (capitalization, naming conventions)
  |
  v
[4. Detect Regional Variant]
  Analyze vocabulary, grammar markers (vosotros/ustedes, leismo, etc.)
  Classify: es-ES, es-LATAM, es-MX, etc.
  |
  v
[5. Build/Update Profile]
  Merge extracted data into client profile
  Mark which metrics were extracted from which pairs
  |
  v
[6. Validate]
  Score the client's own translation against the extracted profile
  The client's translation should score 90+ (sanity check)
```

## API Surface

### CLI Commands

```bash
# Translate a document with scoring
python -m finflow.translate \
  --input report.md \
  --client oanda \
  --language es \
  --output translated.md \
  --score-report score.json

# Extract profile from reference pairs
python -m finflow.extract_profile \
  --pairs pairs.json \
  --client oanda \
  --language es

# Score an existing translation (no translation, just scoring)
python -m finflow.score \
  --source report.md \
  --translation translated.md \
  --client oanda \
  --language es

# List client profiles
python -m finflow.profiles list

# Show profile details
python -m finflow.profiles show oanda
```

`pairs.json` format:
```json
[
  {
    "source": "path/to/base_report_1.md",
    "translation": "path/to/client_version_1.md",
    "language": "es"
  }
]
```

### Flask Endpoints

```
POST /api/translate
  Body: { "document": "...", "client_id": "oanda", "language": "es" }
  Response: { "translation": "...", "scores": {...}, "passed": true/false }
  Streams SSE events during processing.

POST /api/extract-profile
  Body: { "pairs": [...], "client_id": "oanda", "language": "es" }
  Response: { "profile": {...}, "validation_score": 92.5 }

POST /api/score
  Body: { "source": "...", "translation": "...", "client_id": "oanda", "language": "es" }
  Response: { "scores": {...}, "passed": true/false }

GET  /api/profiles
  Response: [{ "client_id": "oanda", "languages": ["es", "zh"], ... }]

GET  /api/profiles/:client_id
  Response: { full profile object }

PUT  /api/profiles/:client_id/thresholds
  Body: { "language": "es", "metric_thresholds": {...}, "aggregate_threshold": 88 }
  Response: { updated profile }
```

## Storage

SQLite for MVP. Single database file at `finflow/data/translation_engine.db`.

### Schema

```sql
CREATE TABLE client_profiles (
  client_id     TEXT PRIMARY KEY,
  client_name   TEXT NOT NULL,
  profile_json  TEXT NOT NULL,   -- full ClientProfile as JSON
  created_at    TEXT NOT NULL,
  updated_at    TEXT NOT NULL
);

CREATE TABLE translations (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  client_id       TEXT NOT NULL,
  language        TEXT NOT NULL,
  source_hash     TEXT NOT NULL,    -- SHA-256 of source document
  source_text     TEXT NOT NULL,
  translated_text TEXT NOT NULL,
  scores_json     TEXT NOT NULL,    -- full scoring breakdown
  passed          INTEGER NOT NULL, -- 0 or 1
  aggregate_score REAL NOT NULL,
  revision_count  INTEGER DEFAULT 0,
  created_at      TEXT NOT NULL,
  FOREIGN KEY (client_id) REFERENCES client_profiles(client_id)
);

CREATE TABLE reference_pairs (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  client_id     TEXT NOT NULL,
  language      TEXT NOT NULL,
  source_text   TEXT NOT NULL,
  translation   TEXT NOT NULL,
  source_hash   TEXT NOT NULL,
  added_at      TEXT NOT NULL,
  FOREIGN KEY (client_id) REFERENCES client_profiles(client_id)
);

CREATE INDEX idx_translations_client ON translations(client_id, language);
CREATE INDEX idx_translations_score ON translations(aggregate_score);
```

## Implementation Phases

### Phase 1: Forward Pass + Scoring (MVP core)

This phase delivers the fundamental value: translate a document and get an objective score.

#### 1a. Scoring Agent
- New `finflow/agents/scoring_agent.py`
- Takes source text, translated text, and client profile
- Evaluates all 13 metrics, returns scores
- Deterministic metrics (glossary_compliance, numerical_accuracy, formatting_preservation) use code-based checks
- Subjective metrics (fluency, meaning_preservation, formality_level) use LLM-as-judge with structured output
- Each metric scorer is a standalone function, testable in isolation
- Error case: if LLM scoring fails, flag metric as "unscored" and exclude from aggregate

#### 1b. Client Profile Loader
- New `finflow/profiles/` module
- Load profiles from SQLite; fall back to existing `finflow/glossaries/client_*.json` files
- Migration script to convert existing glossary JSONs into full profile format
- Error case: missing profile returns clear error, does not fall back to empty profile

#### 1c. Enhanced Translation Agent
- Extend `TranslationAgent.translate()` to accept full client profile (not just glossary)
- Inject tone targets, regional variant, brand rules into system prompt
- Return `TranslationResult` with raw text (scoring happens separately)
- Backward-compatible: if no profile exists, behaves exactly as today

#### 1d. Quality Arbiter
- New `finflow/agents/quality_arbiter.py`
- Model: Haiku (structured classification task — routing decisions, not rewriting)
- Input: full scorecard with per-metric scores, thresholds, and pass/fail status
- Output: structured JSON — which specialists to invoke, in what order, conflict risks
- Decides when to escalate to HITL (no improvement after correction, or 2 rounds exhausted)
- Lightweight by design: reads numbers, outputs routing plan

#### 1e. Specialist Agents
- New `finflow/agents/terminology_specialist.py` — Opus, glossary/term correction
- New `finflow/agents/style_specialist.py` — Opus, tone/formality/voice rewriting
- New `finflow/agents/structural_specialist.py` — Opus, formatting/numbers/alignment
- New `finflow/agents/linguistic_specialist.py` — Opus, fluency/meaning/regional polish
- Each specialist has a narrow system prompt scoped to its domain
- Each explicitly instructed to preserve corrections from prior specialists
- Each returns: corrected text + reasoning for changes made

#### 1f. Translation Engine Orchestrator
- New `finflow/engine/translation_engine.py` orchestrating the full flow:
  translate → score → gate → arbiter → specialists → re-score → gate → HITL
- Max 2 correction rounds (configurable)
- Full audit trail: logs every agent invocation, input/output, scores, reasoning
- Integrates with existing pipeline's `_translation_loop` as drop-in replacement
- Error case: after max rounds, returns result with `passed=False`, all scores, and full audit trail for human review

#### 1g. CLI + API
- CLI: `translate`, `score` commands
- Flask: `POST /api/translate`, `POST /api/score`
- SSE streaming for translation progress, scoring, specialist corrections in real-time

#### Phase 1 deliverable
Given a base document, a client ID, and a target language, produce a scored translation with pass/fail verdict. The existing OANDA and Alpari glossaries/configs are usable as profiles immediately.

### Phase 2: Profile Extraction

#### 2a. Alignment Engine
- New `finflow/extraction/aligner.py`
- Sentence-level alignment between source and translated documents
- Handles paragraph splits/merges gracefully
- Error case: if alignment confidence is low (< 70%), warn and proceed with paragraph-level alignment

#### 2b. Metric Extractors
- New `finflow/extraction/extractors.py`
- One function per metric category: `extract_glossary()`, `extract_tone()`, `extract_regional_variant()`, `extract_brand_rules()`
- Each takes aligned sentence pairs and returns extracted metric values
- Requires minimum 3 reference pairs for statistical confidence; works with 1 pair but flags as "low confidence"

#### 2c. Profile Builder
- Merges extracted metrics into `ClientProfile` schema
- Validates by scoring the client's own reference translation against the profile (sanity check: should score 90+)
- Error case: if validation score < 80, warn that extraction quality is low

#### 2d. CLI + API
- CLI: `extract_profile`, `profiles` commands
- Flask: `POST /api/extract-profile`, `GET /api/profiles`

#### Phase 2 deliverable
Feed (base, client version) pairs and get back a client profile usable by Phase 1's forward pass.

### Phase 3: Learning Loop + Refinement

#### 3a. Correction Analysis
- When a human edits a translation (via HITL), compare before/after
- Extract what changed: terminology corrections, style adjustments, structural edits
- Update client profile automatically (glossary additions, threshold adjustments)
- Integrate with existing `TranslationAgent.update_glossary()` and extend it

#### 3b. Score Trend Tracking
- Track scores over time per client/language
- Identify metrics that consistently score low (systemic issues)
- Surface insights: "OANDA ES translations consistently fail passive_voice_ratio --- consider lowering threshold or adjusting prompt"

#### 3c. A/B Scoring
- Score two translation variants against the same profile
- Support human preference collection: which variant does the reviewer prefer?
- Correlate human preference with metric scores to calibrate weights

#### Phase 3 deliverable
The system learns from every human correction, profiles improve automatically over time, and metric weights are calibrated against actual human preferences.

## Constraints

- **Model strategy**: Quality-first. Opus for all agents that require linguistic judgment (Translation, Scoring, all 4 Specialists). Haiku for the Quality Arbiter (structured routing — classification task, no rewriting). Model downgrades are a future cost-optimization exercise, not an MVP concern.
- **Multi-agent pipeline**: Worst case (all 4 categories fail): Translation + Scoring + Arbiter + 4 Specialists + Re-score = 8 agent calls per document. Typical case (1-2 categories fail): 4-5 calls. If translation passes first try: 2 calls (translate + score).
- **Determinism**: LLM-based scorers use temperature=0 and structured output to minimize variance. Future consideration: majority-vote scoring (3 calls) for high-stakes documents.
- **Language support**: EN->ES (es-ES, es-LATAM) as primary. Architecture must support any language pair without code changes (only profile data).
- **Backward compatibility**: Existing `TranslationAgent`, glossary files, and pipeline must continue to work unchanged. The engine wraps them, not replaces them.
- **Storage**: SQLite for MVP. Schema designed to be trivially portable to PostgreSQL/Supabase later.
- **Python 3.14**: Use modern Python features (type hints, dataclasses, match statements) per existing codebase patterns.

## Out of Scope

- **Document format parsing** --- MVP accepts plain text / markdown. PDF extraction, DOCX parsing, HTML stripping are separate concerns.
- **Supabase / pgvector migration** --- SQLite for now. Migration is a future task.
- **Real-time collaborative editing** --- The engine scores completed translations, not in-progress edits.
- **Multi-document consistency** --- Scoring is per-document. Cross-document terminology consistency tracking is Phase 3+.
- **Custom metric plugins** --- The 13 metrics are hardcoded for MVP. A plugin system for user-defined metrics is future work.
- **UI** --- This spec covers the engine, CLI, and API. The premium dark-theme UI is a separate spec.
- **Billing / usage tracking** --- No metering of API calls or translations in MVP.
- **Languages beyond ES** --- Architecture supports all languages, but testing and validation focus on EN->ES. ZH support exists in glossaries and can be tested but is not the priority.

## Open Questions (Deferred)

1. **Metric weight calibration** --- How do we determine the right weights? Phase 3's A/B scoring addresses this, but initial weights are equal by default.
2. **LLM-as-judge reliability** --- How consistent are fluency/meaning scores across runs? Needs empirical testing with temperature=0. May need majority-vote (3 calls) for high-stakes scoring.
3. **Regional variant granularity** --- Is es-ES / es-LATAM / es-MX sufficient, or do clients need es-AR, es-CO, etc.? Start with 3, expand on demand.
4. **Reference pair volume** --- How many pairs does Profile Extraction need for a reliable profile? Hypothesis: 5-10 pairs for high confidence. Needs validation.
5. **Glossary size scaling** --- Current glossaries have ~90 terms. At 500+ terms, in-prompt glossary may hit token limits. May need retrieval-based approach (semantic search for relevant terms per paragraph).
6. **Specialist interference** --- When the Style Specialist rewrites for tone, it may inadvertently re-introduce non-glossary terms that the Terminology Specialist just fixed. The "preserve prior corrections" instruction mitigates this, but empirical testing is needed to measure how often specialists undo each other's work and whether the Arbiter's conflict detection catches it reliably.
7. **Model selection validation** --- The MVP uses Opus everywhere except the Arbiter. After initial testing, we should measure whether any specialist achieves equivalent quality with Sonnet — but only downgrade with empirical evidence, not assumptions.
