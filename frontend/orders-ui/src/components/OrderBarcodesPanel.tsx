"use client";

import { useState } from "react";
import type { OrderBarcode } from "@/lib/types";

interface Props {
  barcodes: OrderBarcode[];
  busy: boolean;
  onRegister: (barcode: string) => Promise<boolean>;
}

export function OrderBarcodesPanel({ barcodes, busy, onRegister }: Props) {
  const [barcode, setBarcode] = useState("");

  const submit = async () => {
    if (!barcode) return;
    // Only clear the input on success — otherwise a failed registration
    // (wrong order, duplicate barcode, ...) looks like it went through.
    if (await onRegister(barcode)) setBarcode("");
  };

  return (
    <section className="panel">
      <h2>Barcodes</h2>

      {barcodes.length === 0 ? (
        <div className="empty-state">No barcodes registered for this order yet.</div>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Barcode</th>
              <th>Registered</th>
            </tr>
          </thead>
          <tbody>
            {barcodes.map((entry) => (
              <tr key={entry.barcode} data-cy="order-barcode-row">
                <td>{entry.barcode}</td>
                <td>{new Date(entry.registered_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <div className="row" style={{ marginTop: 12 }}>
        <input
          placeholder="barcode"
          data-cy="register-barcode-input"
          value={barcode}
          onChange={(e) => setBarcode(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && submit()}
          style={{ width: 180 }}
        />
        <button className="primary" data-cy="register-barcode-button" disabled={busy || !barcode} onClick={submit}>
          Register
        </button>
      </div>
    </section>
  );
}
