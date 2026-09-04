"use client";

import Link from "next/link";
import type { Order } from "@/lib/types";
import { StatusBadge } from "./StatusBadge";

interface Props {
  orders: Order[];
  busy: boolean;
  onDelete: (orderId: string) => Promise<void>;
}

export function OrdersTable({ orders, busy, onDelete }: Props) {
  if (orders.length === 0) {
    return (
      <section className="panel">
        <h2>Orders</h2>
        <div className="empty-state">No orders yet.</div>
      </section>
    );
  }

  return (
    <section className="panel">
      <h2>Orders</h2>
      <table>
        <thead>
          <tr>
            <th>Order</th>
            <th>Customer</th>
            <th>Destination</th>
            <th>Status</th>
            <th>Stations</th>
            <th>Packages</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {orders.map((order) => (
            <tr key={order.order_id} data-cy="order-row">
              <td>
                <Link href={`/orders/${order.order_id}`} data-cy="order-link">
                  {order.order_id}
                </Link>
              </td>
              <td>{order.customer_name ?? "—"}</td>
              <td>{order.destination_address ?? "—"}</td>
              <td>
                <StatusBadge status={order.status} />
              </td>
              <td>
                <div className="row" style={{ gap: 4 }}>
                  {order.station_statuses.map((station) => (
                    <span key={station.station_id} className={`badge ${station.status}`}>
                      {station.station_id}
                    </span>
                  ))}
                </div>
              </td>
              <td>{order.packages.length}</td>
              <td>
                <button
                  className="danger"
                  data-cy="delete-order-button"
                  disabled={busy}
                  onClick={() => onDelete(order.order_id)}
                >
                  Delete
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
