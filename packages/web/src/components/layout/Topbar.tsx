import { useEffect, useState } from "react";

export function Topbar() {
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const id = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <header className="h-[52px] border-b border-border flex items-center justify-between px-6 bg-bg-app">
      <div className="flex items-center gap-3">
        <h1 className="font-serif text-lg tracking-tight">
          Fin<span className="text-accent">Flow</span>
        </h1>
        <span className="text-text-muted text-[11px] tracking-widest uppercase">
          by WordwideFX
        </span>
      </div>

      <div className="flex items-center gap-4">
        <span className="font-mono text-xs text-text-secondary">
          {time.toLocaleTimeString("en-GB", {
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
          })}
        </span>
        <div className="w-7 h-7 rounded-full bg-accent/20 border border-accent/30 flex items-center justify-center text-accent text-[11px] font-medium">
          AG
        </div>
      </div>
    </header>
  );
}
