import { useState, useRef, useCallback } from "react";
import type { PipelineEvent, StageStatus } from "./types";

interface SSEState {
  events: PipelineEvent[];
  stageStatuses: Record<string, StageStatus>;
  status: "idle" | "connecting" | "streaming" | "complete" | "error";
  streamingText: Record<string, string>;
}

export function useSSE() {
  const [state, setState] = useState<SSEState>({
    events: [],
    stageStatuses: {},
    status: "idle",
    streamingText: {},
  });
  const sourceRef = useRef<EventSource | null>(null);
  const streamingRef = useRef<Record<string, string>>({});

  const connect = useCallback((slug: string) => {
    // Clean up previous
    if (sourceRef.current) {
      sourceRef.current.close();
    }

    streamingRef.current = {};
    setState({
      events: [],
      stageStatuses: {},
      status: "connecting",
      streamingText: {},
    });

    const source = new EventSource(`/api/content-pipeline/run/${slug}`);
    sourceRef.current = source;

    source.onopen = () => {
      setState((s) => ({ ...s, status: "streaming" }));
    };

    source.onmessage = (e) => {
      try {
        const event: PipelineEvent = JSON.parse(e.data);

        if (event.stage === "done") {
          setState((s) => ({ ...s, status: "complete" }));
          source.close();
          return;
        }

        // Handle streaming chunks — accumulate in ref, batch update
        if (event.status === "chunk") {
          const key = event.stage;
          streamingRef.current[key] =
            (streamingRef.current[key] || "") + event.message;
          setState((s) => ({
            ...s,
            streamingText: { ...streamingRef.current },
          }));
          return;
        }

        // Map status to stage status
        let stageStatus: StageStatus = "running";
        if (event.status === "complete") stageStatus = "complete";
        else if (event.status === "waiting") stageStatus = "waiting";
        else if (event.status === "approved") stageStatus = "complete";
        else if (event.status === "rejected") stageStatus = "rejected";
        else if (event.status === "error") stageStatus = "error";

        setState((s) => ({
          ...s,
          events: [...s.events, event],
          stageStatuses: {
            ...s.stageStatuses,
            [event.stage]: stageStatus,
          },
        }));
      } catch {
        // Ignore parse errors
      }
    };

    source.onerror = () => {
      setState((s) => ({
        ...s,
        status: s.status === "streaming" ? "error" : s.status,
      }));
      source.close();
    };
  }, []);

  const disconnect = useCallback(() => {
    if (sourceRef.current) {
      sourceRef.current.close();
      sourceRef.current = null;
    }
    setState((s) => ({ ...s, status: "idle" }));
  }, []);

  return { ...state, connect, disconnect };
}
