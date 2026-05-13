import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useICUStream } from "@/hooks/useICUStream";
import { Reading } from "@/lib/icu-data";
import { PatientList } from "@/components/icu/PatientList";
import { PatientDetail } from "@/components/icu/PatientDetail";

export const Route = createFileRoute("/")({
  component: Index,
});

function Index() {
  const { patients, connected, dismissAlarm } = useICUStream();
  const [selectedId, setSelectedId] = useState(1);
  const [acknowledged, setAcknowledged] = useState<Record<string, boolean>>({});

  // Convert the Map from useICUStream into the shape PatientList expects
  const patientSummaries = Array.from({ length: 50 }, (_, i) => {
    const id = i + 1;
    const key = `Patient #${id.toString().padStart(3, "0")}`;
    const history = patients.get(key) ?? [];
    const latest = history[history.length - 1] ?? null;

    // Convert PatientRecord → Reading shape that existing components expect
    const latestReading: Reading | null = latest
      ? {
          timestamp: latest.timestamp,
          heart_rate: latest.heart_rate,
          spo2: latest.spo2,
          systolic_bp: latest.systolic_bp,
          diastolic_bp: latest.diastolic_bp,
          mean_bp: latest.mean_bp,
          warning: latest.warning,
          risk_score:latest.risk_score,
        }
      : null;

    return { id, latest: latestReading };
  });

  // Build readings array for selected patient
  const selectedKey = `Patient #${selectedId.toString().padStart(3, "0")}`;
  const selectedHistory = patients.get(selectedKey) ?? [];
  const selectedReadings: Reading[] = selectedHistory.map((r) => ({
    timestamp: r.timestamp,
    heart_rate: r.heart_rate,
    spo2: r.spo2,
    systolic_bp: r.systolic_bp,
    diastolic_bp: r.diastolic_bp,
    mean_bp: r.mean_bp,
    warning: r.warning,
    risk_score:r.risk_score,
  }));

  const isAcked = !!acknowledged[selectedKey];

  const handleAcknowledge = () => {
    setAcknowledged((prev) => ({ ...prev, [selectedKey]: true }));
    dismissAlarm(selectedKey);
  };

  return (
    <div className="flex h-screen w-full bg-background text-foreground">
      {/* Connection status bar */}
      {!connected && (
        <div className="fixed top-0 left-0 right-0 z-50 bg-yellow-500 text-yellow-950 text-xs text-center py-1">
          Connecting to ICU stream…
        </div>
      )}

      <PatientList
        patients={patientSummaries}
        selectedId={selectedId}
        onSelect={(id) => {
          setSelectedId(id);
        }}
      />
      <PatientDetail
        patientId={selectedId}
        readings={selectedReadings}
        acknowledged={isAcked}
        onAcknowledge={handleAcknowledge}
      />
    </div>
  );
}