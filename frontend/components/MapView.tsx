"use client";

import { useEffect, useState } from "react";
import { APIProvider, AdvancedMarker, Map, Pin, useMap } from "@vis.gl/react-google-maps";
import type { EnrichedDay } from "@/lib/types";

function FitAndRoute({ day }: { day: EnrichedDay }) {
  const map = useMap();
  useEffect(() => {
    if (!map || day.stops.length === 0) return;
    const bounds = new google.maps.LatLngBounds();
    day.stops.forEach((s) => bounds.extend({ lat: s.lat, lng: s.lng }));
    map.fitBounds(bounds, 60);
    const line = new google.maps.Polyline({
      path: day.stops.map((s) => ({ lat: s.lat, lng: s.lng })),
      strokeColor: "#2563eb",
      strokeOpacity: 0.7,
      strokeWeight: 3,
      map,
    });
    return () => line.setMap(null);
  }, [map, day]);
  return null;
}

export default function MapView({ days }: { days: EnrichedDay[] }) {
  const [idx, setIdx] = useState(0);
  const key = process.env.NEXT_PUBLIC_GOOGLE_MAPS_KEY;
  const day = days[Math.min(idx, days.length - 1)];

  if (!key) {
    return <p className="rounded-lg bg-amber-50 p-3 text-amber-800">Map key missing in .env.local</p>;
  }
  if (!day || day.stops.length === 0) return null;

  return (
    <div className="space-y-2 rounded-2xl bg-white p-4 shadow">
      <div className="flex flex-wrap gap-2">
        {days.map((d, i) => (
          <button
            key={d.day}
            onClick={() => setIdx(i)}
            className={`rounded-full px-3 py-1 text-sm font-medium ${
              i === idx ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-700 hover:bg-gray-200"
            }`}
          >
            Day {d.day}
          </button>
        ))}
      </div>
      <APIProvider apiKey={key}>
        <Map
          defaultCenter={{ lat: day.stops[0].lat, lng: day.stops[0].lng }}
          defaultZoom={13}
          mapId="DEMO_MAP_ID"
          style={{ width: "100%", height: 380 }}
        >
          <FitAndRoute day={day} />
          {day.stops.map((s, i) => (
            <AdvancedMarker key={s.ref} position={{ lat: s.lat, lng: s.lng }} title={s.name}>
              <Pin glyph={String(i + 1)} glyphColor="#ffffff" background="#2563eb" borderColor="#1e40af" />
            </AdvancedMarker>
          ))}
        </Map>
      </APIProvider>
    </div>
  );
}
