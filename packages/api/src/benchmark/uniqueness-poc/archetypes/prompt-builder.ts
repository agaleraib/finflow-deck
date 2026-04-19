/**
 * Archetype Validation PoC — Task 4: Prompt builder.
 *
 * Converts a FrameworkArchetype definition into a system prompt + user message
 * for the identity agent call. Follows the same composition pattern as the
 * existing identity builders (in-house-journalist.ts, trading-desk.ts, etc.)
 * but derives everything from the archetype config rather than hardcoded text.
 *
 * Spec: docs/specs/2026-04-16-archetype-validation.md §6.2
 */

import type { ContentPersona } from "../types.js";
import { renderAngleTagDirectives, renderPersonalityTagDirectives } from "../tags.js";
import type { FrameworkArchetype } from "./types.js";

// ───────────────────────────────────────────────────────────────────
// System prompt — one per framework, encodes the archetype's entire
// editorial personality.
// ───────────────────────────────────────────────────────────────────

export function buildArchetypeSystemPrompt(archetype: FrameworkArchetype): string {
  const { analyticalStance, structuralTemplate, voiceDirectives } = archetype;

  const formalityLabel = (
    { 1: "very casual", 2: "casual", 3: "neutral", 4: "formal", 5: "very formal" } as const
  )[voiceDirectives.formality];

  const jargonLabel = (
    { 1: "minimal (explain all terms)", 2: "low", 3: "moderate", 4: "high", 5: "expert-level (assume fluency)" } as const
  )[voiceDirectives.jargonLevel];

  const personLabel = (
    {
      we: 'first-person plural ("we believe", "our view")',
      I: 'first-person singular ("I see", "my read")',
      impersonal: 'impersonal/third-person ("the data suggests", "the setup favours")',
    } as const
  )[voiceDirectives.personPreference];

  return `You are a financial content writer producing market analysis in the **${archetype.name}** framework.

${archetype.description}

# Analytical stance

- **Directionality:** ${analyticalStance.defaultDirectionality}
- **Horizon:** ${analyticalStance.horizonRange.min} to ${analyticalStance.horizonRange.max}
- **Position style:** ${analyticalStance.positionStyle}
- **Scenario style:** ${analyticalStance.scenarioStyle}

# Structure

Write your analysis following this section flow: ${structuralTemplate.sectionOrder.join(" → ")}.

- **Target length:** ${structuralTemplate.typicalWordCount.target} words (range ${structuralTemplate.typicalWordCount.min}-${structuralTemplate.typicalWordCount.max})
- **Headline style:** ${structuralTemplate.headlineStyle}

The section flow is a guide, not a rigid template. Adapt it naturally to the specific event. But the overall shape — where you START, what you FOREGROUND, and how you CLOSE — must reflect this structure.

# Voice

- **Formality:** ${formalityLabel} (${voiceDirectives.formality}/5)
- **Average sentence length:** ~${voiceDirectives.sentenceLengthTarget} words
- **Hedging frequency:** ${voiceDirectives.hedgingFrequency}
- **Jargon level:** ${jargonLabel} (${voiceDirectives.jargonLevel}/5)
- **Person:** ${personLabel}

# Factual fidelity — HARD CONSTRAINT

The source analysis is your factual ground truth. You may change HOW you present the facts (voice, structure, emphasis, order, which facts to foreground). You may NOT change WHAT the facts are. If the analysis states it, your output must not contradict, alter, omit with misleading effect, or extend it. If you want to say something the analysis doesn't say, you can't.

Specifically:
- Do NOT invent price levels, support/resistance, or probabilities not in the source
- Do NOT reverse or modify the source's directional assessment
- Do NOT fabricate quotes, data points, or historical references
- Do NOT add scenarios the source does not cover

The differentiation between frameworks comes from EMPHASIS, ORDERING, STRUCTURE, and VOICE — not from inventing different facts.

# What NOT to do

- Do NOT include compliance disclaimers — those get added later
- Do NOT use markdown headers within the body unless your structural template calls for them
- Do NOT reference yourself as an AI, model, or assistant
- Do NOT add meta-commentary about the analysis or your approach
- Output ONLY the finished piece — start with the headline`;
}

// ───────────────────────────────────────────────────────────────────
// User message — the core analysis + optional persona overlay.
// Same injection pattern as existing builders.
// ───────────────────────────────────────────────────────────────────

export function buildArchetypeUserMessage(
  coreAnalysis: string,
  archetype: FrameworkArchetype,
  persona?: ContentPersona,
): string {
  // ─── Hard-constraint directives from the persona's tag picks ───
  const angleDirectives = persona?.preferredAngles?.length
    ? renderAngleTagDirectives(persona.preferredAngles)
    : "";
  const personalityDirectives = persona?.personalityTags?.length
    ? renderPersonalityTagDirectives(persona.personalityTags)
    : "";

  // ─── Brand-overlay context (same pattern as in-house-journalist) ───
  const brandSection = persona
    ? `# Brand context

You are writing for **${persona.name}**.
- Brand voice: ${persona.brandVoice}
- Target audience: ${persona.audienceProfile}
- Brand positioning: ${persona.brandPositioning}
- Regional variant: ${persona.regionalVariant}
- Forbidden phrases: ${persona.forbiddenClaims.join(", ")}
- CTA policy: ${persona.ctaPolicy}
${persona.ctaPolicy !== "never" ? `- Available CTAs: ${persona.ctaLibrary.map((c) => `"${c.text}"`).join("; ")}` : ""}
${persona.companyBackground?.length ? `- Company background (weave naturally where relevant): ${persona.companyBackground.join("; ")}` : ""}

Apply the brand context as a natural overlay on top of the ${archetype.name} framework. The piece should feel like it was written by ${persona.name}'s editorial team, not a generic content service.

`
    : "";

  // ─── Archetype framing directive ───
  const framingDirective = `# Archetype framing — ${archetype.name}

You are writing in the **${archetype.name}** framework. Your analytical stance is **${archetype.analyticalStance.defaultDirectionality}** with a **${archetype.analyticalStance.scenarioStyle}** scenario style. Your horizon is **${archetype.analyticalStance.horizonRange.min} to ${archetype.analyticalStance.horizonRange.max}**.

${archetype.analyticalStance.positionStyle}

`;

  return `# Source analysis (background material — do not republish)

The following is a fundamental analysis written by a senior in-house analyst. This is your factual ground truth. Your finished piece should reflect the analyst's facts but be written in your own framework's voice and structure — not as a paraphrase of their analysis.

\`\`\`
${coreAnalysis}
\`\`\`

${framingDirective}${angleDirectives}${personalityDirectives}${brandSection}# Your task

Write a complete piece following your system instructions and the ${archetype.name} framework, applying ALL directives above as hard constraints (not suggestions):
- The ARCHETYPE FRAMING: write from the ${archetype.analyticalStance.defaultDirectionality} analytical stance with ${archetype.analyticalStance.scenarioStyle} scenario style
${angleDirectives ? "- The ANALYTICAL ANGLE directive: write from the assigned angle\n" : ""}${personalityDirectives ? "- The PERSONALITY directives: embody the assigned tags in tone, density, posture\n" : ""}${brandSection ? "- The BRAND CONTEXT: apply as natural overlay\n" : ""}
Output ONLY the finished piece — no preamble, no meta-commentary, no notes about the directives. Start with the headline.

CRITICAL: The archetype framing determines your STRUCTURE and ANALYTICAL STANCE. The angle directive determines WHAT you emphasize. The personality directives determine HOW you write. All must be visible in the final piece.`;
}
