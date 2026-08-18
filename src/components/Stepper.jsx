export default function Stepper({ step }) {
  const items = [
    { n: 1, label: "Upload" },
    { n: 2, label: "Subject" },
    { n: 3, label: "Processing" },
    { n: 4, label: "Results" },
  ];

  return (
    <div className="glass p-4 flex items-center justify-between gap-3">
      {items.map((it, idx) => {
        const active = step === it.n;
        const done = step > it.n;
        return (
          <div key={it.n} className="flex items-center gap-3 flex-1">
            <div
              className={[
                "h-9 w-9 rounded-full flex items-center justify-center font-bold",
                done ? "bg-green-500/80" : active ? "bg-blue-500/80" : "bg-white/10",
                "border border-white/15",
              ].join(" ")}
            >
              {done ? "✓" : it.n}
            </div>
            <div className="flex-1">
              <p className={active ? "text-white font-semibold" : "text-white/70"}>{it.label}</p>
              {active && <div className="h-1 mt-1 rounded bg-white/10 overflow-hidden">
                <div className="h-1 w-2/3 bg-blue-500 animate-pulse" />
              </div>}
            </div>
            {idx !== items.length - 1 && <div className="w-full max-w-[40px] h-[1px] bg-white/15" />}
          </div>
        );
      })}
    </div>
  );
}