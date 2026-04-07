export interface Instrument {
  slug: string;
  name: string;
  asset_class: string;
  price: number;
  price_formatted: string;
  change_pct: number;
  support: number;
  resistance: number;
  languages: string[];
}

export interface PipelineEvent {
  stage: string;
  status: string;
  message: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  data: Record<string, any>;
  timestamp: string;
}

export interface StageInfo {
  id: string;
  label: string;
  sublabel: string;
  icon: string;
  tag?: string;
}

export type StageStatus =
  | "pending"
  | "running"
  | "complete"
  | "waiting"
  | "approved"
  | "rejected"
  | "error";

export interface MetricData {
  name: string;
  score: number;
  threshold: number;
  passed: boolean;
  category: string;
  method: string;
  details: string;
}
