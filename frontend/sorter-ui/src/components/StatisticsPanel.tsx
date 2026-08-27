import type { Statistics } from "@/lib/types";

interface Props {
  stats: Statistics;
}

function fmt(value: number | null, digits = 2, suffix = ""): string {
  return value === null ? "—" : `${value.toFixed(digits)}${suffix}`;
}

export function StatisticsPanel({ stats }: Props) {
  return (
    <section className="panel">
      <h2>Statistics</h2>
      <div className="stats-grid">
        <div className="stat">
          <div className="value">{stats.total_packages}</div>
          <div className="label">Total</div>
        </div>
        <div className="stat">
          <div className="value">{stats.sorted_packages}</div>
          <div className="label">Sorted</div>
        </div>
        <div className="stat">
          <div className="value">{stats.rejected_packages}</div>
          <div className="label">Rejected</div>
        </div>
        <div className="stat">
          <div className="value">{stats.error_packages}</div>
          <div className="label">Errors</div>
        </div>
        <div className="stat">
          <div className="value">
            {stats.success_rate === null ? "—" : `${(stats.success_rate * 100).toFixed(0)}%`}
          </div>
          <div className="label">Success rate</div>
        </div>
        <div className="stat">
          <div className="value">{fmt(stats.throughput, 2, " pkg/s")}</div>
          <div className="label">Throughput</div>
        </div>
        <div className="stat">
          <div className="value">{fmt(stats.average_scan_time, 2, " s")}</div>
          <div className="label">Avg scan time</div>
        </div>
        <div className="stat">
          <div className="value">{fmt(stats.average_sort_time, 2, " s")}</div>
          <div className="label">Avg sort time</div>
        </div>
      </div>
    </section>
  );
}
