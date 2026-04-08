import type { NewsEvent } from "../lib/types";

interface Props {
  fixtures: NewsEvent[] | null;
  selectedFixtureId: string | null;
  eventBody: string;
  runStatus: "idle" | "running" | "complete" | "error";
  costUsd: number | null;
  onFixtureChange: (id: string | null) => void;
  onEventBodyChange: (body: string) => void;
  onRunAll: () => void;
}

export default function TopBar({
  fixtures,
  selectedFixtureId,
  eventBody,
  runStatus,
  costUsd,
  onFixtureChange,
  onEventBodyChange,
  onRunAll,
}: Props) {
  const running = runStatus === "running";
  return (
    <header className="border-b border-border bg-card">
      <div className="px-6 py-4 flex flex-col gap-3">
        <div className="flex items-baseline justify-between">
          <h1 className="text-lg font-semibold tracking-tight text-foreground">
            Uniqueness PoC <span className="text-accent">Playground</span>
          </h1>
          <div className="text-xs text-foreground-muted font-mono">
            {costUsd != null ? `cost: $${costUsd.toFixed(4)}` : "cost: —"}
            {" · "}
            <span
              className={
                runStatus === "running"
                  ? "text-accent"
                  : runStatus === "complete"
                    ? "text-distinct"
                    : runStatus === "error"
                      ? "text-fabrication"
                      : "text-foreground-muted"
              }
            >
              {runStatus}
            </span>
          </div>
        </div>

        <div className="flex flex-wrap items-start gap-3">
          <div className="flex flex-col gap-1">
            <label className="text-xs uppercase tracking-wide text-foreground-muted">
              Fixture
            </label>
            <select
              className="bg-card-elevated border border-border-strong rounded-md px-3 py-2 text-sm text-foreground focus:outline-none focus:border-accent min-w-[200px]"
              value={selectedFixtureId ?? ""}
              onChange={(e) => onFixtureChange(e.target.value || null)}
              disabled={running || !fixtures}
            >
              <option value="">— select —</option>
              {fixtures?.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.id}
                </option>
              ))}
            </select>
          </div>

          <div className="flex flex-col gap-1 flex-1 min-w-[400px]">
            <label className="text-xs uppercase tracking-wide text-foreground-muted">
              Event body
            </label>
            <textarea
              className="bg-card-elevated border border-border-strong rounded-md px-3 py-2 text-sm text-foreground font-mono leading-relaxed focus:outline-none focus:border-accent resize-y"
              rows={4}
              value={eventBody}
              onChange={(e) => onEventBodyChange(e.target.value)}
              placeholder="Paste a news event body here, or pick a fixture above to prefill."
              disabled={running}
            />
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-xs uppercase tracking-wide text-foreground-muted opacity-0">
              Run
            </label>
            <button
              className="bg-accent hover:bg-accent-dim disabled:bg-card-elevated disabled:text-foreground-muted disabled:cursor-not-allowed text-background font-semibold rounded-md px-6 py-2 text-sm transition-colors"
              onClick={onRunAll}
              disabled={running || eventBody.trim().length === 0}
            >
              {running ? "Running…" : "Run all"}
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
