import type { EnrichedDay, Violation } from "@/lib/types";

function endTime(start: string, mins: number) {
  const [h, m] = start.split(":").map(Number);
  const t = h * 60 + m + mins;
  const hh = String(Math.floor(t / 60) % 24).padStart(2, "0");
  const mm = String(t % 60).padStart(2, "0");
  return `${hh}:${mm}`;
}

type Props = { days: EnrichedDay[]; violations: Violation[] };

export default function ItineraryView({ days, violations }: Props) {
  return (
    <div className="space-y-4">
      {violations.length > 0 && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          <p className="mb-1 font-semibold">Heads up</p>
          <ul className="list-disc space-y-1 pl-5">
            {violations.map((v, i) => (
              <li key={i}>{v.message}</li>
            ))}
          </ul>
        </div>
      )}
      {days.map((d) => (
        <div key={d.day} className="rounded-2xl bg-white p-5 shadow">
          <h2 className="mb-3 text-lg font-semibold text-gray-900">
            Day {d.day} · {d.date}
          </h2>
          <ol className="space-y-4">
            {d.stops.map((s) => (
              <li key={s.ref}>
                {s.leg_from_prev && (
                  <p className="mb-2 text-xs text-gray-500">
                    {s.leg_from_prev.minutes} min {s.leg_from_prev.mode === "WALK" ? "walk" : "drive"} ·{" "}
                    {(s.leg_from_prev.meters / 1000).toFixed(1)} km
                    {s.leg_from_prev.estimated ? " (estimated)" : ""}
                  </p>
                )}
                <div className="flex gap-3">
                  <div className="w-24 shrink-0 text-sm font-medium text-gray-700">
                    {s.start_time}
                    <br />
                    <span className="text-gray-400">to {endTime(s.start_time, s.duration_min)}</span>
                  </div>
                  <div>
                    <p className="font-semibold text-gray-900">{s.name}</p>
                    <p className="text-sm text-gray-600">{s.rationale}</p>
                    <p className="mt-1 text-xs text-gray-500">
                      {s.category}
                      {s.rating ? ` · ★ ${s.rating}` : ""}
                      {s.price_level ? ` · ${"$".repeat(s.price_level)}` : ""}
                    </p>
                  </div>
                </div>
              </li>
            ))}
          </ol>
        </div>
      ))}
    </div>
  );
}
