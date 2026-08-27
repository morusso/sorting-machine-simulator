"use client";

import { useState } from "react";
import type { EngineState } from "@/lib/types";

interface Props {
  engineState: EngineState;
  currentSpeed: number;
  targetSpeed: number;
  busy: boolean;
  onStart: () => Promise<void>;
  onStop: () => Promise<void>;
  onReset: () => Promise<void>;
  onSetSpeed: (speed: number) => Promise<void>;
}

export function ControlPanel({
  engineState,
  currentSpeed,
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
          data-cy="start-button"
          disabled={busy || engineState === "RUNNING"}
          onClick={() => onStart()}
        >
          Start
        </button>
        <button
          data-cy="stop-button"
          disabled={busy || engineState !== "RUNNING"}
          onClick={() => onStop()}
        >
          Stop
        </button>
        <button data-cy="reset-button" disabled={busy} onClick={() => onReset()}>
          Reset
        </button>
        <span style={{ width: 1, alignSelf: "stretch", background: "var(--panel-border)" }} />
        <span data-cy="current-speed">Speed: {currentSpeed.toFixed(2)} m/s</span>
        <input
          type="number"
          step="0.1"
          min="0"
          data-cy="speed-input"
          value={speedInput}
          onChange={(e) => setSpeedInput(e.target.value)}
          style={{ width: 90 }}
        />
        <button
          data-cy="set-speed-button"
          disabled={busy || speedInput === ""}
          onClick={() => onSetSpeed(Number(speedInput))}
        >
          Set speed (m/s)
        </button>
      </div>
    </section>
  );
}
