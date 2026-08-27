"use client";

import { useState } from "react";
import {
  createPackage,
  resetSimulation,
  setConveyorSpeed,
  startSimulation,
  stopSimulation,
} from "@/lib/api";
import { useSimulationSocket } from "@/hooks/useSimulationSocket";
import { ControlPanel } from "@/components/ControlPanel";
import { CreatePackageForm } from "@/components/CreatePackageForm";
import { ConveyorTrack } from "@/components/ConveyorTrack";
import { GatesPanel } from "@/components/GatesPanel";
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
        <span className={`status-pill`}>
          <span className={`status-dot ${status}`} />
          {status === "open" ? "connected" : status}
          {snapshot && ` · engine ${snapshot.engine_state}`}
        </span>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <ControlPanel
        engineState={snapshot?.engine_state ?? "STOPPED"}
        targetSpeed={snapshot?.conveyor.target_speed ?? 1.0}
        busy={busy}
        onStart={() => guarded(startSimulation)}
        onStop={() => guarded(stopSimulation)}
        onReset={() => guarded(resetSimulation)}
        onSetSpeed={(speed) => guarded(() => setConveyorSpeed(speed))}
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
