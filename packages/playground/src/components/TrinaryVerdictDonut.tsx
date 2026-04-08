import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip } from "recharts";
import type { SimilarityResult, TrinaryVerdict } from "../lib/types";

interface Props {
  pairs: SimilarityResult[];
}

const COLOR: Record<TrinaryVerdict, string> = {
  distinct_products: "#4ade80",
  reskinned_same_article: "#fbbf24",
  fabrication_risk: "#f87171",
};

const LABEL: Record<TrinaryVerdict, string> = {
  distinct_products: "Distinct",
  reskinned_same_article: "Reskinned",
  fabrication_risk: "Fabrication",
};

export default function TrinaryVerdictDonut({ pairs }: Props) {
  const counts: Record<TrinaryVerdict, number> = {
    distinct_products: 0,
    reskinned_same_article: 0,
    fabrication_risk: 0,
  };
  for (const p of pairs) {
    if (p.judgeTrinaryVerdict) counts[p.judgeTrinaryVerdict] += 1;
  }
  const total = counts.distinct_products + counts.reskinned_same_article + counts.fabrication_risk;

  if (total === 0) {
    return (
      <div className="flex h-[260px] items-center justify-center text-foreground-muted text-sm">
        Donut populates after the judge runs.
      </div>
    );
  }

  const data = (Object.keys(counts) as TrinaryVerdict[])
    .map((k) => ({ name: LABEL[k], value: counts[k], verdict: k }))
    .filter((d) => d.value > 0);

  return (
    <div className="relative h-[260px]">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            nameKey="name"
            innerRadius={60}
            outerRadius={95}
            stroke="#0a0a0c"
            strokeWidth={2}
            startAngle={90}
            endAngle={-270}
          >
            {data.map((entry) => (
              <Cell key={entry.verdict} fill={COLOR[entry.verdict]} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              background: "#14141a",
              border: "1px solid #353541",
              borderRadius: 6,
              color: "#e4e4e7",
              fontSize: 12,
            }}
          />
        </PieChart>
      </ResponsiveContainer>
      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
        <div className="text-2xl font-semibold text-foreground">
          {counts.distinct_products}/{total}
        </div>
        <div className="text-xs text-foreground-muted">distinct</div>
      </div>
    </div>
  );
}
