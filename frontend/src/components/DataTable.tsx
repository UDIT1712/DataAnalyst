import { useEffect, useMemo, useState } from "react";
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  flexRender,
  type SortingState,
  type ColumnDef,
} from "@tanstack/react-table";
import { ChevronUp, ChevronDown, ChevronsUpDown, Table2, Search } from "lucide-react";
import axios from "axios";

interface Props {
  datasetName: string | null;
}

export function DataTable({ datasetName }: Props) {
  const [rawData, setRawData] = useState<Record<string, unknown>[]>([]);
  const [sorting, setSorting] = useState<SortingState>([]);
  const [globalFilter, setGlobalFilter] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!datasetName) return;
    setLoading(true);
    // Fetch preview via chat endpoint asking for more rows
    // We use the /api/chat endpoint — a simple shortcut is to just preview in memory
    // Since data lives in backend session, we could add a dedicated preview endpoint
    // For now we use the stored query result endpoint
    axios
      .post("/api/chat", {
        thread_id: `preview_${datasetName}`,
        messages: [{ role: "user", content: `preview_dataset:${datasetName}:500` }],
      })
      .catch(() => null)
      .finally(() => setLoading(false));
  }, [datasetName]);

  const columns = useMemo<ColumnDef<Record<string, unknown>>[]>(() => {
    if (rawData.length === 0) return [];
    return Object.keys(rawData[0]).map((key) => ({
      accessorKey: key,
      header: key,
      cell: (info) => {
        const val = info.getValue();
        if (val === null || val === undefined) return <span className="text-slate-600 italic">null</span>;
        const str = String(val);
        return <span title={str}>{str.slice(0, 80)}{str.length > 80 ? "…" : ""}</span>;
      },
    }));
  }, [rawData]);

  const table = useReactTable({
    data: rawData,
    columns,
    state: { sorting, globalFilter },
    onSortingChange: setSorting,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: { pagination: { pageSize: 50 } },
  });

  if (!datasetName) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center opacity-50 space-y-2">
        <Table2 size={40} className="text-slate-500" />
        <p className="text-slate-400 text-sm">Load a dataset to view the table</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin w-6 h-6 border-2 border-brand-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  if (rawData.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full opacity-50 space-y-2">
        <Table2 size={40} className="text-slate-500" />
        <p className="text-slate-400 text-sm">Dataset loaded — ask the agent to show data</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full gap-2">
      {/* Search */}
      <div className="relative">
        <Search size={14} className="absolute left-2.5 top-2.5 text-slate-500" />
        <input
          value={globalFilter}
          onChange={(e) => setGlobalFilter(e.target.value)}
          placeholder="Filter table…"
          className="w-full pl-8 pr-3 py-1.5 text-sm bg-surface-secondary border border-slate-700 rounded-lg text-white placeholder-slate-500 outline-none focus:border-brand-500"
        />
      </div>

      {/* Table */}
      <div className="flex-1 overflow-auto rounded-lg border border-slate-700">
        <table className="w-full text-xs text-slate-300 border-collapse">
          <thead className="bg-surface-tertiary sticky top-0 z-10">
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id}>
                {hg.headers.map((header) => (
                  <th
                    key={header.id}
                    onClick={header.column.getToggleSortingHandler()}
                    className="px-2 py-2 text-left font-semibold text-slate-300 cursor-pointer hover:text-white select-none whitespace-nowrap border-b border-slate-700"
                  >
                    <span className="flex items-center gap-1">
                      {flexRender(header.column.columnDef.header, header.getContext())}
                      {header.column.getIsSorted() === "asc" && <ChevronUp size={11} />}
                      {header.column.getIsSorted() === "desc" && <ChevronDown size={11} />}
                      {!header.column.getIsSorted() && <ChevronsUpDown size={11} className="opacity-30" />}
                    </span>
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((row, i) => (
              <tr
                key={row.id}
                className={`border-b border-slate-800 hover:bg-surface-tertiary transition-colors ${
                  i % 2 === 0 ? "" : "bg-slate-900/30"
                }`}
              >
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id} className="px-2 py-1.5 max-w-xs">
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between text-xs text-slate-400">
        <span>
          {table.getFilteredRowModel().rows.length} rows
          {globalFilter && ` (filtered from ${rawData.length})`}
        </span>
        <div className="flex gap-1">
          <button
            onClick={() => table.previousPage()}
            disabled={!table.getCanPreviousPage()}
            className="px-2 py-1 rounded bg-surface-secondary hover:bg-surface-tertiary disabled:opacity-30"
          >
            ‹
          </button>
          <span className="px-2 py-1">
            {table.getState().pagination.pageIndex + 1} / {table.getPageCount()}
          </span>
          <button
            onClick={() => table.nextPage()}
            disabled={!table.getCanNextPage()}
            className="px-2 py-1 rounded bg-surface-secondary hover:bg-surface-tertiary disabled:opacity-30"
          >
            ›
          </button>
        </div>
      </div>
    </div>
  );
}
