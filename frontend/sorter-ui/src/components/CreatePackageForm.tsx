"use client";

import { useState } from "react";

interface Props {
  busy: boolean;
  onCreate: (barcode: string) => Promise<void>;
}

// Mirrors the backend's placeholder DEFAULT_ROUTING_TABLE
// (app/simulation/sorting_line.py) — quick shortcuts for demo purposes.
const DEMO_BARCODES = ["5901234567890", "5900000000000", "5911111111111"];

export function CreatePackageForm({ busy, onCreate }: Props) {
  const [barcode, setBarcode] = useState("");

  const submit = async (code: string) => {
    if (!code) return;
    await onCreate(code);
    setBarcode("");
  };

  return (
    <section className="panel">
      <h2>Create Package</h2>
      <div className="row">
        <input
          placeholder="barcode"
          data-cy="barcode-input"
          value={barcode}
          onChange={(e) => setBarcode(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && submit(barcode)}
          style={{ width: 180 }}
        />
        <button
          className="primary"
          data-cy="create-package-button"
          disabled={busy || !barcode}
          onClick={() => submit(barcode)}
        >
          Create
        </button>
        {DEMO_BARCODES.map((code) => (
          <button key={code} data-cy={`demo-barcode-${code}`} disabled={busy} onClick={() => submit(code)}>
            {code}
          </button>
        ))}
      </div>
    </section>
  );
}
