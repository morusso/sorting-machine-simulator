"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { addPackage, deleteOrder, getOrder, updateOrderStatus, updateStationStatus } from "@/lib/api";
import type { AddPackageInput } from "@/lib/api";
import type { Order, OrderStatus, StationStatus } from "@/lib/types";
import { StatusBadge } from "@/components/StatusBadge";
import { StationStatusPanel } from "@/components/StationStatusPanel";
import { OrderPackagesPanel } from "@/components/OrderPackagesPanel";

const ORDER_STATUSES: OrderStatus[] = ["CREATED", "IN_PROGRESS", "COMPLETED", "CANCELLED"];

export default function OrderDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [order, setOrder] = useState<Order | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setOrder(await getOrder(id));
  }, [id]);

  useEffect(() => {
    let cancelled = false;
    getOrder(id).then(
      (data) => {
        if (!cancelled) setOrder(data);
      },
      (err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      },
    );
    return () => {
      cancelled = true;
    };
  }, [id]);

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

  const handleDelete = async () => {
    setBusy(true);
    setError(null);
    try {
      await deleteOrder(id);
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setBusy(false);
    }
  };

  return (
    <main>
      <div className="header">
        <h1>
          <Link href="/">ORDERS</Link> / {id}
        </h1>
      </div>

      {error && (
        <div className="error-banner" data-cy="error-banner">
          {error}
        </div>
      )}

      {!order ? (
        <div className="panel">
          <div className="empty-state">Loading order…</div>
        </div>
      ) : (
        <>
          <section className="panel">
            <h2>Order</h2>
            <div className="row" style={{ marginBottom: 10 }}>
              <span>Customer: {order.customer_name ?? "—"}</span>
              <span>Destination: {order.destination_address ?? "—"}</span>
              <StatusBadge status={order.status} />
            </div>
            <div className="row">
              {ORDER_STATUSES.filter((status) => status !== order.status).map((status) => (
                <button
                  key={status}
                  data-cy={`order-set-status-${status}`}
                  disabled={busy}
                  onClick={() => guarded(() => updateOrderStatus(order.order_id, status))}
                >
                  Mark {status}
                </button>
              ))}
              <button className="danger" data-cy="delete-order-button" disabled={busy} onClick={handleDelete}>
                Delete Order
              </button>
            </div>
          </section>

          <StationStatusPanel
            stations={order.station_statuses}
            busy={busy}
            onSetStatus={(stationId, status: StationStatus) =>
              guarded(() => updateStationStatus(order.order_id, stationId, status))
            }
          />

          <OrderPackagesPanel
            packages={order.packages}
            busy={busy}
            onAdd={(input: AddPackageInput) => guarded(() => addPackage(order.order_id, input))}
          />
        </>
      )}
    </main>
  );
}
