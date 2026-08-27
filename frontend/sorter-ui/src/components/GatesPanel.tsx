import type { SnapshotGate } from "@/lib/types";

interface Props {
  gates: SnapshotGate[];
}

export function GatesPanel({ gates }: Props) {
  return (
    <section className="panel">
      <h2>Gates</h2>
      <div className="gates-grid">
        {gates.map((gate) => (
          <div key={gate.id} className={`gate-card ${gate.state}`}>
            <div>GATE {gate.id}</div>
            <div className="gate-state">{gate.state}</div>
          </div>
        ))}
      </div>
    </section>
  );
}
