"use client";

import { useEffect, useState } from "react";
import { websocketUrl } from "@/lib/api";
import type { SimulationSnapshot } from "@/lib/types";

const RECONNECT_DELAY_MS = 1000;

export type ConnectionStatus = "connecting" | "open" | "closed";

/** Subscribes to the backend's /ws stream and keeps the latest snapshot in state.
 *
 * Reconnects automatically after RECONNECT_DELAY_MS if the connection drops,
 * so a brief backend restart doesn't leave the dashboard stuck.
 */
export function useSimulationSocket() {
  const [snapshot, setSnapshot] = useState<SimulationSnapshot | null>(null);
  const [status, setStatus] = useState<ConnectionStatus>("connecting");

  useEffect(() => {
    let socket: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let cancelled = false;

    const connect = () => {
      setStatus("connecting");
      socket = new WebSocket(websocketUrl());

      socket.onopen = () => setStatus("open");

      socket.onmessage = (event) => {
        const data = JSON.parse(event.data) as SimulationSnapshot;
        setSnapshot(data);
      };

      socket.onclose = () => {
        setStatus("closed");
        if (!cancelled) {
          reconnectTimer = setTimeout(connect, RECONNECT_DELAY_MS);
        }
      };

      socket.onerror = () => socket?.close();
    };

    connect();

    return () => {
      cancelled = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      socket?.close();
    };
  }, []);

  return { snapshot, status };
}
