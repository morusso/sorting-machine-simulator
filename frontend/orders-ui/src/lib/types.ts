export type OrderStatus = "CREATED" | "IN_PROGRESS" | "COMPLETED" | "CANCELLED";

export type StationStatus = "PENDING" | "PROCESSED" | "ERROR";

// Mirrors app.domain.package.PackageStatus (backend/app/domain/package.py).
export type PackageStatus =
  | "CREATED"
  | "IN_TRANSIT"
  | "SCANNED"
  | "ASSIGNED"
  | "WAITING_FOR_GATE"
  | "SORTED"
  | "REJECTED"
  | "LOST"
  | "ERROR";

export interface StationStatusEntry {
  station_id: number;
  status: StationStatus;
  processed_at: string | null;
}

export interface OrderBarcode {
  barcode: string;
  registered_at: string;
}

export interface OrderPackage {
  package_id: string;
  order_id: string;
  barcode: string | null;
  width: number;
  length: number;
  height: number;
  weight: number;
  destination: number | null;
  status: PackageStatus;
  created_at: string;
  updated_at: string;
}

export interface Order {
  order_id: string;
  customer_name: string | null;
  destination_address: string | null;
  status: OrderStatus;
  created_at: string;
  updated_at: string;
  packages: OrderPackage[];
  station_statuses: StationStatusEntry[];
  barcodes: OrderBarcode[];
}
