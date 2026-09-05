"use client";

import { useState } from "react";
import type { EngineState } from "@/lib/types";

const SPEED_MULTIPLIER_PRESETS = [1, 2, 10, 100];

interface Props {
  engineState: EngineState;
  currentSpeed: number;
  targetSpeed: number;
  speedMultiplier: number;
  busy: boolean;
  onStart: () => Promise<boolean>;
  onPause: () => Promise<boolean>;
  onResume: () => Promise<boolean>;
  onStop: () => Promise<boolean>;
  onReset: () => Promise<boolean>;
  onSetSpeed: (speed: number) => Promise<boolean>;
  onSetSpeedMultiplier: (multiplier: number) => Promise<boolean>;
}

export function ControlPanel({
  engineState,
  currentSpeed,
  targetSpeed,
  speedMultiplier,
  busy,
  onStart,
  onPause,
  onResume,
  onStop,
  onReset,
  onSetSpeed,
  onSetSpeedMultiplier,
}: Props) {
  const [speedInput, setSpeedInput] = useState(String(targetSpeed));

  return (
    <section className="panel">
      <h2>Controls</h2>
      <div className="row">
        <button
          className="primary"
          data-cy="start-button"
          disabled={busy || engineState !== "STOPPED"}
          onClick={() => onStart()}
        >
          Start
        </button>
        <button
          data-cy="pause-button"
          disabled={busy || engineState !== "RUNNING"}
          onClick={() => onPause()}
        >
          Pause
        </button>
        <button
          data-cy="resume-button"
          disabled={busy || engineState !== "PAUSED"}
          onClick={() => onResume()}
        >
          Resume
        </button>
        <button
          data-cy="stop-button"
          disabled={busy || (engineState !== "RUNNING" && engineState !== "PAUSED")}
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
      <div className="row" style={{ marginTop: 10 }}>
        <span data-cy="current-speed-multiplier">Sim speed: x{speedMultiplier}</span>
        {SPEED_MULTIPLIER_PRESETS.map((preset) => (
          <button
            key={preset}
            className={preset === speedMultiplier ? "primary" : undefined}
            data-cy={`speed-multiplier-x${preset}`}
            disabled={busy}
            onClick={() => onSetSpeedMultiplier(preset)}
          >
            x{preset}
          </button>
        ))}
      </div>
    </section>
  );
}
