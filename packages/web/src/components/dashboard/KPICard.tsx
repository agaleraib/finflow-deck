import { motion } from "framer-motion";

export function KPICard({
  label,
  value,
  change,
  index = 0,
}: {
  label: string;
  value: string;
  change?: string;
  index?: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.08, duration: 0.4 }}
      className="bg-bg-surface border border-border rounded-lg p-4"
    >
      <span className="text-[11px] font-medium text-text-muted uppercase tracking-wider">
        {label}
      </span>
      <div className="flex items-baseline gap-2 mt-1">
        <span className="font-mono text-[28px] text-text-primary leading-none">
          {value}
        </span>
        {change && (
          <span className="text-[11px] font-mono text-success">{change}</span>
        )}
      </div>
    </motion.div>
  );
}
