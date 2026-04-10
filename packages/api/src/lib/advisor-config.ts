/**
 * Feature flags for pipeline optimization experiments.
 *
 * Read at invocation time (not cached), so changes take effect
 * between runs without restarting the server.
 */

/** Sonnet agentic pipeline loop (replaces specialist dispatch). On by default. Set FINFLOW_PIPELINE_LOOP=0 to disable. */
export function isPipelineLoopEnabled(): boolean {
  const raw = process.env.FINFLOW_PIPELINE_LOOP;
  if (raw === undefined || raw === "" || raw === "1") return true;
  if (raw === "0") return false;
  console.warn(`[pipeline-loop] Unknown FINFLOW_PIPELINE_LOOP="${raw}", treating as enabled`);
  return true;
}
