"use client";

import { useState } from "react";
import {
  createPackage,
  pauseSimulation,
  resetSimulation,
  resumeSimulation,
  setConveyorSpeed,
  setSimulationSpeed,
  startSimulation,
  stopSimulation,
} from "@/lib/api";
import { useSimulationSocket } from "@/hooks/useSimulationSocket";
import { ControlPanel } from "@/components/ControlPanel";
import { CreatePackageForm } from "@/components/CreatePackageForm";
import { ConveyorTrack } from "@/components/ConveyorTrack";
import { GatesPanel } from "@/components/GatesPanel";
import { GravitySegmentPanel } from "@/components/GravitySegmentPanel";
import { PackagesTable } from "@/components/PackagesTable";
import { StatisticsPanel } from "@/components/StatisticsPanel";

export default function Home() {
  const { snapshot, status } = useSimulationSocket();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const guarded = async (action: () => Promise<unknown>) => {
    setBusy(true);
    setError(null);
    try {
      await action();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
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

      <CreatePackageForm busy={busy} onCreate={(barcode) => guarded(() => createPackage(barcode))} />

      {snapshot ? (
        <>
          <StatisticsPanel stats={snapshot.statistics} />
          <ConveyorTrack
            length={snapshot.conveyor.length}
            packages={snapshot.packages}
            gates={snapshot.gates}
          />
          <GatesPanel gates={snapshot.gates} />
          <GravitySegmentPanel segment={snapshot.gravity_segment} />
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
