import { cn } from "../../lib/cn";

export function StreamingText({
  text,
  label,
  stage,
}: {
  text: string;
  label: string;
  stage: string;
}) {
  if (!text) return null;

  const borderColor =
    stage === "translate"
      ? "border-accent/30"
      : stage === "correct"
        ? "border-warning/30"
        : "border-border";

  return (
    <div
      className={cn(
        "bg-bg-surface border rounded-lg p-4 border-l-[3px]",
        borderColor
      )}
    >
      <div className="text-[10px] font-semibold tracking-[1.5px] uppercase text-text-muted mb-2 flex items-center gap-2">
        {label}
        <span className="inline-block w-1.5 h-1.5 rounded-full bg-accent animate-blink" />
      </div>
      <pre className="text-xs text-text-secondary font-mono whitespace-pre-wrap leading-relaxed max-h-[200px] overflow-y-auto">
        {text}
      </pre>
    </div>
  );
}
