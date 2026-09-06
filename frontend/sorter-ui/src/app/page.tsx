"use client";

import { useEffect, useState } from "react";
import {
  createPackage,
  listOrderBarcodes,
  pauseSimulation,
  resetSimulation,
  resumeSimulation,
  setConveyorSpeed,
  setSimulationSpeed,
  startSimulation,
  stopSimulation,
} from "@/lib/api";
import type { OrderBarcodeOption } from "@/lib/types";
import { useSimulationSocket } from "@/hooks/useSimulationSocket";
import { ControlPanel } from "@/components/ControlPanel";
import { OrderBarcodePicker } from "@/components/OrderBarcodePicker";
import { ConveyorTrack } from "@/components/ConveyorTrack";
import { EncoderSensorPanel } from "@/components/EncoderSensorPanel";
import { GatesPanel } from "@/components/GatesPanel";
import { GravitySegmentPanel } from "@/components/GravitySegmentPanel";
import { PackagesTable } from "@/components/PackagesTable";
import { StatisticsPanel } from "@/components/StatisticsPanel";

export default function Home() {
  const { snapshot, status } = useSimulationSocket();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [orderBarcodes, setOrderBarcodes] = useState<OrderBarcodeOption[]>([]);

  useEffect(() => {
    let cancelled = false;
    listOrderBarcodes().then(
      (data) => {
        if (!cancelled) setOrderBarcodes(data);
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
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      return false;
    } finally {
      setBusy(false);
    }
  };

  return (
    <main>
      <div className="header">
        <h1>SORTER SIMULATOR</h1>
        <span className="status-pill" data-cy="connection-status">
          <span className={`status-dot ${status}`} />
          {status === "open" ? "connected" : status}
          {snapshot && (
            <span data-cy="engine-status"> · engine {snapshot.engine_state}</span>
          )}
        </span>
      </div>

      {error && (
        <div className="error-banner" data-cy="error-banner">
          {error}
        </div>
      )}

      <ControlPanel
        engineState={snapshot?.engine_state ?? "STOPPED"}
        currentSpeed={snapshot?.conveyor.speed ?? 0}
        targetSpeed={snapshot?.conveyor.target_speed ?? 1.0}
        speedMultiplier={snapshot?.speed_multiplier ?? 1.0}
        busy={busy}
        onStart={() => guarded(startSimulation)}
        onPause={() => guarded(pauseSimulation)}
        onResume={() => guarded(resumeSimulation)}
        onStop={() => guarded(stopSimulation)}
        onReset={() => guarded(resetSimulation)}
        onSetSpeed={(speed) => guarded(() => setConveyorSpeed(speed))}
        onSetSpeedMultiplier={(multiplier) => guarded(() => setSimulationSpeed(multiplier))}
      />

      <OrderBarcodePicker
        options={orderBarcodes}
        busy={busy}
        onCreate={(barcode) => guarded(() => createPackage(barcode))}
      />

      {snapshot ? (
        <>
          <StatisticsPanel stats={snapshot.statistics} />
          <ConveyorTrack
            length={snapshot.conveyor.length}
            packages={snapshot.packages}
            gates={snapshot.gates}
          />
          <GatesPanel gates={snapshot.gates} />
          <EncoderSensorPanel encoder={snapshot.encoder} sensors={snapshot.sensors} />
          {snapshot.gravity_segments.map((segment) => (
            <GravitySegmentPanel key={segment.id} segment={segment} />
          ))}
          <PackagesTable packages={snapshot.packages} />
        </>
      ) : (
        <div className="panel">
          <div className="empty-state">Waiting for the simulator connection…</div>
        </div>
      )}
    </main>
  );
}
