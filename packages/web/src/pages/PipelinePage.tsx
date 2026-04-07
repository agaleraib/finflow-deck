import { useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { useSSE } from "../lib/useSSE";
import { StageTimeline } from "../components/pipeline/StageTimeline";
import { EventCard } from "../components/pipeline/EventCard";
import { StreamingText } from "../components/pipeline/StreamingText";
import { cn } from "../lib/cn";

const INSTRUMENT_NAMES: Record<string, string> = {
  eurusd: "EUR/USD",
  gold: "Gold (XAU/USD)",
  oil: "Brent Crude Oil",
};

export function PipelinePage() {
  const { slug } = useParams<{ slug: string }>();
  const navigate = useNavigate();
  const { events, stageStatuses, status, streamingText, connect } = useSSE();
  const streamRef = useRef<HTMLDivElement>(null);

  // Auto-connect when slug is present
  useEffect(() => {
    if (slug && status === "idle") {
      connect(slug);
    }
  }, [slug, status, connect]);

  // Auto-scroll event stream
  useEffect(() => {
    if (streamRef.current) {
      streamRef.current.scrollTop = streamRef.current.scrollHeight;
    }
  }, [events, streamingText]);

  // No slug — show instrument selector
  if (!slug) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <h2 className="font-serif text-2xl text-text-secondary mb-2">
            Pipeline Monitor
          </h2>
          <p className="text-text-muted text-sm mb-6">
            Select an instrument from the{" "}
            <button
              onClick={() => navigate("/dashboard")}
              className="text-accent hover:underline"
            >
              Command Center
            </button>
          </p>
          <div className="flex gap-3 justify-center">
            {Object.entries(INSTRUMENT_NAMES).map(([s, name]) => (
              <button
                key={s}
                onClick={() => navigate(`/pipeline/${s}`)}
                className="px-4 py-2 bg-bg-surface border border-border rounded-lg text-sm text-text-secondary hover:text-text-primary hover:border-accent/30 transition-all"
              >
                {name}
              </button>
            ))}
          </div>
        </div>
      </div>
    );
  }

  const instrumentName = INSTRUMENT_NAMES[slug] || slug;

  // Filter out chunk and metric events for the main stream
  // (metrics are shown inline, chunks are in StreamingText)
  const displayEvents = events.filter(
    (e) => e.status !== "chunk" && e.status !== "metric"
  );

  // Collect metric events for grouping
  const metricEvents = events.filter((e) => e.status === "metric");

  return (
    <div className="flex h-full">
      {/* Left: Stage Timeline */}
      <StageTimeline stageStatuses={stageStatuses} />

      {/* Center: Event Stream */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div>
            <h2 className="font-serif text-lg">
              {instrumentName}
              <span className="text-text-muted text-sm ml-2 font-sans">
                Content Pipeline
              </span>
            </h2>
          </div>
          <div className="flex items-center gap-3">
            <StatusBadge status={status} />
            {status === "complete" && (
              <button
                onClick={() => connect(slug)}
                className="text-[11px] font-medium text-accent hover:text-accent/80 transition-colors"
              >
                Run Again
              </button>
            )}
          </div>
        </div>

        {/* Stream */}
        <div ref={streamRef} className="flex-1 overflow-y-auto p-6 space-y-3">
          {status === "connecting" && (
            <div className="flex items-center gap-3 text-text-muted text-sm py-8 justify-center">
              <div className="w-2 h-2 rounded-full bg-accent animate-blink" />
              Starting pipeline...
            </div>
          )}

          <AnimatePresence mode="popLayout">
            {displayEvents.map((event, i) => (
              <EventCard key={`${event.stage}-${event.status}-${i}`} event={event} />
            ))}
          </AnimatePresence>

          {/* Streaming text (translation / correction) */}
          {streamingText.translate && stageStatuses.translate !== "complete" && (
            <StreamingText
              text={streamingText.translate}
              label="Translating..."
              stage="translate"
            />
          )}
          {streamingText.correct && stageStatuses.correct !== "complete" && (
            <StreamingText
              text={streamingText.correct}
              label="Correcting..."
              stage="correct"
            />
          )}

          {/* Metric events grouped */}
          {metricEvents.length > 0 && stageStatuses.score !== "complete" && (
            <div className="space-y-1">
              <div className="text-[10px] font-semibold tracking-[1.5px] uppercase text-text-muted mb-2 px-4">
                Scoring — 13 Metrics
              </div>
              {metricEvents.map((e, i) => (
                <EventCard key={`metric-${i}`} event={e} />
              ))}
            </div>
          )}

          {status === "complete" && (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-center py-6"
            >
              <div className="text-success text-sm font-medium">
                Pipeline Complete
              </div>
              <p className="text-text-muted text-xs mt-1">
                All 8 stages executed successfully
              </p>
            </motion.div>
          )}
        </div>
      </div>

      {/* Right: Detail Panel */}
      <DetailPanel events={events} stageStatuses={stageStatuses} />
    </div>
  );
}


function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { bg: string; text: string; label: string; dot?: boolean }> = {
    idle: { bg: "bg-bg-raised", text: "text-text-muted", label: "Ready" },
    connecting: { bg: "bg-accent/10", text: "text-accent", label: "Connecting", dot: true },
    streaming: { bg: "bg-accent/10", text: "text-accent", label: "Running", dot: true },
    complete: { bg: "bg-success/10", text: "text-success", label: "Complete" },
    error: { bg: "bg-danger/10", text: "text-danger", label: "Error" },
  };
  const c = config[status] || config.idle;

  return (
    <span className={cn("text-[10px] font-semibold px-2.5 py-1 rounded-full flex items-center gap-1.5 uppercase tracking-wider", c.bg, c.text)}>
      {c.dot && <span className="w-1.5 h-1.5 rounded-full bg-current animate-blink" />}
      {c.label}
    </span>
  );
}


function DetailPanel({
  events,
  stageStatuses,
}: {
  events: import("../lib/types").PipelineEvent[];
  stageStatuses: Record<string, import("../lib/types").StageStatus>;
}) {
  // Extract latest relevant data
  const marketEvent = events.find(
    (e) => e.stage === "market_event" && e.status === "complete"
  );
  const scoreEvent = events.find(
    (e) => e.stage === "score" && e.status === "complete"
  );
  const publishEvent = events.find(
    (e) => e.stage === "publish" && e.status === "complete"
  );

  const completedStages = Object.values(stageStatuses).filter(
    (s) => s === "complete"
  ).length;

  return (
    <div className="w-[300px] border-l border-border bg-bg-sidebar p-5 overflow-y-auto">
      <h3 className="text-[10px] font-semibold tracking-[2px] uppercase text-text-muted mb-4">
        Details
      </h3>

      {/* Progress */}
      <div className="mb-6">
        <div className="flex justify-between text-[11px] mb-1.5">
          <span className="text-text-secondary">Progress</span>
          <span className="font-mono text-text-primary">{completedStages}/8</span>
        </div>
        <div className="h-1.5 bg-bg-app rounded-full overflow-hidden">
          <div
            className="h-full bg-accent rounded-full transition-all duration-500"
            style={{ width: `${(completedStages / 8) * 100}%` }}
          />
        </div>
      </div>

      {/* Market Context */}
      {marketEvent && (
        <div className="mb-6">
          <div className="text-[10px] font-semibold tracking-[1.5px] uppercase text-text-muted mb-2">
            Market Context
          </div>
          <div className="space-y-1.5 text-[11px]">
            <div className="flex justify-between">
              <span className="text-text-muted">Price</span>
              <span className="font-mono text-text-primary">
                {String(marketEvent.data.price)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-muted">Change</span>
              <span className={cn(
                "font-mono",
                Number(marketEvent.data.change_pct) >= 0
                  ? "text-success"
                  : "text-danger"
              )}>
                {Number(marketEvent.data.change_pct) >= 0 ? "+" : ""}
                {marketEvent.data.change_pct}%
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-muted">Sentiment</span>
              <span className="text-text-secondary capitalize">
                {String(marketEvent.data.sentiment)}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Quality Score */}
      {scoreEvent && (
        <div className="mb-6">
          <div className="text-[10px] font-semibold tracking-[1.5px] uppercase text-text-muted mb-2">
            Quality Score
          </div>
          <div className="flex items-baseline gap-2">
            <span className={cn(
              "font-mono text-2xl",
              scoreEvent.data.verdict === "PASS" ? "text-success" : "text-warning"
            )}>
              {scoreEvent.data.aggregate_score}
            </span>
            <span className="text-text-muted text-sm">/100</span>
          </div>
          <div className="text-[11px] text-text-secondary mt-1">
            {scoreEvent.data.passed_count}/{scoreEvent.data.total_count} metrics passed
          </div>
          {scoreEvent.data.failed_metrics && (scoreEvent.data.failed_metrics as string[]).length > 0 && (
            <div className="mt-2 text-[11px] text-danger/70">
              Failed: {(scoreEvent.data.failed_metrics as string[]).map(m => m.replace(/_/g, " ")).join(", ")}
            </div>
          )}
        </div>
      )}

      {/* Pipeline Stats */}
      {publishEvent && (
        <div className="mb-6">
          <div className="text-[10px] font-semibold tracking-[1.5px] uppercase text-text-muted mb-2">
            Pipeline Stats
          </div>
          <div className="space-y-1.5 text-[11px]">
            <div className="flex justify-between">
              <span className="text-text-muted">Duration</span>
              <span className="font-mono text-text-primary">{publishEvent.data.duration}s</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-muted">Corrections</span>
              <span className="font-mono text-text-primary">{publishEvent.data.corrections}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-muted">Language</span>
              <span className="text-text-primary">{publishEvent.data.language}</span>
            </div>
          </div>
        </div>
      )}

      {/* Deck reference */}
      <div className="mt-auto pt-4 border-t border-border">
        <div className="text-[10px] text-text-muted leading-relaxed">
          Pipeline matches the FinFlow deck: Market Event → Auto-Suggest → Translate → Score → Correct → Compliance → Human → Publish
        </div>
      </div>
    </div>
  );
}
