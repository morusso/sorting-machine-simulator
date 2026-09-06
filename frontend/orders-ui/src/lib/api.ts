import type {
  Order,
  OrderBarcode,
  OrderPackage,
  OrderStatus,
  PackageStatus,
  StationStatus,
  StationStatusEntry,
} from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`${init?.method ?? "GET"} ${path} failed: ${response.status} ${body}`);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export function listOrders(): Promise<Order[]> {
  return request<Order[]>("/api/orders");
}

export function getOrder(orderId: string): Promise<Order> {
  return request<Order>(`/api/orders/${orderId}`);
}

export function createOrder(customerName: string, destinationAddress: string): Promise<Order> {
  return request<Order>("/api/orders", {
    method: "POST",
    body: JSON.stringify({
      customer_name: customerName || null,
      destination_address: destinationAddress || null,
    }),
  });
}

export function updateOrderStatus(orderId: string, status: OrderStatus): Promise<Order> {
  return request<Order>(`/api/orders/${orderId}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}

export function deleteOrder(orderId: string): Promise<void> {
  return request<void>(`/api/orders/${orderId}`, { method: "DELETE" });
}

export interface AddPackageInput {
  package_id?: string;
  barcode?: string;
  width: number;
  length: number;
  height: number;
  weight?: number;
  destination?: number;
  status?: PackageStatus;
}

export function addPackage(orderId: string, input: AddPackageInput): Promise<OrderPackage> {
  return request<OrderPackage>(`/api/orders/${orderId}/packages`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function updateStationStatus(
  orderId: string,
  stationId: number,
  status: StationStatus,
): Promise<StationStatusEntry> {
  return request<StationStatusEntry>(`/api/orders/${orderId}/stations/${stationId}`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}

export function registerBarcode(orderId: string, barcode: string): Promise<OrderBarcode> {
  return request<OrderBarcode>(`/api/orders/${orderId}/barcodes`, {
    method: "POST",
    body: JSON.stringify({ barcode }),
  });
}

export function getOrderByBarcode(barcode: string): Promise<Order> {
  return request<Order>(`/api/orders/by-barcode/${encodeURIComponent(barcode)}`);
}
