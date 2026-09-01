import type { GravitySegment } from "@/lib/types";

interface Props {
  segment: GravitySegment;
}

export function GravitySegmentPanel({ segment }: Props) {
  const percent = (position: number) =>
    `${Math.min(100, Math.max(0, (position / segment.length) * 100))}%`;

  return (
    <section className="panel" data-cy="gravity-segment-panel" data-segment-id={segment.id}>
      <h2>Gravity Buffer ({segment.packages.length})</h2>
      <div className="track">
        {segment.packages.map((pkg) => (
          <div
            key={pkg.id}
            className="package-dot"
            data-cy="gravity-package-dot"
            style={{ left: percent(pkg.position) }}
            title={`${pkg.id} — ${pkg.velocity.toFixed(2)} m/s`}
          />
        ))}
      </div>
      {segment.packages.length === 0 && (
        <div className="empty-state">No packages on the gravity buffer.</div>
      )}
    </section>
  );
}
