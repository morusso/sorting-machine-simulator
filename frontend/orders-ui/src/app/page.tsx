"use client";

import { useCallback, useEffect, useState } from "react";
import { createOrder, deleteOrder, listOrders } from "@/lib/api";
import type { Order } from "@/lib/types";
import { CreateOrderForm } from "@/components/CreateOrderForm";
import { OrdersTable } from "@/components/OrdersTable";

export default function Home() {
  const [orders, setOrders] = useState<Order[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setOrders(await listOrders());
  }, []);

  useEffect(() => {
    let cancelled = false;
    listOrders().then(
      (data) => {
        if (!cancelled) setOrders(data);
      },
      (err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      },
    );
    return () => {
      cancelled = true;
    };
  }, []);

  const guarded = async (action: () => Promise<unknown>) => {
    setBusy(true);
    setError(null);
    try {
      await action();
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <main>
      <div className="header">
        <h1>ORDERS</h1>
      </div>

      {error && (
        <div className="error-banner" data-cy="error-banner">
          {error}
        </div>
      )}

      <CreateOrderForm
        busy={busy}
        onCreate={(customerName, destinationAddress) =>
          guarded(() => createOrder(customerName, destinationAddress))
        }
      />

      {orders ? (
        <OrdersTable orders={orders} busy={busy} onDelete={(orderId) => guarded(() => deleteOrder(orderId))} />
      ) : (
        <div className="panel">
          <div className="empty-state">Loading orders…</div>
        </div>
      )}
    </main>
  );
}
