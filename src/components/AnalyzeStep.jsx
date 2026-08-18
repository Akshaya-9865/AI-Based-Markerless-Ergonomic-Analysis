import { useEffect, useState } from "react";
import { api, API_BASE } from "../api";
import VideoPlayer from "./VideoPlayer";

const STAGES = [
  "Extracting video frames...",
  "Detecting pose landmarks...",
  "Calculating joint angles...",
  "Computing accelerations...",
  "Applying filters...",
  "Generating annotated video...",
  "Creating report...",
];

function stageIndex(message) {
  if (!message) return -1;
  return STAGES.findIndex((s) =>
    message.toLowerCase().includes(s.toLowerCase().slice(0, 10))
  );
}

export default function AnalyzeStep({
  upload,
  subject,
  onJobStarted,
  jobId,
  onDone,
  onBackToStart,
}) {
  const [status, setStatus] = useState(null);
  const [err, setErr] = useState("");
  const [done, setDone] = useState(false);

  // Start analysis once
  useEffect(() => {
    if (!upload?.video_id) return;
    if (jobId) return;

    async function startJob() {
      try {
        const res = await api.post("/api/analyze", {
          video_id: upload.video_id,
          subject,
          seat_reference_length_cm: subject.seat_reference_length_cm,
          seat_reference_pixel_length: subject.seat_reference_pixel_length,
        });
        onJobStarted(res.data.job_id);
      } catch (e) {
        setErr(e?.response?.data?.detail || "Failed to start analysis.");
      }
    }

    startJob();
  }, [upload, subject, jobId, onJobStarted]);

  // Poll status
  useEffect(() => {
    if (!jobId) return;
    let stopped = false;
    let timer = null;

    async function tick() {
      try {
        const res = await api.get(`/api/status/${jobId}`);
        setStatus(res.data);

        if (res.data.state?.toLowerCase() === "done") {
          stopped = true;
          clearInterval(timer);
          setDone(true);
          const r = await api.get(`/api/results/${jobId}`);
          onDone(r.data);
          return;
        }

        if (res.data.state?.toLowerCase() === "failed") {
          stopped = true;
          clearInterval(timer);
          setErr(res.data.message || "Job failed.");
          return;
        }
      } catch (e) {
        if (!stopped) setErr("Unable to fetch status.");
      }
    }

    tick();
    timer = setInterval(tick, 1200);
    return () => {
      stopped = true;
      clearInterval(timer);
    };
  }, [jobId, onDone]);

  async function cancelJob() {
    if (!jobId) return;
    try {
      await api.post(`/api/cancel/${jobId}`);
    } catch {
      setErr("Cancel failed.");
    }
  }

  const progressPct = Math.round((status?.progress ?? 0) * 100);
  const message = status?.message || "Processing...";
  const idx = stageIndex(message);
  const previewSrc = status?.preview_url ? `${API_BASE}${status.preview_url}` : null;

  return (
    <div className="glass p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-lg font-semibold">Analysis Processing</p>
          <p className="help">Job ID: {jobId || "starting..."}</p>
        </div>
        {!done && !err && (
          <div className="h-7 w-7 border-2 border-white/20 border-t-blue-400 rounded-full animate-spin" />
        )}
        {done && <div className="text-green-400 text-xl">✓</div>}
      </div>

      <p className="text-white/90">{message}</p>

      <div>
        <div className="flex justify-between text-sm mb-1 text-white/75">
          <span>{progressPct}%</span>
          <span>{status?.eta_sec ? `${status.eta_sec}s remaining` : ""}</span>
        </div>
        <div className="h-2 bg-white/10 rounded">
          <div className="h-2 bg-blue-500 rounded" style={{ width: `${progressPct}%` }} />
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-2">
        {STAGES.map((s, i) => {
          const isDone = idx >= i;
          const isActive = idx === i;
          return (
            <div key={s} className="flex items-center gap-2 p-2 rounded-lg bg-white/5 border border-white/10">
              <div className={[
                "h-6 w-6 rounded-full flex items-center justify-center text-sm font-bold",
                isDone ? "bg-green-500/80" : isActive ? "bg-blue-500/80" : "bg-white/10"
              ].join(" ")}>
                {isDone ? "✓" : i + 1}
              </div>
              <p className={isActive ? "text-blue-200 font-semibold" : "text-white/80"}>{s}</p>
            </div>
          );
        })}
      </div>

      {err && <p className="error">{err}</p>}

      <div className="flex gap-3">
        <button className="btn-ghost" onClick={onBackToStart}>Back</button>
        <button
          className="btn-primary bg-red-600 hover:bg-red-700"
          onClick={cancelJob}
          disabled={!jobId || done}
        >
          Cancel
        </button>
      </div>

      {previewSrc && (
        <div className="border border-white/15 rounded-xl p-4 bg-white/5">
          <p className="font-semibold mb-2">Live Annotated Preview</p>
          <VideoPlayer src={previewSrc} />
        </div>
      )}
    </div>
  );
}