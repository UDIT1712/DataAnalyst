import { useState } from "react";
import { v4 as uuidv4 } from "uuid";
import { BarChart2, MessageSquare, Table2, LayoutGrid } from "lucide-react";

import { useAgentStream } from "@/hooks/useAgentStream";
import { ChatInterface } from "@/components/ChatInterface";
import { ChartViewer } from "@/components/ChartViewer";
import { DataTable } from "@/components/DataTable";
import { Sidebar } from "@/components/Sidebar";

type RightTab = "charts" | "table";

const THREAD_ID = uuidv4();

const SUGGESTIONS = [
  "Show me the schema of the database",
  "List all uploaded files",
  "Give me a statistical summary",
  "Detect anomalies in the data",
  "Create a correlation heatmap",
  "Run a trend analysis",
];

export default function App() {
  const {
    messages,
    charts,
    datasets,
    reports,
    isStreaming,
    activeTools,
    sendMessage,
    stopStream,
    clearChat,
  } = useAgentStream(THREAD_ID);

  const [rightTab, setRightTab] = useState<RightTab>("charts");
  const [activeDataset, setActiveDataset] = useState<string | null>(null);

  function handleDatasetSelect(name: string) {
    setActiveDataset(name);
    setRightTab("table");
  }

  return (
    <div className="flex h-screen overflow-hidden bg-surface-primary">
      {/* Left: Sidebar */}
      <Sidebar
        datasets={datasets}
        reports={reports}
        activeDataset={activeDataset}
        onDatasetSelect={handleDatasetSelect}
        onSendMessage={sendMessage}
        onClearChat={clearChat}
        isStreaming={isStreaming}
      />

      {/* Center: Chat */}
      <main className="flex flex-col flex-1 min-w-0 border-r border-slate-700">
        <header className="flex items-center gap-2 px-4 py-3 border-b border-slate-700 bg-surface-primary">
          <MessageSquare size={16} className="text-brand-500" />
          <span className="font-semibold text-white text-sm">Chat</span>
          {isStreaming && (
            <span className="ml-auto flex items-center gap-1.5 text-xs text-brand-400">
              <span className="w-1.5 h-1.5 bg-brand-400 rounded-full animate-pulse" />
              Analyzing…
            </span>
          )}
        </header>
        <div className="flex-1 overflow-hidden">
          <ChatInterface
            messages={messages}
            isStreaming={isStreaming}
            activeTools={activeTools}
            onSend={sendMessage}
            onStop={stopStream}
            suggestions={messages.length === 0 ? SUGGESTIONS : []}
          />
        </div>
      </main>

      {/* Right: Charts / Table */}
      <aside className="flex flex-col w-[420px] shrink-0">
        {/* Tab bar */}
        <div className="flex items-center border-b border-slate-700 bg-surface-primary px-2">
          <TabButton
            icon={<BarChart2 size={14} />}
            label={`Charts${charts.length > 0 ? ` (${charts.length})` : ""}`}
            active={rightTab === "charts"}
            onClick={() => setRightTab("charts")}
          />
          <TabButton
            icon={<Table2 size={14} />}
            label={`Table${activeDataset ? ` · ${activeDataset}` : ""}`}
            active={rightTab === "table"}
            onClick={() => setRightTab("table")}
          />
        </div>

        {/* Tab content */}
        <div className="flex-1 overflow-hidden p-3">
          {rightTab === "charts" ? (
            <ChartViewer charts={charts} />
          ) : (
            <DataTable datasetName={activeDataset} />
          )}
        </div>
      </aside>
    </div>
  );
}

function TabButton({
  icon,
  label,
  active,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-1.5 px-3 py-3 text-xs font-medium border-b-2 transition-colors ${
        active
          ? "border-brand-500 text-white"
          : "border-transparent text-slate-500 hover:text-slate-300"
      }`}
    >
      {icon}
      {label}
    </button>
  );
}
