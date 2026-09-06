"use client";

import { useState } from "react";
import type { OrderPackage } from "@/lib/types";
import type { AddPackageInput } from "@/lib/api";

interface Props {
  packages: OrderPackage[];
  busy: boolean;
  onAdd: (input: AddPackageInput) => Promise<boolean>;
}

export function OrderPackagesPanel({ packages, busy, onAdd }: Props) {
  const [barcode, setBarcode] = useState("");
  const [width, setWidth] = useState("0.25");
  const [length, setLength] = useState("0.4");
  const [height, setHeight] = useState("0.2");
  const [weight, setWeight] = useState("1.0");

  const submit = async () => {
    // Only clear the barcode on success — otherwise a failed add looks
    // like it went through.
    const ok = await onAdd({
      barcode: barcode || undefined,
      width: Number(width),
      length: Number(length),
      height: Number(height),
      weight: Number(weight),
    });
    if (ok) setBarcode("");
  };

  return (
    <section className="panel">
      <h2>Packages</h2>

      {packages.length === 0 ? (
        <div className="empty-state">No packages in this order yet.</div>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Package</th>
              <th>Barcode</th>
              <th>W×L×H (m)</th>
              <th>Weight (kg)</th>
              <th>Destination</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {packages.map((pkg) => (
              <tr key={pkg.package_id} data-cy="order-package-row">
                <td>{pkg.package_id}</td>
                <td>{pkg.barcode ?? "—"}</td>
                <td>
                  {pkg.width} × {pkg.length} × {pkg.height}
                </td>
                <td>{pkg.weight}</td>
                <td>{pkg.destination ?? "—"}</td>
                <td>{pkg.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <div className="row" style={{ marginTop: 12 }}>
        <input
          placeholder="barcode (optional)"
          data-cy="package-barcode-input"
          value={barcode}
          onChange={(e) => setBarcode(e.target.value)}
          style={{ width: 160 }}
        />
        <input
          placeholder="width"
          value={width}
          onChange={(e) => setWidth(e.target.value)}
          style={{ width: 70 }}
        />
        <input
          placeholder="length"
          value={length}
          onChange={(e) => setLength(e.target.value)}
          style={{ width: 70 }}
        />
        <input
          placeholder="height"
          value={height}
          onChange={(e) => setHeight(e.target.value)}
          style={{ width: 70 }}
        />
        <input
          placeholder="weight"
          value={weight}
          onChange={(e) => setWeight(e.target.value)}
          style={{ width: 70 }}
        />
        <button className="primary" data-cy="add-package-button" disabled={busy} onClick={submit}>
          Add Package
        </button>
      </div>
    </section>
  );
}
