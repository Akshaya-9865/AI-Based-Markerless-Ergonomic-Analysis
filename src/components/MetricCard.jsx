export default function MetricCard({ title, value, unit, note }) {
  return (
    <div className="glass p-4">
      <p className="text-sm text-white/70">{title}</p>
      <div className="mt-1 flex items-end gap-2">
        <p className="text-2xl font-semibold">{value ?? "-"}</p>
        {unit && <p className="text-sm text-white/60 mb-1">{unit}</p>}
      </div>
      {note && <p className="text-xs text-white/55 mt-2">{note}</p>}
    </div>
  );
}