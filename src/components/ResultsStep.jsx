import { API_BASE } from "../api";
import VideoPlayer from "./VideoPlayer";
import MetricCard from "./MetricCard";

function link(path) {
  if (!path) return "";
  return `${API_BASE}${path}`;
}

export default function ResultsStep({ result, onNew }) {
  const files = result?.files || {};
  const summary = result?.summary || {};
  const qc = summary?.video_qc || {};
  const comfort = summary?.comfort_summary || {};

  // aggregate metrics (worst-case comfort)
  const joints = Object.keys(comfort);
  const maxJerk = joints.length ? Math.max(...joints.map(j => Number(comfort[j]?.max_jerk ?? 0))) : null;
  const meanRms = joints.length
    ? (joints.reduce((acc, j) => acc + Number(comfort[j]?.rms_acc ?? 0), 0) / joints.length).toFixed(2)
    : null;
  const minComfortIdx = joints.length ? Math.min(...joints.map(j => Number(comfort[j]?.comfort_index ?? 1))).toFixed(3) : null;

  async function shareReport() {
    const url = link(files.pdf_report);
    if (!url) return;
    if (navigator.share) {
      await navigator.share({ title: "Motion Analysis Report", url });
    } else {
      await navigator.clipboard.writeText(url);
      alert("Report link copied!");
    }
  }

  return (
    <div className="space-y-6">
      {/* Key metric dashboard cards */}
      <div className="grid md:grid-cols-4 gap-4">
        <MetricCard title="FPS" value={qc.fps?.toFixed?.(2)} unit="" />
        <MetricCard title="Resolution" value={qc.width && qc.height ? `${qc.width}×${qc.height}` : "-"} />
        <MetricCard title="Mean RMS Acc" value={meanRms} unit="m/s²" note="Across joints" />
        <MetricCard title="Worst Max Jerk" value={maxJerk?.toFixed?.(2)} unit="m/s³" note="Higher → discomfort" />
      </div>

      <div className="grid md:grid-cols-3 gap-4">
        <MetricCard title="Comfort Index (min)" value={minComfortIdx} unit="" note="Higher → better" />
        <MetricCard title="Quality OK %" value={summary.quality_ok_frame_pct?.toFixed?.(1)} unit="%" />
        <MetricCard title="Frames" value={qc.nframes} unit="" />
      </div>

      {/* Annotated video */}
      <div className="glass p-5 space-y-3">
        <div className="flex items-center justify-between">
          <p className="text-lg font-semibold">Annotated Video</p>
          {files.annotated_video && (
            <a className="btn-ghost" href={link(files.annotated_video)} target="_blank" rel="noreferrer">
              Open in new tab
            </a>
          )}
        </div>
        {files.annotated_video ? (
          <VideoPlayer src={link(files.annotated_video)} />
        ) : (
          <p className="help">No annotated video found.</p>
        )}
      </div>

      {/* Downloads */}
      <div className="glass p-5 space-y-4">
        <div className="flex items-center justify-between">
          <p className="text-lg font-semibold">Downloads</p>
          <button className="btn-ghost" onClick={shareReport}>Share Report</button>
        </div>

        <div className="grid md:grid-cols-3 gap-3">
          <a className="btn-primary text-center" href={link(files.pdf_report)} target="_blank" rel="noreferrer">
            PDF Report
          </a>
          <a className="btn-ghost text-center" href={link(files.raw_landmarks_csv)} target="_blank" rel="noreferrer">
            Raw Landmarks CSV
          </a>
          <a className="btn-ghost text-center" href={link(files.angles_csv)} target="_blank" rel="noreferrer">
            Angles CSV
          </a>
          <a className="btn-ghost text-center" href={link(files.timeseries_csv)} target="_blank" rel="noreferrer">
            Timeseries CSV
          </a>
          <a className="btn-ghost text-center" href={link(files.acceleration_summary_csv)} target="_blank" rel="noreferrer">
            Acceleration Summary CSV
          </a>
        </div>

        <button className="btn-primary bg-green-600 hover:bg-green-700" onClick={onNew}>
          Start New Analysis
        </button>
      </div>
    </div>
  );
}