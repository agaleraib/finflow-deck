import { motion } from "framer-motion";
import type { PipelineEvent, MetricData } from "../../lib/types";
import { cn } from "../../lib/cn";

const STAGE_LABELS: Record<string, string> = {
  market_event: "Market Event",
  auto_suggest: "Auto-Suggest",
  translate: "Translation",
  score: "Quality Score",
  correct: "Correction",
  compliance: "Compliance",
  human_review: "Human Review",
  publish: "Distribution",
};

export function EventCard({ event }: { event: PipelineEvent }) {
  const label = STAGE_LABELS[event.stage] || event.stage;

  // Metric event — special rendering
  if (event.status === "metric") {
    return <MetricEventCard event={event} />;
  }

  // Score complete — render scorecard
  if (event.stage === "score" && event.status === "complete") {
    return <ScorecardEvent event={event} />;
  }

  // Compliance with flags
  if (event.stage === "compliance" && event.data?.flags) {
    return <ComplianceEvent event={event} />;
  }

  // Human review with timeline
  if (event.stage === "human_review" && event.data?.timeline) {
    return <AdaptiveReviewEvent event={event} />;
  }

  // Publish complete
  if (event.stage === "publish" && event.status === "complete") {
    return <PublishEvent event={event} />;
  }

  // HITL waiting
  if (event.status === "waiting") {
    return (
      <EventWrapper stage={label} borderColor="border-info/40">
        <div className="flex items-center gap-3 py-2">
          <div className="w-5 h-5 rounded-full bg-info/20 border border-info/40 flex items-center justify-center animate-gentle-bounce">
            <div className="w-2 h-2 rounded-full bg-info" />
          </div>
          <span className="text-info text-sm">{event.message}</span>
        </div>
      </EventWrapper>
    );
  }

  // Approved / Rejected
  if (event.status === "approved" || event.status === "rejected") {
    const isApproved = event.status === "approved";
    return (
      <EventWrapper
        stage={label}
        borderColor={isApproved ? "border-success/40" : "border-danger/40"}
      >
        <div className="flex items-center gap-2 py-1">
          <span className={cn(
            "text-sm font-medium",
            isApproved ? "text-success" : "text-danger"
          )}>
            {isApproved ? "Approved" : "Rejected"} — {event.message}
          </span>
        </div>
      </EventWrapper>
    );
  }

  // Translation complete — show preview
  if (event.stage === "translate" && event.status === "complete") {
    return (
      <EventWrapper stage={label} borderColor="border-accent/30">
        <p className="text-sm text-text-primary">{event.message}</p>
        {event.data?.source_preview && (
          <div className="grid grid-cols-2 gap-3 mt-3">
            <div className="bg-bg-app rounded p-3">
              <div className="text-[10px] font-semibold text-text-muted uppercase tracking-wider mb-1">
                Source (EN)
              </div>
              <p className="text-xs text-text-secondary leading-relaxed">
                {String(event.data.source_preview).slice(0, 150)}...
              </p>
            </div>
            <div className="bg-bg-app rounded p-3">
              <div className="text-[10px] font-semibold text-text-muted uppercase tracking-wider mb-1">
                Translation ({String(event.data.language || "").toUpperCase()})
              </div>
              <p className="text-xs text-text-secondary leading-relaxed">
                {String(event.data.translation_preview || "").slice(0, 150)}...
              </p>
            </div>
          </div>
        )}
        {event.data?.glossary_compliance != null && (
          <div className="flex gap-4 mt-3 text-[11px]">
            <span className="text-text-secondary">
              Glossary: <span className="font-mono text-accent">{event.data.glossary_compliance}%</span>
            </span>
            <span className="text-text-secondary">
              Terms: <span className="font-mono">{event.data.terms_used}/{event.data.terms_total}</span>
            </span>
          </div>
        )}
      </EventWrapper>
    );
  }

  // Market event with headlines
  if (event.stage === "market_event" && event.status === "complete") {
    return (
      <EventWrapper stage={label} borderColor="border-warning/30">
        <p className="text-sm font-medium text-text-primary">{event.message}</p>
        <div className="flex gap-4 mt-2 text-[11px]">
          {event.data?.price && (
            <span className="text-text-secondary">
              Price: <span className="font-mono text-text-primary">{event.data.price}</span>
            </span>
          )}
          {event.data?.change_pct != null && (
            <span className={cn(
              "font-mono",
              Number(event.data.change_pct) >= 0 ? "text-success" : "text-danger"
            )}>
              {Number(event.data.change_pct) >= 0 ? "+" : ""}{event.data.change_pct}%
            </span>
          )}
          {event.data?.sentiment && (
            <span className="text-text-muted capitalize">{event.data.sentiment}</span>
          )}
        </div>
        {event.data?.headlines && (
          <div className="mt-3 space-y-1">
            {(event.data.headlines as string[]).slice(0, 3).map((h, i) => (
              <div key={i} className="flex items-start gap-2 text-[11px] text-text-secondary">
                <span className="text-text-muted mt-0.5">•</span>
                <span>{h}</span>
              </div>
            ))}
          </div>
        )}
      </EventWrapper>
    );
  }

  // Auto-suggest
  if (event.stage === "auto_suggest" && event.status === "complete") {
    return (
      <EventWrapper stage={label} borderColor="border-purple/30">
        <p className="text-sm text-text-primary">{event.message}</p>
        <div className="flex gap-3 mt-2">
          {event.data?.direction && (
            <span className={cn(
              "text-[10px] font-semibold px-2 py-0.5 rounded-full uppercase",
              event.data.direction === "bullish"
                ? "bg-success/10 text-success"
                : event.data.direction === "bearish"
                  ? "bg-danger/10 text-danger"
                  : "bg-warning/10 text-warning"
            )}>
              {event.data.direction}
            </span>
          )}
          {event.data?.impact && (
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-bg-raised text-text-secondary uppercase">
              {event.data.impact} impact
            </span>
          )}
        </div>
      </EventWrapper>
    );
  }

  // Default running / complete event
  return (
    <EventWrapper stage={label}>
      <p className="text-sm text-text-secondary">{event.message}</p>
    </EventWrapper>
  );
}


function EventWrapper({
  stage,
  borderColor = "border-border",
  children,
}: {
  stage: string;
  borderColor?: string;
  children: React.ReactNode;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      className={cn(
        "bg-bg-surface border rounded-lg p-4 border-l-[3px]",
        borderColor
      )}
    >
      <div className="text-[10px] font-semibold tracking-[1.5px] uppercase text-text-muted mb-2">
        {stage}
      </div>
      {children}
    </motion.div>
  );
}


function MetricEventCard({ event }: { event: PipelineEvent }) {
  const passed = event.data?.passed as boolean;
  const score = event.data?.score as number;
  const threshold = event.data?.threshold as number;
  const name = String(event.data?.metric || "").replace(/_/g, " ");
  const method = event.data?.method as string;

  return (
    <motion.div
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.2 }}
      className="flex items-center gap-3 px-4 py-2 bg-bg-surface/50 rounded-md"
    >
      <div className={cn(
        "w-2 h-2 rounded-full flex-shrink-0",
        passed ? "bg-success" : "bg-danger"
      )} />
      <span className="text-xs text-text-secondary capitalize flex-1 min-w-0 truncate">
        {name}
      </span>
      <span className={cn(
        "font-mono text-xs",
        passed ? "text-success" : "text-danger"
      )}>
        {score}
      </span>
      <span className="text-text-muted text-[10px]">/{threshold}</span>
      <span className={cn(
        "text-[9px] font-medium px-1.5 py-0.5 rounded uppercase",
        passed ? "bg-success/10 text-success" : "bg-danger/10 text-danger"
      )}>
        {passed ? "PASS" : "FAIL"}
      </span>
      {method === "llm" && (
        <span className="text-[9px] text-accent/50">LLM</span>
      )}
    </motion.div>
  );
}


function ScorecardEvent({ event }: { event: PipelineEvent }) {
  const scorecard = event.data?.scorecard as { metrics: MetricData[] } | undefined;
  const verdict = event.data?.verdict as string;
  const aggregate = event.data?.aggregate_score as number;

  return (
    <EventWrapper
      stage="Quality Gate"
      borderColor={verdict === "PASS" ? "border-success/40" : "border-warning/40"}
    >
      <div className="flex items-center gap-3 mb-3">
        <span className={cn(
          "text-lg font-mono font-semibold",
          verdict === "PASS" ? "text-success" : "text-warning"
        )}>
          {aggregate}/100
        </span>
        <span className={cn(
          "text-[10px] font-bold px-2 py-0.5 rounded uppercase",
          verdict === "PASS"
            ? "bg-success/10 text-success"
            : "bg-warning/10 text-warning"
        )}>
          {verdict}
        </span>
        <span className="text-[11px] text-text-secondary">
          {event.data?.passed_count}/{event.data?.total_count} metrics passed
        </span>
      </div>

      {scorecard?.metrics && (
        <div className="grid grid-cols-2 gap-x-4 gap-y-1">
          {scorecard.metrics.map((m) => (
            <div key={m.name} className="flex items-center gap-2 py-0.5">
              <div className={cn(
                "w-1.5 h-1.5 rounded-full flex-shrink-0",
                m.passed ? "bg-success" : "bg-danger"
              )} />
              <span className="text-[11px] text-text-secondary capitalize truncate flex-1">
                {m.name.replace(/_/g, " ")}
              </span>
              <span className={cn(
                "font-mono text-[11px]",
                m.passed ? "text-text-primary" : "text-danger"
              )}>
                {m.score}
              </span>
            </div>
          ))}
        </div>
      )}
    </EventWrapper>
  );
}


function ComplianceEvent({ event }: { event: PipelineEvent }) {
  const flags = event.data?.flags as Array<{
    severity: string;
    category: string;
    issue: string;
    suggestion: string;
  }>;

  return (
    <EventWrapper stage="Compliance Review" borderColor="border-warning/30">
      <p className="text-sm text-text-primary mb-3">{event.message}</p>
      {flags && (
        <div className="space-y-2">
          {flags.map((flag, i) => (
            <div key={i} className="flex gap-2 text-[11px]">
              <span className={cn(
                "flex-shrink-0 mt-0.5 w-4 h-4 rounded flex items-center justify-center text-[9px] font-bold",
                flag.severity === "critical"
                  ? "bg-danger/15 text-danger"
                  : "bg-warning/15 text-warning"
              )}>
                {flag.severity === "critical" ? "!" : "?"}
              </span>
              <div>
                <span className="text-text-secondary">{flag.issue}</span>
                {flag.suggestion && (
                  <span className="text-text-muted ml-1">→ {flag.suggestion}</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </EventWrapper>
  );
}


function AdaptiveReviewEvent({ event }: { event: PipelineEvent }) {
  const timeline = event.data?.timeline as Array<{
    phase: string;
    hitl: number;
    auto: number;
    label: string;
  }>;

  return (
    <EventWrapper stage="Human Review" borderColor="border-info/30">
      <p className="text-sm text-text-primary mb-3">{event.message}</p>
      {timeline && (
        <div className="space-y-1.5">
          {timeline.map((t, i) => (
            <div key={i} className="flex items-center gap-2 text-[11px]">
              <span className="text-text-muted w-16 flex-shrink-0">{t.phase}</span>
              <div className="flex-1 h-2 bg-bg-app rounded-full overflow-hidden flex">
                <div
                  className="h-full bg-info/60 rounded-l-full"
                  style={{ width: `${t.hitl}%` }}
                />
                <div
                  className="h-full bg-accent/40"
                  style={{ width: `${t.auto}%` }}
                />
              </div>
              <span className="text-text-muted w-24 text-right text-[10px]">{t.label}</span>
            </div>
          ))}
        </div>
      )}
    </EventWrapper>
  );
}


function PublishEvent({ event }: { event: PipelineEvent }) {
  return (
    <EventWrapper stage="Published" borderColor="border-success/40">
      <p className="text-sm font-medium text-success mb-3">{event.message}</p>
      <div className="grid grid-cols-2 gap-3 text-[11px]">
        {event.data?.channels && (
          <div>
            <span className="text-text-muted">Channels: </span>
            <span className="text-text-secondary capitalize">
              {(event.data.channels as string[]).join(", ")}
            </span>
          </div>
        )}
        {event.data?.audience_levels && (
          <div>
            <span className="text-text-muted">Levels: </span>
            <span className="text-text-secondary capitalize">
              {(event.data.audience_levels as string[]).join(", ")}
            </span>
          </div>
        )}
        {event.data?.score != null && (
          <div>
            <span className="text-text-muted">Quality: </span>
            <span className="font-mono text-accent">{event.data.score}/100</span>
          </div>
        )}
        {event.data?.duration != null && (
          <div>
            <span className="text-text-muted">Duration: </span>
            <span className="font-mono">{event.data.duration}s</span>
          </div>
        )}
      </div>
      <div className="mt-3 text-center">
        <span className="text-[10px] font-semibold tracking-widest uppercase text-success/70 border border-success/20 px-3 py-1 rounded">
          Every Document Scored Before Publication
        </span>
      </div>
    </EventWrapper>
  );
}
