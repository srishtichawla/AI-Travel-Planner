import type { RunMetrics } from "@/lib/types";

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-gray-50 p-3">
      <p className="text-xs text-gray-500">{label}</p>
      <p className="text-lg font-semibold text-gray-900">{value}</p>
    </div>
  );
}

export default function TracePanel({ m }: { m: RunMetrics }) {
  return (
    <details className="rounded-2xl bg-white p-4 shadow">
      <summary className="cursor-pointer text-sm font-medium text-gray-700">
        Run trace · Claude ${m.llm_cost_usd.toFixed(3)} · {(m.latency_ms / 1000).toFixed(1)}s
      </summary>
      <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat label="Claude cost" value={`$${m.llm_cost_usd.toFixed(3)}`} />
        <Stat label="Maps cost (est.)" value={`$${m.maps_cost_usd.toFixed(3)}`} />
        <Stat label="Latency" value={`${(m.latency_ms / 1000).toFixed(1)}s`} />
        <Stat label="LLM calls" value={String(m.llm_calls)} />
        <Stat label="Maps calls" value={String(m.maps_calls)} />
        <Stat label="Cache hits" value={String(m.cache_hits)} />
        <Stat label="Repair rounds" value={String(m.repair_rounds)} />
        <Stat label="First-pass violations" value={String(m.first_pass_hard_violations)} />
      </div>
      <p className="mt-3 text-xs text-gray-500">
        Maps cost is estimated from list prices and usually falls inside Google&apos;s free monthly credit.
        Run ID {m.run_id}
      </p>
    </details>
  );
}
