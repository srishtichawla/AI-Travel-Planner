import type { PlanResponse, TripRequest } from "./types";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export async function planTrip(req: TripRequest): Promise<PlanResponse> {
  const r = await fetch(`${API}/api/plan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!r.ok) {
    throw new Error(`Planning failed (HTTP ${r.status})`);
  }
  return r.json();
}
