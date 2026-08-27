import type { SnapshotGate, SnapshotPackage } from "@/lib/types";

interface Props {
  length: number;
  packages: SnapshotPackage[];
  gates: SnapshotGate[];
}

export function ConveyorTrack({ length, packages, gates }: Props) {
  const percent = (position: number) => `${Math.min(100, Math.max(0, (position / length) * 100))}%`;

  return (
    <section className="panel">
      <h2>Conveyor</h2>
      <div className="track">
        {gates.map((gate) => (
          <div key={gate.id} className="track-marker" style={{ left: percent(gate.position) }}>
            <span className="track-marker-label" style={{ left: 0 }}>
              G{gate.id}
            </span>
          </div>
        ))}
        {packages.map((pkg) => (
          <div
            key={pkg.id}
            className={`package-dot ${pkg.status}`}
            style={{ left: percent(pkg.position) }}
            title={`${pkg.id} — ${pkg.status}${pkg.gate ? ` — gate ${pkg.gate}` : ""}`}
          />
        ))}
      </div>
    </section>
  );
}
