import { useState } from "react";
import { Database, CheckCircle, Loader2 } from "lucide-react";

type Preset = { label: string; template: string };

const PRESETS: Preset[] = [
  { label: "SQLite", template: "sqlite:///./data.db" },
  { label: "PostgreSQL", template: "postgresql://user:password@localhost:5432/dbname" },
  { label: "MySQL", template: "mysql://user:password@localhost:3306/dbname" },
];

interface Props {
  onConnect: (msg: string) => void;
}

export function DatabaseConnect({ onConnect }: Props) {
  const [url, setUrl] = useState("");
  const [alias, setAlias] = useState("default");
  const [connecting, setConnecting] = useState(false);
  const [connected, setConnected] = useState(false);

  function handleConnect() {
    if (!url.trim()) return;
    setConnecting(true);
    // Send as agent message so the agent handles it via connect_database tool
    onConnect(`Connect to this database: ${url.trim()} with alias "${alias || "default"}"`);
    setTimeout(() => {
      setConnecting(false);
      setConnected(true);
    }, 800);
  }

  return (
    <div className="space-y-3">
      <div className="flex gap-1 flex-wrap">
        {PRESETS.map((p) => (
          <button
            key={p.label}
            onClick={() => setUrl(p.template)}
            className="text-xs px-2 py-1 bg-surface-tertiary hover:bg-slate-600 text-slate-300 rounded-md transition-colors"
          >
            {p.label}
          </button>
        ))}
      </div>
      <input
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        placeholder="Database URL"
        className="w-full text-xs bg-surface-primary border border-slate-700 rounded-lg px-3 py-2 text-white placeholder-slate-500 outline-none focus:border-brand-500"
      />
      <input
        value={alias}
        onChange={(e) => setAlias(e.target.value)}
        placeholder="Alias (optional)"
        className="w-full text-xs bg-surface-primary border border-slate-700 rounded-lg px-3 py-2 text-white placeholder-slate-500 outline-none focus:border-brand-500"
      />
      <button
        onClick={handleConnect}
        disabled={!url.trim() || connecting}
        className="w-full flex items-center justify-center gap-2 bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-white text-xs rounded-lg py-2 transition-colors"
      >
        {connecting ? (
          <Loader2 size={13} className="animate-spin" />
        ) : connected ? (
          <CheckCircle size={13} />
        ) : (
          <Database size={13} />
        )}
        {connecting ? "Connecting…" : connected ? "Connected" : "Connect"}
      </button>
    </div>
  );
}
