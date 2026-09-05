"use client";

import { useState } from "react";
import type { OrderBarcodeOption } from "@/lib/types";

interface Props {
  options: OrderBarcodeOption[];
  busy: boolean;
  onCreate: (barcode: string) => Promise<boolean>;
}

export function OrderBarcodePicker({ options, busy, onCreate }: Props) {
  const [selected, setSelected] = useState("");

  const selectedOption = options.find((option) => option.barcode === selected) ?? null;

  const submit = async () => {
    if (!selected) return;
    // Only clear the selection on success — otherwise a failed create
    // looks like it went through.
    if (await onCreate(selected)) setSelected("");
  };

  return (
    <section className="panel">
      <h2>Create Package From Order</h2>

      {options.length === 0 ? (
        <div className="empty-state">
          No barcodes registered in the order storage service yet.
        </div>
      ) : (
        <>
          <div className="row">
            <select
              data-cy="order-barcode-select"
              value={selected}
              onChange={(e) => setSelected(e.target.value)}
            >
              <option value="">select a barcode…</option>
              {options.map((option) => (
                <option key={option.barcode} value={option.barcode}>
                  {option.barcode} — {option.customer_name ?? "no customer"} ({option.order_id})
                </option>
              ))}
            </select>
            <button
              className="primary"
              data-cy="create-from-order-button"
              disabled={busy || !selected}
              onClick={submit}
            >
              Create
            </button>
          </div>

          {selectedOption && (
            <div className="row" data-cy="order-barcode-details" style={{ marginTop: 10 }}>
              <span>Order: {selectedOption.order_id}</span>
              <span>Customer: {selectedOption.customer_name ?? "—"}</span>
              <span>Destination: {selectedOption.destination_address ?? "—"}</span>
              <span>Status: {selectedOption.order_status}</span>
            </div>
          )}
        </>
      )}
    </section>
  );
}
