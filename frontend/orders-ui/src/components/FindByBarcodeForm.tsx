"use client";

import { useState } from "react";

interface Props {
  busy: boolean;
  onFind: (barcode: string) => Promise<void>;
}

export function FindByBarcodeForm({ busy, onFind }: Props) {
  const [barcode, setBarcode] = useState("");

  const submit = async () => {
    if (!barcode) return;
    await onFind(barcode);
  };

  return (
    <section className="panel">
      <h2>Find Order by Barcode</h2>
      <div className="row">
        <input
          placeholder="barcode"
          data-cy="find-barcode-input"
          value={barcode}
          onChange={(e) => setBarcode(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && submit()}
          style={{ width: 200 }}
        />
        <button data-cy="find-barcode-button" disabled={busy || !barcode} onClick={submit}>
          Find
        </button>
      </div>
    </section>
  );
}
