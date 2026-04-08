/**
 * Tiny fetch wrappers for the v1.0 backend routes. All paths go through the
 * Vite proxy in dev (`/poc/* → http://localhost:3000/poc/*`).
 */

import type {
  ContentPersona,
  NewsEvent,
  PlaygroundRunRequest,
  PlaygroundRunResponse,
} from "./types";

async function jsonGet<T>(path: string): Promise<T> {
  const res = await fetch(path);
  if (!res.ok) {
    throw new Error(`GET ${path} failed: ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as T;
}

export function fetchPersonas(): Promise<ContentPersona[]> {
  return jsonGet<ContentPersona[]>("/poc/personas");
}

export function fetchFixtures(): Promise<NewsEvent[]> {
  return jsonGet<NewsEvent[]>("/poc/fixtures");
}

export async function startRun(
  request: PlaygroundRunRequest,
): Promise<PlaygroundRunResponse> {
  const res = await fetch("/poc/runs", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`POST /poc/runs failed: ${res.status} — ${text}`);
  }
  return (await res.json()) as PlaygroundRunResponse;
}
