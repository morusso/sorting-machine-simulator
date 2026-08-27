export type EngineState = "STOPPED" | "RUNNING" | "PAUSED";

export type GateState = "CLOSED" | "OPENING" | "OPEN" | "CLOSING" | "ERROR";

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

export interface Package {
  package_id: string;
  barcode: string | null;
  position: number;
  velocity: number;
  destination: number | null;
  width: number;
  length: number;
  height: number;
  status: PackageStatus;
}

export interface SimulationStatus {
  state: EngineState;
  time: number;
}

export interface ConveyorStatus {
  speed: number;
  target_speed: number;
}

export interface Statistics {
  total_packages: number;
  sorted_packages: number;
  rejected_packages: number;
  unknown_codes: number;
  scan_errors: number;
  gate_errors: number;
  error_packages: number;
  average_scan_time: number | null;
  average_sort_time: number | null;
  throughput: number;
  packages_per_second: number;
  success_rate: number | null;
}

export interface SnapshotPackage {
  id: string;
  position: number;
  gate: number | null;
  status: PackageStatus;
}

export interface SnapshotGate {
  id: number;
  position: number;
  state: GateState;
}

export interface SimulationSnapshot {
  type: "simulation_state";
  timestamp: number;
  engine_state: EngineState;
  conveyor: { speed: number; target_speed: number; length: number };
  packages: SnapshotPackage[];
  gates: SnapshotGate[];
  statistics: Statistics;
}
