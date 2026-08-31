import type { EncoderState, SensorState } from "@/lib/types";

interface Props {
  encoder: EncoderState;
  sensors: SensorState[];
}

const SENSOR_LABELS: Record<string, string> = {
  "SENSOR-ENTRY": "Entry",
  "SENSOR-END-OF-BELT": "End of belt",
};

export function EncoderSensorPanel({ encoder, sensors }: Props) {
  return (
    <section className="panel" data-cy="encoder-sensor-panel">
      <h2>Encoder &amp; Sensors</h2>
      <div className="row">
        <span data-cy="encoder-pulse-count">Encoder: {encoder.pulse_count} pulses</span>
      </div>
      <div className="sensors-grid">
        {sensors.map((sensor) => (
          <div
            key={sensor.id}
            className={`sensor-card ${sensor.triggered ? "triggered" : "idle"}`}
            data-cy={`sensor-${sensor.id}`}
          >
            <div>{SENSOR_LABELS[sensor.id] ?? sensor.id}</div>
            <div className="sensor-state">{sensor.triggered ? "TRIGGERED" : "IDLE"}</div>
          </div>
        ))}
      </div>
    </section>
  );
}
