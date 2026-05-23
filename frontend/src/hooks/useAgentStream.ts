import { useCallback, useRef, useState } from "react";
import { v4 as uuidv4 } from "uuid";
import type {
  AGUIEventPayload,
  ChartData,
  ChatMessage,
  ReportInfo,
  ToolCall,
} from "@/types";

const API_BASE = "/api";

export function useAgentStream(threadId: string) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [charts, setCharts] = useState<ChartData[]>([]);
  const [datasets, setDatasets] = useState<string[]>([]);
  const [reports, setReports] = useState<ReportInfo[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [activeTools, setActiveTools] = useState<ToolCall[]>([]);
  const abortRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(
    async (userText: string) => {
      if (isStreaming) return;

      const userMsg: ChatMessage = {
        id: uuidv4(),
        role: "user",
        content: userText,
        timestamp: Date.now(),
      };
      setMessages((prev) => [...prev, userMsg]);
      setIsStreaming(true);

      const runId = uuidv4();
      const assistantId = uuidv4();
      let assistantText = "";
      const currentToolCalls: Record<string, ToolCall> = {};

      // Placeholder assistant message
      const assistantMsg: ChatMessage = {
        id: assistantId,
        role: "assistant",
        content: "",
        timestamp: Date.now(),
        toolCalls: [],
      };
      setMessages((prev) => [...prev, assistantMsg]);

      abortRef.current = new AbortController();

      try {
        const res = await fetch(`${API_BASE}/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            thread_id: threadId,
            run_id: runId,
            messages: [{ role: "user", content: userText }],
          }),
          signal: abortRef.current.signal,
        });

        if (!res.ok || !res.body) {
          throw new Error(`HTTP ${res.status}`);
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });

          const lines = buffer.split("\n");
          buffer = lines.pop() ?? "";

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            const raw = line.slice(6).trim();
            if (!raw || raw === "[DONE]") continue;

            try {
              const evt = JSON.parse(raw) as AGUIEventPayload;
              handleEvent(evt);
            } catch {
              // malformed line — skip
            }
          }
        }
      } catch (err: unknown) {
        if ((err as Error).name !== "AbortError") {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? { ...m, content: m.content || "_Agent error — please try again._" }
                : m
            )
          );
        }
      } finally {
        setIsStreaming(false);
        setActiveTools([]);
      }

      function handleEvent(evt: AGUIEventPayload) {
        switch (evt.type) {
          case "TEXT_MESSAGE_CONTENT":
            assistantText += evt.delta as string;
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId ? { ...m, content: assistantText } : m
              )
            );
            break;

          case "TOOL_CALL_START": {
            const tc: ToolCall = {
              id: evt.toolCallId as string,
              name: evt.toolCallName as string,
              status: "running",
            };
            currentToolCalls[tc.id] = tc;
            setActiveTools(Object.values(currentToolCalls));
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? { ...m, toolCalls: Object.values(currentToolCalls) }
                  : m
              )
            );
            break;
          }

          case "TOOL_CALL_ARGS": {
            const tc = currentToolCalls[evt.toolCallId as string];
            if (tc) {
              tc.args = (tc.args ?? "") + (evt.delta as string);
            }
            break;
          }

          case "TOOL_CALL_END": {
            const tc = currentToolCalls[evt.toolCallId as string];
            if (tc) tc.status = "done";
            setActiveTools(Object.values(currentToolCalls));
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? { ...m, toolCalls: Object.values(currentToolCalls) }
                  : m
              )
            );
            break;
          }

          case "STATE_SNAPSHOT": {
            const snap = evt.snapshot as { datasets: string[]; chart_count: number };
            if (snap?.datasets) setDatasets(snap.datasets);
            break;
          }

          case "CUSTOM": {
            const name = evt.name as string;
            if (name === "chart_generated") {
              const chartJson = evt.value as Record<string, unknown>;
              const newChart: ChartData = {
                id: uuidv4(),
                timestamp: Date.now(),
                data: (chartJson.data as Plotly.Data[]) ?? [],
                layout: (chartJson.layout as Partial<Plotly.Layout>) ?? {},
                frames: chartJson.frames as Plotly.Frame[],
                title: ((chartJson.layout as Record<string, unknown>)?.title as string) ?? "",
              };
              setCharts((prev) => [...prev, newChart]);
            } else if (name === "report_ready") {
              setReports((prev) => [...prev, evt.value as ReportInfo]);
            }
            break;
          }

          default:
            break;
        }
      }
    },
    [isStreaming, threadId]
  );

  const stopStream = useCallback(() => {
    abortRef.current?.abort();
    setIsStreaming(false);
  }, []);

  const clearChat = useCallback(() => {
    setMessages([]);
    setCharts([]);
    setDatasets([]);
    setReports([]);
  }, []);

  return {
    messages,
    charts,
    datasets,
    reports,
    isStreaming,
    activeTools,
    sendMessage,
    stopStream,
    clearChat,
  };
}
