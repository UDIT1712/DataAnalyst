import { useState } from "react";
import {
  Database,
  Upload,
  BarChart2,
  Table2,
  FileText,
  Trash2,
  ChevronDown,
  ChevronRight,
} from "lucide-react";
import type { ReportInfo, UploadedFile } from "@/types";
import { FileUpload } from "./FileUpload";
import { DatabaseConnect } from "./DatabaseConnect";
import { ReportPanel } from "./ReportPanel";

interface Props {
  datasets: string[];
  reports: ReportInfo[];
  activeDataset: string | null;
  onDatasetSelect: (name: string) => void;
  onSendMessage: (msg: string) => void;
  onClearChat: () => void;
  isStreaming: boolean;
}

type Section = "files" | "database" | "datasets" | "reports";

export function Sidebar({
  datasets,
  reports,
  activeDataset,
  onDatasetSelect,
  onSendMessage,
  onClearChat,
  isStreaming,
}: Props) {
  const [open, setOpen] = useState<Set<Section>>(new Set(["files", "datasets"]));
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);

  function toggle(s: Section) {
    setOpen((prev) => {
      const next = new Set(prev);
      next.has(s) ? next.delete(s) : next.add(s);
      return next;
    });
  }

  function handleFileUploaded(f: UploadedFile) {
    setUploadedFiles((prev) => [...prev, f]);
    onSendMessage(`Load the file "${f.name}" as a dataset and give me a quick summary of its contents.`);
  }

  function handleUseFile(filename: string) {
    onSendMessage(`Load the file "${filename}" and preview the first 10 rows.`);
  }

  return (
    <aside className="flex flex-col h-full bg-surface-primary border-r border-slate-700 w-64 shrink-0">
      {/* Logo */}
      <div className="flex items-center gap-2 px-4 py-4 border-b border-slate-700">
        <BarChart2 size={20} className="text-brand-500" />
        <span className="font-bold text-white text-sm">Data Analyst</span>
      </div>

      <div className="flex-1 overflow-y-auto py-2 space-y-1 px-2">
        {/* File Upload */}
        <SidebarSection
          icon={<Upload size={14} />}
          label="Upload File"
          id="files"
          open={open.has("files")}
          onToggle={() => toggle("files")}
        >
          <FileUpload onUploaded={handleFileUploaded} onUseFile={handleUseFile} />
        </SidebarSection>

        {/* Database */}
        <SidebarSection
          icon={<Database size={14} />}
          label="Database"
          id="database"
          open={open.has("database")}
          onToggle={() => toggle("database")}
        >
          <DatabaseConnect onConnect={onSendMessage} />
        </SidebarSection>

        {/* Datasets */}
        <SidebarSection
          icon={<Table2 size={14} />}
          label={`Datasets ${datasets.length > 0 ? `(${datasets.length})` : ""}`}
          id="datasets"
          open={open.has("datasets")}
          onToggle={() => toggle("datasets")}
        >
          {datasets.length === 0 ? (
            <p className="text-xs text-slate-600 py-2 text-center">No datasets loaded</p>
          ) : (
            <div className="space-y-1">
              {datasets.map((name) => (
                <button
                  key={name}
                  onClick={() => onDatasetSelect(name)}
                  className={`w-full text-left text-xs px-2 py-1.5 rounded-lg transition-colors font-mono ${
                    activeDataset === name
                      ? "bg-brand-600 text-white"
                      : "text-slate-400 hover:bg-surface-secondary hover:text-white"
                  }`}
                >
                  {name}
                </button>
              ))}
            </div>
          )}
        </SidebarSection>

        {/* Reports */}
        <SidebarSection
          icon={<FileText size={14} />}
          label={`Reports ${reports.length > 0 ? `(${reports.length})` : ""}`}
          id="reports"
          open={open.has("reports")}
          onToggle={() => toggle("reports")}
        >
          <ReportPanel
            reports={reports}
            datasets={datasets}
            onGenerate={onSendMessage}
            isStreaming={isStreaming}
          />
        </SidebarSection>
      </div>

      {/* Footer */}
      <div className="border-t border-slate-700 p-3">
        <button
          onClick={onClearChat}
          className="w-full flex items-center gap-2 text-xs text-slate-500 hover:text-red-400 hover:bg-red-900/20 rounded-lg px-2 py-1.5 transition-colors"
        >
          <Trash2 size={13} />
          Clear session
        </button>
      </div>
    </aside>
  );
}

function SidebarSection({
  icon,
  label,
  id,
  open,
  onToggle,
  children,
}: {
  icon: React.ReactNode;
  label: string;
  id: Section;
  open: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-lg overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-2 px-2 py-2 text-xs font-medium text-slate-300 hover:text-white hover:bg-surface-secondary transition-colors rounded-lg"
      >
        <span className="text-slate-500">{icon}</span>
        <span className="flex-1 text-left">{label}</span>
        {open ? (
          <ChevronDown size={12} className="text-slate-600" />
        ) : (
          <ChevronRight size={12} className="text-slate-600" />
        )}
      </button>
      {open && <div className="px-2 pb-2">{children}</div>}
    </div>
  );
}
