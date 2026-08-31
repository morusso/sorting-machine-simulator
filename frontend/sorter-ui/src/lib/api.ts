import type {
  ConveyorStatus,
  Package,
  SimulationSpeed,
  SimulationStatus,
  Statistics,
} from "./types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function websocketUrl(): string {
  return `${API_BASE_URL.replace(/^http/, "ws")}/ws`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`${init?.method ?? "GET"} ${path} failed: ${response.status} ${body}`);
  }
  return response.json() as Promise<T>;
}

export function createPackage(barcode: string): Promise<Package> {
  return request<Package>("/api/packages", {
    method: "POST",
    body: JSON.stringify({ barcode }),
  });
}

export function getSimulationStatus(): Promise<SimulationStatus> {
  return request<SimulationStatus>("/api/simulation/status");
}

export function startSimulation(): Promise<SimulationStatus> {
  return request<SimulationStatus>("/api/simulation/start", { method: "POST" });
}

export function pauseSimulation(): Promise<SimulationStatus> {
  return request<SimulationStatus>("/api/simulation/pause", { method: "POST" });
}

export function resumeSimulation(): Promise<SimulationStatus> {
  return request<SimulationStatus>("/api/simulation/resume", { method: "POST" });
}

export function stopSimulation(): Promise<SimulationStatus> {
  return request<SimulationStatus>("/api/simulation/stop", { method: "POST" });
}

export function resetSimulation(): Promise<SimulationStatus> {
  return request<SimulationStatus>("/api/simulation/reset", { method: "POST" });
}

export function setConveyorSpeed(speed: number): Promise<ConveyorStatus> {
  return request<ConveyorStatus>("/api/conveyor/speed", {
    method: "POST",
    body: JSON.stringify({ speed }),
  });
}

export function setSimulationSpeed(speedMultiplier: number): Promise<SimulationSpeed> {
  return request<SimulationSpeed>("/api/simulation/speed", {
    method: "POST",
    body: JSON.stringify({ speed_multiplier: speedMultiplier }),
  });
}

export function getStatistics(): Promise<Statistics> {
  return request<Statistics>("/api/statistics");
}
