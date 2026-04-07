import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { fetchInstruments } from "../lib/api";
import type { Instrument } from "../lib/types";
import { InstrumentCard } from "../components/dashboard/InstrumentCard";
import { KPICard } from "../components/dashboard/KPICard";

export function DashboardPage() {
  const [instruments, setInstruments] = useState<Instrument[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchInstruments()
      .then(setInstruments)
      .catch(() => {
        // Fallback demo data if Flask not running
        setInstruments([
          { slug: "eurusd", name: "EUR/USD", asset_class: "forex", price: 1.158, price_formatted: "1.1580", change_pct: 0.32, support: 1.13, resistance: 1.1686, languages: ["es", "zh"] },
          { slug: "gold", name: "Gold", asset_class: "commodity", price: 2342.5, price_formatted: "$2,342.50", change_pct: 0.85, support: 2280, resistance: 2380, languages: ["es", "zh"] },
          { slug: "oil", name: "Brent Crude Oil", asset_class: "commodity", price: 87.35, price_formatted: "$87.35", change_pct: -0.45, support: 84, resistance: 92, languages: ["es", "zh"] },
        ]);
      })
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="p-6 max-w-[1400px]">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="mb-6"
      >
        <h2 className="font-serif text-2xl">Command Center</h2>
        <p className="text-text-secondary text-sm mt-1">
          Select an instrument to run the content pipeline
        </p>
      </motion.div>

      {/* KPIs */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <KPICard label="Daily Output" value="10+" change="+8 vs generic" index={0} />
        <KPICard label="Languages" value="40+" index={1} />
        <KPICard label="Quality Score" value="92.2" change="avg" index={2} />
        <KPICard label="Compliance" value="100%" index={3} />
      </div>

      {/* Scanning Bar */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="flex items-center gap-4 px-4 py-2.5 bg-bg-surface border border-border rounded-lg mb-6"
      >
        <span className="text-[10px] font-semibold text-text-muted uppercase tracking-widest">
          Scanning
        </span>
        {["Finnhub", "Yahoo Finance", "Economic Calendar"].map((source) => (
          <div key={source} className="flex items-center gap-1.5">
            <div className="w-1.5 h-1.5 rounded-full bg-success animate-blink" />
            <span className="text-[11px] font-mono text-text-secondary">
              {source}
            </span>
          </div>
        ))}
        <div className="ml-auto flex items-center gap-1.5">
          <span className="text-[11px] font-mono text-accent">3 events</span>
        </div>
      </motion.div>

      {/* Instruments */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        {loading ? (
          <div className="col-span-3 text-center py-12 text-text-muted">
            Loading instruments...
          </div>
        ) : (
          instruments.map((inst, i) => (
            <InstrumentCard key={inst.slug} instrument={inst} index={i} />
          ))
        )}
      </div>

      {/* Pipeline Flow Reference */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
        className="bg-bg-surface border border-border rounded-lg p-5"
      >
        <h3 className="text-[11px] font-semibold text-text-muted uppercase tracking-widest mb-4">
          Pipeline Flow
        </h3>
        <div className="flex items-center gap-2 flex-wrap">
          {[
            { label: "Market Event", sub: "24/7 Monitoring" },
            { label: "Auto-Suggest", sub: "Relevance Filter" },
            { label: "Translate", sub: "Quality Reference" },
            { label: "Score", sub: "13 Metrics", highlight: true },
            { label: "Correct", sub: "Max 3 Rounds", highlight: true },
            { label: "Compliance", sub: "HITL Approval", highlight: true },
            { label: "Human", sub: "Adaptive", highlight: true },
            { label: "Publish", sub: "Multi-Channel" },
          ].map((stage, i) => (
            <div key={stage.label} className="flex items-center gap-2">
              <div
                className={`px-3 py-1.5 rounded-md border text-xs ${
                  stage.highlight
                    ? "border-accent/30 bg-accent/5 text-accent"
                    : "border-border bg-bg-raised text-text-secondary"
                }`}
              >
                <div className="font-medium">{stage.label}</div>
                <div className="text-[10px] text-text-muted mt-0.5">
                  {stage.sub}
                </div>
              </div>
              {i < 7 && (
                <span className="text-accent text-sm">→</span>
              )}
            </div>
          ))}
        </div>
        <div className="mt-3 text-center">
          <span className="text-[10px] font-semibold tracking-widest uppercase text-warning/70 border border-warning/20 px-3 py-1 rounded">
            Every Document Scored Before Publication
          </span>
        </div>
      </motion.div>
    </div>
  );
}
