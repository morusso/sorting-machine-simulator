"use client";

import type { StationStatus, StationStatusEntry } from "@/lib/types";
import { StatusBadge } from "./StatusBadge";

const TRANSITIONS: StationStatus[] = ["PENDING", "PROCESSED", "ERROR"];

interface Props {
  stations: StationStatusEntry[];
  busy: boolean;
  onSetStatus: (stationId: number, status: StationStatus) => Promise<boolean>;
}

export function StationStatusPanel({ stations, busy, onSetStatus }: Props) {
  return (
    <section className="panel">
      <h2>Stations</h2>
      <div className="stations-grid">
        {stations.map((station) => (
          <div className="station-card" key={station.station_id} data-cy={`station-card-${station.station_id}`}>
            <div className="station-title">Station {station.station_id}</div>
            <StatusBadge status={station.status} />
            <div className="row" style={{ marginTop: 8 }}>
              {TRANSITIONS.filter((status) => status !== station.status).map((status) => (
                <button
                  key={status}
                  data-cy={`station-${station.station_id}-set-${status}`}
                  disabled={busy}
                  onClick={() => onSetStatus(station.station_id, status)}
                >
                  {status}
                </button>
              ))}
            </div>
            {station.processed_at && (
              <div className="station-timestamp">{new Date(station.processed_at).toLocaleString()}</div>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
