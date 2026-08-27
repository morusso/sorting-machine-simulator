"use client";

import { useState } from "react";
import type { EngineState } from "@/lib/types";

interface Props {
  engineState: EngineState;
  targetSpeed: number;
  busy: boolean;
  onStart: () => Promise<void>;
  onStop: () => Promise<void>;
  onReset: () => Promise<void>;
  onSetSpeed: (speed: number) => Promise<void>;
}

export function ControlPanel({
  engineState,
  targetSpeed,
  busy,
  onStart,
  onStop,
  onReset,
  onSetSpeed,
}: Props) {
  const [speedInput, setSpeedInput] = useState(String(targetSpeed));

  return (
    <section className="panel">
      <h2>Controls</h2>
      <div className="row">
        <button
          className="primary"
          disabled={busy || engineState === "RUNNING"}
          onClick={() => onStart()}
        >
          Start
        </button>
        <button disabled={busy || engineState !== "RUNNING"} onClick={() => onStop()}>
          Stop
        </button>
        <button disabled={busy} onClick={() => onReset()}>
          Reset
        </button>
        <span style={{ width: 1, alignSelf: "stretch", background: "var(--panel-border)" }} />
        <input
          type="number"
          step="0.1"
          min="0"
          value={speedInput}
          onChange={(e) => setSpeedInput(e.target.value)}
          style={{ width: 90 }}
        />
        <button
          disabled={busy || speedInput === ""}
          onClick={() => onSetSpeed(Number(speedInput))}
        >
          Set speed (m/s)
        </button>
      </div>
    </section>
  );
}
