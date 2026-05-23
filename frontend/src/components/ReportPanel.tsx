import { FileText, Download, Table, Loader2 } from "lucide-react";
import type { ReportInfo } from "@/types";

interface Props {
  reports: ReportInfo[];
  datasets: string[];
  onGenerate: (msg: string) => void;
  isStreaming: boolean;
}

export function ReportPanel({ reports, datasets, onGenerate, isStreaming }: Props) {
  const hasData = datasets.length > 0 || reports.length > 0;

  return (
    <div className="space-y-4">
      {/* Generate buttons */}
      <div className="space-y-2">
        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Generate Report</p>
        <button
          onClick={() =>
            onGenerate(
              'Generate a comprehensive PDF report with all charts and a narrative summary of the analysis so far.'
            )
          }
          disabled={isStreaming || !hasData}
          className="w-full flex items-center gap-2 bg-red-700/80 hover:bg-red-700 disabled:opacity-40 text-white text-xs rounded-lg px-3 py-2 transition-colors"
        >
          <FileText size={13} />
          PDF Report
        </button>
        <button
          onClick={() =>
            onGenerate(
              'Generate an Excel report with all loaded datasets as separate sheets.'
            )
          }
          disabled={isStreaming || !hasData}
          className="w-full flex items-center gap-2 bg-green-700/80 hover:bg-green-700 disabled:opacity-40 text-white text-xs rounded-lg px-3 py-2 transition-colors"
        >
          <Table size={13} />
          Excel Report
        </button>
      </div>

      {/* Generated reports list */}
      {reports.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Downloads</p>
          {reports.map((r, i) => (
            <a
              key={i}
              href={`/api${r.download_url}`}
              download={r.filename}
              className="flex items-center gap-2 bg-surface-secondary hover:bg-surface-tertiary border border-slate-700 rounded-lg px-3 py-2 transition-colors group"
            >
              {r.filename.endsWith(".pdf") ? (
                <FileText size={13} className="text-red-400" />
              ) : (
                <Table size={13} className="text-green-400" />
              )}
              <span className="flex-1 text-xs text-slate-300 truncate">{r.filename}</span>
              <Download size={12} className="text-slate-500 group-hover:text-white transition-colors" />
            </a>
          ))}
        </div>
      )}

      {!hasData && (
        <p className="text-xs text-slate-600 text-center py-4">
          Load data first to generate reports
        </p>
      )}
    </div>
  );
}
