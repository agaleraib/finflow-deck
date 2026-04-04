/**
 * Profile Extraction Agent — extracts client profile parameters from text samples.
 *
 * Given source texts and (optionally) their human translations, this agent
 * uses Claude to infer: glossary, tone profile, brand rules, regional variant,
 * forbidden terms, and compliance patterns.
 *
 * Recommended sample sizes:
 *   - Minimum:  5 documents  — basic terminology + tone direction
 *   - Solid:   10-15 docs    — reliable statistics (sentence length, passive %, formality)
 *   - Ideal:   20+ docs      — high-confidence glossary + full style fingerprint
 *
 * Best results come from source + translation pairs, not source-only.
 */

import { runAgentStructured } from "../lib/anthropic.js";
import type { AgentConfig, EventHandler } from "../lib/types.js";
import type { LanguageProfile } from "../profiles/types.js";
import { LanguageProfileSchema } from "../profiles/types.js";

// --- Types ---

export interface TextSample {
  /** Source text (English) */
  source: string;
  /** Human translation (optional but strongly recommended) */
  translation?: string;
}

export interface ExtractionRequest {
  clientId: string;
  clientName: string;
  targetLanguage: string;
  regionalVariant?: string;
  samples: TextSample[];
}

export interface ExtractionResult {
  clientId: string;
  clientName: string;
  sourceLanguage: string;
  targetLanguage: string;
  extractedProfile: LanguageProfile;
  sampleCount: number;
  confidence: "low" | "medium" | "high";
  warnings: string[];
}

// --- Confidence ---

function assessConfidence(sampleCount: number): "low" | "medium" | "high" {
  if (sampleCount >= 15) return "high";
  if (sampleCount >= 5) return "medium";
  return "low";
}

function buildWarnings(req: ExtractionRequest): string[] {
  const warnings: string[] = [];
  const count = req.samples.length;

  if (count < 3) {
    warnings.push(
      `Only ${count} sample(s) provided. Minimum 5 recommended for reliable extraction.`,
    );
  } else if (count < 5) {
    warnings.push(
      `${count} samples provided. 10-15 recommended for reliable tone statistics.`,
    );
  }

  const withTranslation = req.samples.filter((s) => s.translation).length;
  if (withTranslation === 0) {
    warnings.push(
      "No translation pairs provided. Glossary extraction will be inferred (less accurate). " +
        "Provide source + human translation pairs for best results.",
    );
  } else if (withTranslation < count) {
    warnings.push(
      `Only ${withTranslation}/${count} samples have translations. Missing pairs reduce glossary accuracy.`,
    );
  }

  return warnings;
}

// --- System Prompt ---

function buildExtractionPrompt(req: ExtractionRequest): string {
  return `You are a senior localization analyst at WordwideFX, specializing in financial translation quality. Your task is to analyze text samples from a client and extract a complete translation profile.

CLIENT: ${req.clientName} (${req.clientId})
TARGET LANGUAGE: ${req.targetLanguage}
REGIONAL VARIANT: ${req.regionalVariant || "detect from samples"}
SAMPLES PROVIDED: ${req.samples.length}

Analyze ALL samples carefully and extract:

1. GLOSSARY: Identify recurring financial terms and their translations. Only include terms that appear in at least 2 samples or are clearly domain-specific. For source-only samples, propose translations based on the client's apparent style.

2. TONE PROFILE:
   - formalityLevel (1-5): Assess from word choice, sentence structure, register
   - description: Short description of the tone (e.g. "professional, conservative, institutional")
   - passiveVoiceTargetPct: Estimate % of passive constructions
   - avgSentenceLength: Count words per sentence across samples, compute mean
   - sentenceLengthStddev: Compute standard deviation
   - personPreference: "first" / "second" / "third" — which is dominant?
   - hedgingFrequency: "low" / "moderate" / "high" — how often do they hedge? ("may", "could", "potentially")

3. BRAND RULES: Identify consistent patterns — capitalization rules, untranslated brand names, specific phrasings that always appear the same way.

4. FORBIDDEN TERMS: Terms that never appear despite being common alternatives (compare against standard financial vocabulary).

5. COMPLIANCE PATTERNS: Any regulatory disclaimers or required phrases that appear consistently.

6. REGIONAL VARIANT: If not specified, detect from vocabulary and grammar markers (vosotros/ustedes, ordenador/computadora, etc.).

Be precise. Use actual counts from the text. Do not invent terms you did not observe.`;
}

// --- Tool Schema for Structured Output ---

const EXTRACTION_TOOL_SCHEMA = {
  type: "object" as const,
  properties: {
    regionalVariant: {
      type: "string" as const,
      description: "BCP-47 tag for the regional variant (e.g. es-ES, es-MX, en-GB)",
    },
    glossary: {
      type: "object" as const,
      additionalProperties: { type: "string" as const },
      description: "Source term -> target translation mapping",
    },
    tone: {
      type: "object" as const,
      properties: {
        formalityLevel: {
          type: "number" as const,
          description: "1-5 (1=casual, 5=institutional)",
        },
        description: {
          type: "string" as const,
          description: "Short tone description",
        },
        passiveVoiceTargetPct: {
          type: "number" as const,
          description: "Target passive voice percentage",
        },
        avgSentenceLength: {
          type: "number" as const,
          description: "Average words per sentence",
        },
        sentenceLengthStddev: {
          type: "number" as const,
          description: "Sentence length standard deviation",
        },
        personPreference: {
          type: "string" as const,
          enum: ["first", "second", "third"],
          description: "Dominant person preference",
        },
        hedgingFrequency: {
          type: "string" as const,
          enum: ["low", "moderate", "high"],
          description: "How often hedging language is used",
        },
      },
      required: [
        "formalityLevel",
        "description",
        "passiveVoiceTargetPct",
        "avgSentenceLength",
        "sentenceLengthStddev",
        "personPreference",
        "hedgingFrequency",
      ],
    },
    brandRules: {
      type: "array" as const,
      items: { type: "string" as const },
      description: "Brand voice rules observed",
    },
    forbiddenTerms: {
      type: "array" as const,
      items: { type: "string" as const },
      description: "Terms that should never appear in output",
    },
    compliancePatterns: {
      type: "array" as const,
      items: { type: "string" as const },
      description: "Regulatory disclaimers or required phrases",
    },
  },
  required: [
    "regionalVariant",
    "glossary",
    "tone",
    "brandRules",
    "forbiddenTerms",
    "compliancePatterns",
  ],
};

// --- User Message ---

function buildUserMessage(samples: TextSample[]): string {
  const parts: string[] = ["Analyze these text samples:\n"];

  for (const [i, sample] of samples.entries()) {
    parts.push(`--- SAMPLE ${i + 1} ---`);
    parts.push(`SOURCE:\n${sample.source}`);
    if (sample.translation) {
      parts.push(`TRANSLATION:\n${sample.translation}`);
    }
    parts.push("");
  }

  parts.push(
    "Extract the complete profile. Be precise — use actual counts from the text.",
  );
  return parts.join("\n");
}

// --- Main ---

export async function extractProfile(
  req: ExtractionRequest,
  onEvent?: EventHandler,
): Promise<ExtractionResult> {
  const warnings = buildWarnings(req);
  const confidence = assessConfidence(req.samples.length);

  onEvent?.({
    stage: "extraction",
    status: "analyzing",
    message: `Analyzing ${req.samples.length} sample(s) for ${req.clientName} (${req.targetLanguage})...`,
    timestamp: new Date().toISOString(),
    data: { sampleCount: req.samples.length, confidence },
  });

  const config: AgentConfig = {
    name: "ProfileExtractionAgent",
    systemPrompt: buildExtractionPrompt(req),
    model: "opus",
    maxTokens: 8192,
  };

  const { result: raw } = await runAgentStructured(
    config,
    buildUserMessage(req.samples),
    "extract_profile",
    "Extract a complete client translation profile from the provided text samples",
    EXTRACTION_TOOL_SCHEMA,
    (input) => input,
  );

  // Parse through Zod to apply defaults and validate
  const extractedProfile = LanguageProfileSchema.parse({
    regionalVariant: raw.regionalVariant,
    glossary: raw.glossary,
    tone: raw.tone,
    brandRules: raw.brandRules,
    forbiddenTerms: raw.forbiddenTerms,
    compliancePatterns: raw.compliancePatterns,
    // Use default scoring — extraction doesn't override thresholds
  });

  onEvent?.({
    stage: "extraction",
    status: "complete",
    message: `Profile extracted: ${Object.keys(extractedProfile.glossary).length} glossary terms, ` +
      `formality ${extractedProfile.tone.formalityLevel}/5, ` +
      `${extractedProfile.brandRules.length} brand rules. ` +
      `Confidence: ${confidence}.`,
    timestamp: new Date().toISOString(),
  });

  return {
    clientId: req.clientId,
    clientName: req.clientName,
    sourceLanguage: "en",
    targetLanguage: req.targetLanguage,
    extractedProfile,
    sampleCount: req.samples.length,
    confidence,
    warnings,
  };
}
