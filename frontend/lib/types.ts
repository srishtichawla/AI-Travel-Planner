export type TripRequest = {
  destination: string;
  days: number;
  start_date: string;
  budget_level: "budget" | "moderate" | "luxury";
  interests: string[];
  pace: "relaxed" | "balanced" | "packed";
};

export type Leg = {
  minutes: number;
  meters: number;
  mode: "WALK" | "DRIVE";
  estimated: boolean;
};

export type EnrichedStop = {
  ref: string;
  start_time: string;
  duration_min: number;
  rationale: string;
  place_id: string;
  name: string;
  category: string;
  lat: number;
  lng: number;
  address: string;
  rating: number | null;
  price_level: number | null;
  leg_from_prev: Leg | null;
};

export type EnrichedDay = {
  day: number;
  date: string;
  stops: EnrichedStop[];
};

export type Violation = {
  code: string;
  severity: "hard" | "soft";
  day: number | null;
  ref: string | null;
  message: string;
};

export type RunMetrics = {
  run_id: string;
  cost_usd: number;
  latency_ms: number;
  llm_calls: number;
  maps_calls: number;
  cache_hits: number;
  repair_rounds: number;
  first_pass_hard_violations: number;
};

export type PlanResponse = {
  days: EnrichedDay[];
  violations: Violation[];
  metrics: RunMetrics;
};
