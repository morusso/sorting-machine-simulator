import type { SnapshotPackage } from "@/lib/types";

interface Props {
  packages: SnapshotPackage[];
}

export function PackagesTable({ packages }: Props) {
  return (
    <section className="panel">
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
            </tr>
          </thead>
          <tbody>
            {packages.map((pkg) => (
              <tr key={pkg.id}>
                <td>{pkg.id}</td>
                <td>{pkg.position.toFixed(2)}</td>
                <td>{pkg.gate ?? "—"}</td>
                <td>{pkg.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
