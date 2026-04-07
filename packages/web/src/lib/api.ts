import type { Instrument, StageInfo } from "./types";

export async function fetchInstruments(): Promise<Instrument[]> {
  const res = await fetch("/api/instruments");
  if (!res.ok) throw new Error("Failed to fetch instruments");
  return res.json();
}

export async function fetchStages(): Promise<StageInfo[]> {
  const res = await fetch("/api/content-pipeline/stages");
  if (!res.ok) throw new Error("Failed to fetch stages");
  return res.json();
}
