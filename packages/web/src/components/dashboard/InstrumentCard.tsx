import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import type { Instrument } from "../../lib/types";
import { cn } from "../../lib/cn";

export function InstrumentCard({
  instrument,
  index,
}: {
  instrument: Instrument;
  index: number;
}) {
  const navigate = useNavigate();
  const isPositive = instrument.change_pct >= 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      className="bg-bg-surface border border-border rounded-lg p-5 hover:border-border-focus transition-all group cursor-pointer"
      onClick={() => navigate(`/pipeline/${instrument.slug}`)}
    >
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="text-[15px] font-medium text-text-primary">
            {instrument.name}
          </h3>
          <span className="text-[11px] text-text-muted uppercase tracking-wider">
            {instrument.asset_class}
          </span>
        </div>
        <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-success/10 text-success border border-success/20">
          live
        </span>
      </div>

      <div className="flex items-baseline gap-3 mb-4">
        <span className="font-mono text-2xl text-text-primary">
          {instrument.price_formatted}
        </span>
        <span
          className={cn(
            "font-mono text-sm",
            isPositive ? "text-success" : "text-danger"
          )}
        >
          {isPositive ? "+" : ""}
          {instrument.change_pct.toFixed(2)}%
        </span>
      </div>

      <div className="flex gap-4 text-[11px] text-text-secondary mb-4">
        <div>
          <span className="text-text-muted">S: </span>
          <span className="font-mono">{instrument.support}</span>
        </div>
        <div>
          <span className="text-text-muted">R: </span>
          <span className="font-mono">{instrument.resistance}</span>
        </div>
      </div>

      <div className="flex items-center justify-between">
        <div className="flex gap-1.5">
          {instrument.languages.map((lang) => (
            <span
              key={lang}
              className="text-[10px] px-1.5 py-0.5 rounded bg-bg-raised text-text-muted uppercase"
            >
              {lang}
            </span>
          ))}
        </div>
        <button className="text-[11px] font-medium text-accent opacity-0 group-hover:opacity-100 transition-opacity">
          Run Pipeline →
        </button>
      </div>
    </motion.div>
  );
}
