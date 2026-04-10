/**
 * Feature flags for pipeline optimization experiments.
 *
 * Read at invocation time (not cached), so changes take effect
 * between runs without restarting the server.
 */

/** Sonnet agentic pipeline loop (replaces specialist dispatch). On by default. Set FINFLOW_PIPELINE_LOOP=0 to disable. */
export function isPipelineLoopEnabled(): boolean {
  return process.env.FINFLOW_PIPELINE_LOOP !== "0";
}
