"use client";

import { useState } from "react";

interface Props {
  busy: boolean;
  onCreate: (customerName: string, destinationAddress: string) => Promise<void>;
}

export function CreateOrderForm({ busy, onCreate }: Props) {
  const [customerName, setCustomerName] = useState("");
  const [destinationAddress, setDestinationAddress] = useState("");

  const submit = async () => {
    await onCreate(customerName, destinationAddress);
    setCustomerName("");
    setDestinationAddress("");
  };

  return (
    <section className="panel">
      <h2>Create Order</h2>
      <div className="row">
        <input
          placeholder="customer name"
          data-cy="customer-name-input"
          value={customerName}
          onChange={(e) => setCustomerName(e.target.value)}
          style={{ width: 200 }}
        />
        <input
          placeholder="destination address"
          data-cy="destination-address-input"
          value={destinationAddress}
          onChange={(e) => setDestinationAddress(e.target.value)}
          style={{ width: 240 }}
        />
        <button className="primary" data-cy="create-order-button" disabled={busy} onClick={submit}>
          Create
        </button>
      </div>
    </section>
  );
}
