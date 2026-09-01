import type { SnapshotPackage } from "@/lib/types";

interface Props {
  packages: SnapshotPackage[];
}

function formatEta(eta: number | null): string {
  return eta === null ? "—" : `${eta.toFixed(1)} s`;
}

export function PackagesTable({ packages }: Props) {
  return (
    <section className="panel" data-cy="packages-panel">
      <h2>Packages ({packages.length})</h2>
      {packages.length === 0 ? (
        <div className="empty-state">No packages on the line yet.</div>
      ) : (
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Position (m)</th>
              <th>Gate</th>
              <th>Status</th>
              <th>ETA</th>
            </tr>
          </thead>
          <tbody>
            {packages.map((pkg) => (
              <tr key={pkg.id} data-cy="package-row" data-package-id={pkg.id}>
                <td>{pkg.id}</td>
                <td>{pkg.position.toFixed(2)}</td>
                <td>{pkg.gate ?? "—"}</td>
                <td data-cy="package-status">{pkg.status}</td>
                <td data-cy="package-eta">{formatEta(pkg.eta)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
