import { useCallback, useEffect, useMemo, useReducer, useState } from "react";
import TopBar from "../components/TopBar";
import TenantCard, { type TenantState } from "../components/TenantCard";
import FidelityPresentationScatter from "../components/FidelityPresentationScatter";
import TrinaryVerdictDonut from "../components/TrinaryVerdictDonut";
import { fetchFixtures, fetchPersonas, startRun } from "../lib/api";
import { useSSE } from "../lib/useSSE";
import type {
  ContentPersona,
  NewsEvent,
  PocSseEvent,
  SimilarityResult,
} from "../lib/types";

type RunStatus = "idle" | "running" | "complete" | "error";

interface PageState {
  tenants: TenantState[];
  runStatus: RunStatus;
  costUsd: number | null;
  pairs: SimilarityResult[];
  errorMessage: string | null;
}

type Action =
  | { type: "set_persona"; index: number; personaId: string }
  | { type: "reset_for_run" }
  | { type: "sse"; event: PocSseEvent }
  | { type: "set_status"; status: RunStatus; errorMessage?: string };

const DEFAULT_PERSONA_IDS = [
  "premium-capital-markets",
  "fasttrade-pro",
  "helix-markets",
  "northbridge-wealth",
];

function makeInitialTenants(): TenantState[] {
  return DEFAULT_PERSONA_IDS.map((personaId) => ({
    personaId,
    status: "pending" as const,
    body: null,
    wordCount: null,
  }));
}

function reducer(state: PageState, action: Action): PageState {
  switch (action.type) {
    case "set_persona": {
      const tenants = state.tenants.map((t, i) =>
        i === action.index ? { ...t, personaId: action.personaId } : t,
      );
      return { ...state, tenants };
    }
    case "reset_for_run": {
      return {
        ...state,
        tenants: state.tenants.map((t) => ({
          ...t,
          status: "pending",
          body: null,
          wordCount: null,
        })),
        pairs: [],
        costUsd: null,
        errorMessage: null,
      };
    }
    case "sse": {
      const event = action.event;
      switch (event.type) {
        case "tenant_started": {
          const tenants = state.tenants.map((t, i) =>
            i === event.tenantIndex ? { ...t, status: "generating" as const } : t,
          );
          return { ...state, tenants };
        }
        case "tenant_completed": {
          const tenants = state.tenants.map((t, i) =>
            i === event.tenantIndex
              ? {
                  ...t,
                  status: "complete" as const,
                  body: event.output.body,
                  wordCount: event.output.wordCount,
                }
              : t,
          );
          return { ...state, tenants };
        }
        case "judge_completed": {
          // Replace the matching pair (if any) or append.
          const others = state.pairs.filter(
            (p) => p.pairId !== event.similarity.pairId,
          );
          return { ...state, pairs: [...others, event.similarity] };
        }
        case "cost_updated": {
          return { ...state, costUsd: event.totalCostUsd };
        }
        case "run_completed": {
          return {
            ...state,
            runStatus: "complete",
            costUsd: event.result.totalCostUsd,
          };
        }
        case "run_errored": {
          return { ...state, runStatus: "error", errorMessage: event.error };
        }
        default:
          return state;
      }
    }
    case "set_status": {
      return {
        ...state,
        runStatus: action.status,
        errorMessage: action.errorMessage ?? state.errorMessage,
      };
    }
    default:
      return state;
  }
}

const SSE_EVENT_TYPES: ReadonlyArray<PocSseEvent["type"]> = [
  "run_started",
  "stage_started",
  "core_analysis_completed",
  "tenant_started",
  "tenant_completed",
  "judge_completed",
  "cost_updated",
  "run_completed",
  "run_errored",
];

export default function PlaygroundUniqueness() {
  const [fixtures, setFixtures] = useState<NewsEvent[] | null>(null);
  const [personas, setPersonas] = useState<ContentPersona[] | null>(null);
  const [selectedFixtureId, setSelectedFixtureId] = useState<string | null>(null);
  const [eventBody, setEventBody] = useState<string>("");
  const [streamUrl, setStreamUrl] = useState<string | null>(null);

  const [state, dispatch] = useReducer(reducer, {
    tenants: makeInitialTenants(),
    runStatus: "idle" as RunStatus,
    costUsd: null,
    pairs: [],
    errorMessage: null,
  });

  // Load catalogs once on mount.
  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const [f, p] = await Promise.all([fetchFixtures(), fetchPersonas()]);
        if (cancelled) return;
        setFixtures(f);
        setPersonas(p);
        // Default-pick the first fixture id if none chosen yet, but leave the
        // body empty until the user explicitly selects.
      } catch (err) {
        // eslint-disable-next-line no-console
        console.error("[playground] failed to load catalogs", err);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleFixtureChange = useCallback(
    (id: string | null) => {
      setSelectedFixtureId(id);
      if (!id) return;
      const fixture = fixtures?.find((f) => f.id === id);
      if (fixture) {
        setEventBody(fixture.body);
      }
    },
    [fixtures],
  );

  const handleRunAll = useCallback(async () => {
    dispatch({ type: "reset_for_run" });
    dispatch({ type: "set_status", status: "running" });
    try {
      const res = await startRun({
        eventBody,
        ...(selectedFixtureId ? { fixtureId: selectedFixtureId } : {}),
        tenants: state.tenants.map((t) => ({ personaId: t.personaId })),
      });
      setStreamUrl(res.streamUrl);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unknown error";
      dispatch({ type: "set_status", status: "error", errorMessage: message });
    }
  }, [eventBody, selectedFixtureId, state.tenants]);

  const onSseEvent = useCallback((event: PocSseEvent) => {
    dispatch({ type: "sse", event });
  }, []);

  useSSE<PocSseEvent>(streamUrl, SSE_EVENT_TYPES, {
    onEvent: onSseEvent,
    onError: () => {
      // EventSource auto-reconnects on transient errors; we just log.
      // eslint-disable-next-line no-console
      console.warn("[playground] SSE error");
    },
  });

  const showCharts = useMemo(
    () => state.runStatus === "complete" && state.pairs.length > 0,
    [state.runStatus, state.pairs],
  );

  return (
    <div className="min-h-full flex flex-col">
      <TopBar
        fixtures={fixtures}
        selectedFixtureId={selectedFixtureId}
        eventBody={eventBody}
        runStatus={state.runStatus}
        costUsd={state.costUsd}
        onFixtureChange={handleFixtureChange}
        onEventBodyChange={setEventBody}
        onRunAll={handleRunAll}
      />

      <main className="flex-1 px-6 py-6 flex flex-col gap-6 max-w-[1400px] mx-auto w-full">
        {state.errorMessage && (
          <div className="border border-fabrication/40 bg-fabrication/10 text-fabrication text-sm rounded-md px-4 py-2 font-mono">
            {state.errorMessage}
          </div>
        )}

        <section className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {state.tenants.map((tenant, i) => (
            <TenantCard
              key={i}
              index={i}
              tenant={tenant}
              personas={personas}
              pairs={state.pairs}
              allTenants={state.tenants}
              disabled={state.runStatus === "running"}
              onPersonaChange={(personaId) =>
                dispatch({ type: "set_persona", index: i, personaId })
              }
            />
          ))}
        </section>

        <section className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2 bg-card border border-border rounded-lg p-4">
            <h2 className="text-xs uppercase tracking-wide text-foreground-muted mb-2">
              Fidelity vs Presentation
            </h2>
            {showCharts ? (
              <FidelityPresentationScatter pairs={state.pairs} />
            ) : (
              <div className="h-[320px] flex items-center justify-center text-foreground-muted text-sm">
                Charts populate after the run completes.
              </div>
            )}
          </div>

          <div className="bg-card border border-border rounded-lg p-4">
            <h2 className="text-xs uppercase tracking-wide text-foreground-muted mb-2">
              Trinary verdict
            </h2>
            {showCharts ? (
              <TrinaryVerdictDonut pairs={state.pairs} />
            ) : (
              <div className="h-[260px] flex items-center justify-center text-foreground-muted text-sm">
                —
              </div>
            )}
          </div>
        </section>
      </main>
    </div>
  );
}
