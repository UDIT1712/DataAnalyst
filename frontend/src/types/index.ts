export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: number;
  toolCalls?: ToolCall[];
}

export interface ToolCall {
  id: string;
  name: string;
  status: "running" | "done" | "error";
  args?: string;
  result?: string;
}

export interface ChartData {
  data: Plotly.Data[];
  layout: Partial<Plotly.Layout>;
  frames?: Plotly.Frame[];
  id: string;
  timestamp: number;
  title?: string;
}

export interface DatasetInfo {
  name: string;
  columns: string[];
  shape: [number, number];
  dtypes: Record<string, string>;
}

export interface UploadedFile {
  name: string;
  size_kb: number;
  original_name?: string;
}

export interface Session {
  thread_id: string;
  message_count: number;
  dataframes: string[];
  chart_count: number;
  last_active: number;
}

export interface ReportInfo {
  filename: string;
  download_url: string;
  status: string;
}

export type AGUIEventType =
  | "RUN_STARTED"
  | "RUN_FINISHED"
  | "RUN_ERROR"
  | "STEP_STARTED"
  | "STEP_FINISHED"
  | "TEXT_MESSAGE_START"
  | "TEXT_MESSAGE_CONTENT"
  | "TEXT_MESSAGE_END"
  | "TOOL_CALL_START"
  | "TOOL_CALL_ARGS"
  | "TOOL_CALL_END"
  | "STATE_SNAPSHOT"
  | "STATE_DELTA"
  | "CUSTOM";

export interface AGUIEventPayload {
  type: AGUIEventType;
  timestamp: number;
  [key: string]: unknown;
}
