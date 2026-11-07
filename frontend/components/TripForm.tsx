"use client";

import { useState } from "react";
import type { TripRequest } from "@/lib/types";

type Props = {
  onSubmit: (req: TripRequest) => void;
  loading: boolean;
};

const input =
  "w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-gray-900 focus:border-blue-500 focus:outline-none";
const lbl = "mb-1 block text-sm font-medium text-gray-700";

export default function TripForm({ onSubmit, loading }: Props) {
  const [destination, setDestination] = useState("");
  const [days, setDays] = useState(1);
  const [startDate, setStartDate] = useState("");
  const [budget, setBudget] = useState<TripRequest["budget_level"]>("moderate");
  const [pace, setPace] = useState<TripRequest["pace"]>("relaxed");
  const [interests, setInterests] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    onSubmit({
      destination: destination.trim(),
      days,
      start_date: startDate,
      budget_level: budget,
      interests: interests
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean)
        .slice(0, 6),
      pace,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4 rounded-2xl bg-white p-6 shadow">
      <div>
        <label className={lbl}>Destination</label>
        <input className={input} value={destination} placeholder="Where to? e.g. Rome, Italy" required minLength={2} maxLength={80}
          onChange={(e) => setDestination(e.target.value)} />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className={lbl}>Days (1-7)</label>
          <input type="number" min={1} max={7} className={input} value={days} required
            onChange={(e) => setDays(Number(e.target.value))} />
        </div>
        <div>
          <label className={lbl}>Start date</label>
          <input type="date" className={input} value={startDate} required
            onChange={(e) => setStartDate(e.target.value)} />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className={lbl}>Budget</label>
          <select className={input} value={budget}
            onChange={(e) => setBudget(e.target.value as TripRequest["budget_level"])}>
            <option value="budget">Budget</option>
            <option value="moderate">Moderate</option>
            <option value="luxury">Luxury</option>
          </select>
        </div>
        <div>
          <label className={lbl}>Pace</label>
          <select className={input} value={pace}
            onChange={(e) => setPace(e.target.value as TripRequest["pace"])}>
            <option value="relaxed">Relaxed</option>
            <option value="balanced">Balanced</option>
            <option value="packed">Packed</option>
          </select>
        </div>
      </div>
      <div>
        <label className={lbl}>Interests (comma separated, up to 6)</label>
        <input className={input} value={interests} placeholder="food, history"
          onChange={(e) => setInterests(e.target.value)} />
      </div>
      <button type="submit" disabled={loading}
        className="w-full rounded-lg bg-blue-600 px-4 py-2 font-semibold text-white hover:bg-blue-700 disabled:opacity-50">
        {loading ? "Planning... (10-60 seconds)" : "Plan my trip"}
      </button>
    </form>
  );
}
