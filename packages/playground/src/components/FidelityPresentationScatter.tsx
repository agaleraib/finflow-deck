import {
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  Legend,
} from "recharts";
import type { SimilarityResult, TrinaryVerdict } from "../lib/types";

interface Props {
  pairs: SimilarityResult[];
}

interface ScatterDot {
  pairId: string;
  x: number; // presentation
  y: number; // fidelity
}

const VERDICT_COLOR: Record<TrinaryVerdict, string> = {
  distinct_products: "#4ade80",
  reskinned_same_article: "#fbbf24",
  fabrication_risk: "#f87171",
};

const VERDICT_LABEL: Record<TrinaryVerdict, string> = {
  distinct_products: "Distinct",
  reskinned_same_article: "Reskinned",
  fabrication_risk: "Fabrication risk",
};

function partition(pairs: SimilarityResult[]): Record<TrinaryVerdict, ScatterDot[]> {
  const out: Record<TrinaryVerdict, ScatterDot[]> = {
    distinct_products: [],
    reskinned_same_article: [],
    fabrication_risk: [],
  };
  for (const p of pairs) {
    const v = p.judgeTrinaryVerdict;
    const x = p.judgePresentationSimilarity;
    const y = p.judgeFactualFidelity;
    if (!v || x == null || y == null) continue;
    out[v].push({ pairId: p.pairId, x, y });
  }
  return out;
}

export default function FidelityPresentationScatter({ pairs }: Props) {
  const partitioned = partition(pairs);
  const total = pairs.filter((p) => p.judgeTrinaryVerdict).length;

  if (total === 0) {
    return (
      <div className="flex h-[320px] items-center justify-center text-foreground-muted text-sm">
        Scatter populates after the judge runs.
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={320}>
      <ScatterChart margin={{ top: 16, right: 24, bottom: 32, left: 8 }}>
        <CartesianGrid stroke="#262630" strokeDasharray="3 3" />
        <XAxis
          type="number"
          dataKey="x"
          name="Presentation"
          domain={[0, 1]}
          tick={{ fill: "#a1a1aa", fontSize: 11 }}
          stroke="#353541"
          label={{
            value: "Presentation similarity",
            position: "insideBottom",
            offset: -16,
            fill: "#a1a1aa",
            fontSize: 12,
          }}
        />
        <YAxis
          type="number"
          dataKey="y"
          name="Fidelity"
          domain={[0, 1]}
          tick={{ fill: "#a1a1aa", fontSize: 11 }}
          stroke="#353541"
          label={{
            value: "Factual fidelity",
            angle: -90,
            position: "insideLeft",
            fill: "#a1a1aa",
            fontSize: 12,
          }}
        />
        <ReferenceLine x={0.5} stroke="#d97757" strokeDasharray="4 4" />
        <ReferenceLine y={0.9} stroke="#d97757" strokeDasharray="4 4" />
        <Tooltip
          cursor={{ stroke: "#d97757", strokeWidth: 1 }}
          contentStyle={{
            background: "#14141a",
            border: "1px solid #353541",
            borderRadius: 6,
            color: "#e4e4e7",
            fontSize: 12,
          }}
          formatter={(value: number) => value.toFixed(2)}
          labelFormatter={(_, payload) => {
            const first = payload?.[0]?.payload as ScatterDot | undefined;
            return first?.pairId ?? "";
          }}
        />
        <Legend
          wrapperStyle={{ fontSize: 12, color: "#a1a1aa" }}
          formatter={(value) => <span style={{ color: "#a1a1aa" }}>{value}</span>}
        />
        {(Object.keys(partitioned) as TrinaryVerdict[]).map((verdict) => (
          <Scatter
            key={verdict}
            name={VERDICT_LABEL[verdict]}
            data={partitioned[verdict]}
            fill={VERDICT_COLOR[verdict]}
          />
        ))}
      </ScatterChart>
    </ResponsiveContainer>
  );
}
