import type { ContentPersona, SimilarityResult, TrinaryVerdict } from "../lib/types";

export type TenantStatus = "pending" | "generating" | "complete" | "error";

export interface TenantState {
  personaId: string;
  status: TenantStatus;
  body: string | null;
  wordCount: number | null;
}

interface Props {
  index: number;
  tenant: TenantState;
  personas: ContentPersona[] | null;
  pairs: SimilarityResult[];
  /** All four tenants in order — used to label the per-pair mini-table. */
  allTenants: TenantState[];
  disabled: boolean;
  onPersonaChange: (personaId: string) => void;
}

const VERDICT_COLOR: Record<TrinaryVerdict, string> = {
  distinct_products: "text-distinct",
  reskinned_same_article: "text-reskinned",
  fabrication_risk: "text-fabrication",
};

const VERDICT_GLYPH: Record<TrinaryVerdict, string> = {
  distinct_products: "✓",
  reskinned_same_article: "≈",
  fabrication_risk: "!",
};

function findPair(
  pairs: SimilarityResult[],
  personaA: string,
  personaB: string,
): SimilarityResult | undefined {
  // pairId is `${a.id}__${b.id}` per the runner; either order may match.
  return pairs.find(
    (p) =>
      p.pairId === `${personaA}__${personaB}` ||
      p.pairId === `${personaB}__${personaA}`,
  );
}

export default function TenantCard({
  index,
  tenant,
  personas,
  pairs,
  allTenants,
  disabled,
  onPersonaChange,
}: Props) {
  const persona = personas?.find((p) => p.id === tenant.personaId);
  const others = allTenants
    .map((t, i) => ({ tenant: t, index: i }))
    .filter((x) => x.index !== index);

  return (
    <div className="bg-card border border-border rounded-lg p-4 flex flex-col gap-3 min-h-[320px]">
      <div className="flex items-center justify-between">
        <span className="text-xs uppercase tracking-wide text-foreground-muted">
          Tenant {index + 1}
        </span>
        <span
          className={
            tenant.status === "complete"
              ? "text-xs text-distinct"
              : tenant.status === "generating"
                ? "text-xs text-accent animate-pulse"
                : tenant.status === "error"
                  ? "text-xs text-fabrication"
                  : "text-xs text-foreground-muted"
          }
        >
          {tenant.status}
        </span>
      </div>

      <select
        className="bg-card-elevated border border-border-strong rounded-md px-2 py-1.5 text-sm text-foreground focus:outline-none focus:border-accent"
        value={tenant.personaId}
        onChange={(e) => onPersonaChange(e.target.value)}
        disabled={disabled || !personas}
      >
        {personas?.map((p) => (
          <option key={p.id} value={p.id}>
            {p.name}
          </option>
        ))}
      </select>

      <div className="flex-1 min-h-[100px] bg-background border border-border rounded-md p-3 text-xs leading-relaxed font-mono text-foreground-dim overflow-y-auto max-h-[280px]">
        {tenant.status === "pending" && (
          <span className="text-foreground-muted">waiting…</span>
        )}
        {tenant.status === "generating" && (
          <span className="text-accent animate-pulse">
            {persona?.name ?? "Tenant"} is thinking…
          </span>
        )}
        {tenant.status === "error" && (
          <span className="text-fabrication">error</span>
        )}
        {tenant.status === "complete" && tenant.body && (
          <div className="whitespace-pre-wrap">{tenant.body}</div>
        )}
      </div>

      <div className="flex items-center justify-between text-xs text-foreground-muted">
        <span>
          {tenant.wordCount != null ? `${tenant.wordCount} words` : "—"}
        </span>
      </div>

      {/* Per-pair judge results vs the other tenants */}
      <div className="border-t border-border pt-2 flex flex-col gap-1">
        {others.map(({ tenant: otherTenant, index: otherIndex }) => {
          const pair = findPair(pairs, tenant.personaId, otherTenant.personaId);
          const verdict = pair?.judgeTrinaryVerdict;
          return (
            <div
              key={otherIndex}
              className="flex items-center justify-between text-[11px] font-mono"
            >
              <span className="text-foreground-muted">vs T{otherIndex + 1}</span>
              {pair ? (
                <span className="flex items-center gap-2">
                  <span className="text-foreground-dim">
                    fid {pair.judgeFactualFidelity?.toFixed(2) ?? "—"}
                  </span>
                  <span className="text-foreground-dim">
                    pres {pair.judgePresentationSimilarity?.toFixed(2) ?? "—"}
                  </span>
                  {verdict && (
                    <span className={VERDICT_COLOR[verdict]}>
                      {VERDICT_GLYPH[verdict]}
                    </span>
                  )}
                </span>
              ) : (
                <span className="text-foreground-muted">—</span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
