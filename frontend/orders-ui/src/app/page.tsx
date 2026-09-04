"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { createOrder, deleteOrder, getOrderByBarcode, listOrders } from "@/lib/api";
import type { Order } from "@/lib/types";
import { CreateOrderForm } from "@/components/CreateOrderForm";
import { OrdersTable } from "@/components/OrdersTable";
import { FindByBarcodeForm } from "@/components/FindByBarcodeForm";

export default function Home() {
  const router = useRouter();
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

  // Returns whether action() succeeded, so callers (e.g. form submit
  // handlers) can tell a real failure apart from success instead of
  // assuming success just because nothing threw back out to them.
  const guarded = async (action: () => Promise<unknown>): Promise<boolean> => {
    setBusy(true);
    setError(null);
    try {
      await action();
      await refresh();
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      return false;
    } finally {
      setBusy(false);
    }
  };

  const handleFindByBarcode = async (barcode: string) => {
    setBusy(true);
    setError(null);
    try {
      const order = await getOrderByBarcode(barcode);
      router.push(`/orders/${order.order_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
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

      <FindByBarcodeForm busy={busy} onFind={handleFindByBarcode} />

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
