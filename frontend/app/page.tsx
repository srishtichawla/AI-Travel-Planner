"use client";

import { useState } from "react";
import ItineraryView from "@/components/ItineraryView";
import MapView from "@/components/MapView";
import TracePanel from "@/components/TracePanel";
import TripForm from "@/components/TripForm";
import { planTrip } from "@/lib/api";
import type { PlanResponse, TripRequest } from "@/lib/types";

export default function Home() {
  const [result, setResult] = useState<PlanResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(req: TripRequest) {
    setLoading(true);
    setError(null);
    try {
      setResult(await planTrip(req));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <main className="mx-auto max-w-3xl space-y-6 p-6">
        <header>
          <h1 className="text-3xl font-bold text-gray-900">AI Travel Planner</h1>
          <p className="text-gray-600">
            Itineraries grounded in real Google Maps places, hours, and travel times.
          </p>
        </header>
        <TripForm onSubmit={run} loading={loading} />
        {error && <p className="rounded-lg bg-red-50 p-3 text-red-700">{error}</p>}
        {result && (
          <section className="space-y-4">
            <MapView days={result.days} />
            <ItineraryView days={result.days} violations={result.violations} />
            <TracePanel m={result.metrics} />
          </section>
        )}
      </main>
    </div>
  );
}
