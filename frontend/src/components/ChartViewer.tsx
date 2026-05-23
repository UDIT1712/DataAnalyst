import { useState } from "react";
import Plot from "react-plotly.js";
import { X, Maximize2, Download, BarChart2 } from "lucide-react";
import type { ChartData } from "@/types";

interface Props {
  charts: ChartData[];
}

export function ChartViewer({ charts }: Props) {
  const [fullscreenIdx, setFullscreenIdx] = useState<number | null>(null);

  if (charts.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center opacity-50 space-y-2">
        <BarChart2 size={40} className="text-slate-500" />
        <p className="text-slate-400 text-sm">Charts will appear here</p>
      </div>
    );
  }

  return (
    <>
      <div className="space-y-4 overflow-y-auto h-full pr-1">
        {charts.map((chart, i) => (
          <div
            key={chart.id}
            className="bg-surface-secondary rounded-xl border border-slate-700 overflow-hidden"
          >
            <div className="flex items-center justify-between px-3 py-2 border-b border-slate-700">
              <span className="text-xs text-slate-400 font-medium truncate">
                {chart.title || `Chart ${i + 1}`}
              </span>
              <div className="flex gap-1">
                <button
                  onClick={() => setFullscreenIdx(i)}
                  className="p-1 rounded hover:bg-slate-700 text-slate-400 hover:text-white transition-colors"
                  title="Fullscreen"
                >
                  <Maximize2 size={13} />
                </button>
                <button
                  onClick={() => downloadChart(chart, i)}
                  className="p-1 rounded hover:bg-slate-700 text-slate-400 hover:text-white transition-colors"
                  title="Download PNG"
                >
                  <Download size={13} />
                </button>
              </div>
            </div>
            <PlotlyChart chart={chart} height={280} />
          </div>
        ))}
      </div>

      {/* Fullscreen overlay */}
      {fullscreenIdx !== null && (
        <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4">
          <div className="bg-surface-secondary rounded-xl border border-slate-600 w-full max-w-5xl max-h-[90vh] flex flex-col">
            <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700">
              <span className="text-sm text-white font-medium">
                {charts[fullscreenIdx].title || `Chart ${fullscreenIdx + 1}`}
              </span>
              <button
                onClick={() => setFullscreenIdx(null)}
                className="p-1 rounded hover:bg-slate-700 text-slate-400 hover:text-white"
              >
                <X size={16} />
              </button>
            </div>
            <div className="flex-1 overflow-hidden p-2">
              <PlotlyChart chart={charts[fullscreenIdx]} height={500} />
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function PlotlyChart({ chart, height }: { chart: ChartData; height: number }) {
  const layout: Partial<Plotly.Layout> = {
    ...chart.layout,
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    font: { color: "#cbd5e1", size: 11 },
    margin: { t: 30, r: 16, b: 40, l: 50 },
    height,
    autosize: true,
    legend: {
      bgcolor: "rgba(0,0,0,0)",
      font: { color: "#94a3b8", size: 10 },
    },
    xaxis: {
      ...((chart.layout as Record<string, unknown>)?.xaxis as object),
      gridcolor: "#334155",
      zerolinecolor: "#475569",
    },
    yaxis: {
      ...((chart.layout as Record<string, unknown>)?.yaxis as object),
      gridcolor: "#334155",
      zerolinecolor: "#475569",
    },
  };

  return (
    <Plot
      data={chart.data}
      layout={layout}
      frames={chart.frames}
      config={{ displayModeBar: false, responsive: true }}
      style={{ width: "100%" }}
      useResizeHandler
    />
  );
}

function downloadChart(chart: ChartData, idx: number) {
  import("plotly.js").then((Plotly) => {
    const div = document.createElement("div");
    Plotly.newPlot(div, chart.data, chart.layout).then(() => {
      Plotly.downloadImage(div, {
        format: "png",
        filename: chart.title || `chart_${idx + 1}`,
        width: 1200,
        height: 700,
      });
    });
  });
}
