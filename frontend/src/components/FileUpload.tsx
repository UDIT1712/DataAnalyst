import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, File, CheckCircle, AlertCircle, Loader2 } from "lucide-react";
import axios from "axios";
import type { UploadedFile } from "@/types";

interface Props {
  onUploaded: (file: UploadedFile) => void;
  onUseFile: (filename: string) => void;
}

export function FileUpload({ onUploaded, onUseFile }: Props) {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploaded, setUploaded] = useState<UploadedFile[]>([]);

  const onDrop = useCallback(
    async (accepted: File[]) => {
      for (const file of accepted) {
        setUploading(true);
        setError(null);
        const form = new FormData();
        form.append("file", file);
        try {
          const res = await axios.post<UploadedFile>("/api/upload", form);
          setUploaded((prev) => [...prev, res.data]);
          onUploaded(res.data);
        } catch (err: unknown) {
          const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Upload failed";
          setError(msg);
        } finally {
          setUploading(false);
        }
      }
    },
    [onUploaded]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "text/csv": [".csv"],
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
      "application/vnd.ms-excel": [".xls"],
      "application/json": [".json"],
      "application/octet-stream": [".parquet"],
    },
    maxFiles: 5,
    disabled: uploading,
  });

  return (
    <div className="space-y-3">
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-xl p-4 text-center cursor-pointer transition-colors ${
          isDragActive
            ? "border-brand-500 bg-brand-900/20"
            : "border-slate-700 hover:border-slate-500"
        } ${uploading ? "opacity-50 cursor-not-allowed" : ""}`}
      >
        <input {...getInputProps()} />
        <div className="flex flex-col items-center gap-2">
          {uploading ? (
            <Loader2 size={24} className="text-brand-400 animate-spin" />
          ) : (
            <Upload size={24} className="text-slate-500" />
          )}
          <p className="text-xs text-slate-400">
            {uploading
              ? "Uploading…"
              : isDragActive
              ? "Drop here"
              : "CSV, Excel, JSON, Parquet"}
          </p>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 text-xs text-red-400 bg-red-900/20 rounded-lg px-3 py-2">
          <AlertCircle size={13} />
          {error}
        </div>
      )}

      {uploaded.map((f) => (
        <div
          key={f.name}
          className="flex items-center gap-2 bg-surface-secondary rounded-lg px-3 py-2"
        >
          <CheckCircle size={13} className="text-green-400 shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-xs text-white truncate">{f.original_name || f.name}</p>
            <p className="text-xs text-slate-500">{f.size_kb} KB</p>
          </div>
          <button
            onClick={() => onUseFile(f.name)}
            className="text-xs text-brand-400 hover:text-brand-300 shrink-0"
          >
            Load
          </button>
        </div>
      ))}
    </div>
  );
}
