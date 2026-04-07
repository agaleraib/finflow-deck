import { cn } from "../../lib/cn";
import type { StageStatus } from "../../lib/types";

const STAGES = [
  { id: "market_event", label: "Market Event", sublabel: "24/7 Monitoring" },
  { id: "auto_suggest", label: "Auto-Suggest", sublabel: "Relevance Filter" },
  { id: "translate", label: "Translate", sublabel: "Quality Reference" },
  { id: "score", label: "Score", sublabel: "13 Metrics", tag: "QUALITY GATE" },
  { id: "correct", label: "Correct", sublabel: "If Needed", tag: "MAX 3 ROUNDS" },
  { id: "compliance", label: "Compliance", sublabel: "Jurisdiction Rules", tag: "HITL APPROVAL" },
  { id: "human_review", label: "Human", sublabel: "Quality Check", tag: "ADAPTIVE" },
  { id: "publish", label: "Publish", sublabel: "Multi-Channel" },
];

const STATUS_STYLES: Record<StageStatus | "pending", {
  dot: string;
  label: string;
  line: string;
}> = {
  pending: {
    dot: "bg-bg-raised border-border",
    label: "text-text-muted",
    line: "bg-border",
  },
  running: {
    dot: "bg-accent border-accent animate-pulse-ring",
    label: "text-accent",
    line: "bg-accent/30",
  },
  complete: {
    dot: "bg-success border-success",
    label: "text-text-primary",
    line: "bg-success/40",
  },
  waiting: {
    dot: "bg-info border-info animate-pulse-ring",
    label: "text-info",
    line: "bg-info/30",
  },
  approved: {
    dot: "bg-success border-success",
    label: "text-success",
    line: "bg-success/40",
  },
  rejected: {
    dot: "bg-danger border-danger",
    label: "text-danger",
    line: "bg-danger/30",
  },
  error: {
    dot: "bg-danger border-danger",
    label: "text-danger",
    line: "bg-danger/30",
  },
};

export function StageTimeline({
  stageStatuses,
}: {
  stageStatuses: Record<string, StageStatus>;
}) {
  return (
    <div className="w-[260px] border-r border-border bg-bg-sidebar p-5 overflow-y-auto">
      <h3 className="text-[10px] font-semibold tracking-[2px] uppercase text-text-muted mb-5">
        Pipeline Stages
      </h3>

      <div className="space-y-0">
        {STAGES.map((stage, i) => {
          const status = stageStatuses[stage.id] || "pending";
          const styles = STATUS_STYLES[status];
          const isLast = i === STAGES.length - 1;

          return (
            <div key={stage.id} className="relative flex gap-3">
              {/* Connector line */}
              {!isLast && (
                <div
                  className={cn(
                    "absolute left-[9px] top-[22px] w-[2px] h-[calc(100%-2px)]",
                    styles.line
                  )}
                />
              )}

              {/* Dot */}
              <div className="relative z-10 mt-[3px] flex-shrink-0">
                <div
                  className={cn(
                    "w-[20px] h-[20px] rounded-full border-2 flex items-center justify-center transition-all duration-normal",
                    styles.dot
                  )}
                >
                  {status === "complete" && (
                    <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                      <path d="M2 5L4 7L8 3" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                  )}
                  {status === "running" && (
                    <div className="w-2 h-2 rounded-full bg-white/80" />
                  )}
                  {status === "waiting" && (
                    <div className="w-2 h-2 rounded-full bg-white/80 animate-gentle-bounce" />
                  )}
                </div>
              </div>

              {/* Label */}
              <div className="pb-5 min-w-0">
                <div className={cn("text-sm font-medium transition-colors", styles.label)}>
                  {stage.label}
                </div>
                <div className="text-[11px] text-text-muted">
                  {stage.sublabel}
                </div>
                {stage.tag && (
                  <span className={cn(
                    "inline-block mt-1 text-[9px] font-semibold tracking-wider uppercase px-1.5 py-0.5 rounded",
                    status === "running" || status === "waiting"
                      ? "bg-accent/10 text-accent"
                      : "bg-bg-raised text-text-muted"
                  )}>
                    {stage.tag}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
