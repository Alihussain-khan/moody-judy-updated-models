import { useState, useRef, useCallback } from "react";
import { motion } from "framer-motion";
import { Key, Sparkles, Send, RotateCcw, Eye, EyeOff } from "lucide-react";
import AudioDropzone from "@/components/AudioDropzone";
import ProgressTracker, { type ProgressEvent } from "@/components/ProgressTracker";
import ResultDisplay from "@/components/ResultDisplay";

const CLAUDE_MODELS = [
  { value: "claude-opus-4-6", label: "Claude Opus 4.6 | Most Intelligent" },
  { value: "claude-sonnet-4-6", label: "Claude Sonnet 4.6 | Balanced" },
  { value: "claude-opus-4-20250514", label: "Claude Opus 4 (May 2025)" },
  { value: "claude-sonnet-4-20250514", label: "Claude Sonnet 4 (May 2025)" },
  { value: "claude-haiku-4-5-20251001", label: "Claude Haiku 4.5 | Fast & Cheap" },
];

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

interface AnalysisResult {
  analysis: string;
  model_signals: string;
  final_label: string;
  confidence: number;
}

type AppState = "idle" | "uploading" | "processing" | "done" | "error";

export default function Index() {
  const [apiKey, setApiKey] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [model, setModel] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [state, setState] = useState<AppState>("idle");
  const [events, setEvents] = useState<ProgressEvent[]>([]);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [errorMsg, setErrorMsg] = useState("");
  const eventSourceRef = useRef<EventSource | null>(null);

  const reset = () => {
    setState("idle");
    setEvents([]);
    setResult(null);
    setErrorMsg("");
    eventSourceRef.current?.close();
  };

  const fetchResult = useCallback(async (resultUrl: string) => {
    try {
      const res = await fetch(`${API_BASE}${resultUrl}`);
      if (!res.ok) throw new Error("Failed to fetch result");
      const data = await res.json();
      const finalData = data.final || data;
      setResult(finalData);
      setState("done");
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to fetch result");
      setState("error");
    }
  }, []);

  const listenEvents = useCallback((eventsPath: string, resultPath: string) => {
    const es = new EventSource(`${API_BASE}${eventsPath}`);
    eventSourceRef.current = es;
    let eventCounter = 0;

    es.onmessage = (e) => {
      let parsed: any;
      try {
        parsed = JSON.parse(e.data);
      } catch {
        parsed = { message: e.data };
      }

      const msg = parsed.message || parsed.status || e.data;
      const isDone = parsed.stage === "final";

      eventCounter++;
      const id = `evt-${eventCounter}`;

      setEvents((prev) => {
        const updated = prev.map((ev) =>
          ev.status === "active" ? { ...ev, status: "done" as const } : ev
        );
        return [...updated, { id, message: msg, status: isDone ? "done" : "active" }];
      });

      if (isDone) {
        es.close();
        fetchResult(resultPath);
      }
    };

    es.onerror = () => {
      es.close();
      setEvents((prev) => prev.map((ev) =>
        ev.status === "active" ? { ...ev, status: "done" as const } : ev
      ));
      fetchResult(resultPath);
    };
  }, [fetchResult]);

  const handleSubmit = async () => {
    if (!apiKey.trim() || !file) return;

    reset();
    setState("uploading");

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("claude_api_key", apiKey.trim());
      if (model) formData.append("claude_model", model);

      const res = await fetch(`${API_BASE}/v1/jobs/run-all`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const errBody = await res.text();
        throw new Error(errBody || `HTTP ${res.status}`);
      }

      const data = await res.json();
      const jobId = data.job_id;
      const eventsUrl = data.events_url;
      const resultUrl = data.result_url;

      if (!jobId) throw new Error("No job ID returned");

      setState("processing");
      listenEvents(eventsUrl || `/v1/jobs/${jobId}/events`, resultUrl || `/v1/jobs/${jobId}/result`);
    } catch (err: any) {
      setErrorMsg(err.message || "Upload failed");
      setState("error");
    }
  };

  const canSubmit = apiKey.trim().length > 0 && file !== null && state === "idle";
  const isWorking = state === "uploading" || state === "processing";

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-xl px-4 py-12">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -12 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-10"
        >
          <div className="inline-flex items-center gap-2 rounded-full bg-primary/10 px-4 py-1.5 mb-4">
            <Sparkles className="h-4 w-4 text-primary" />
            <span className="text-xs font-semibold text-primary uppercase tracking-wider">Moody Judy Prototype</span>
          </div>
          <h1 className="text-3xl font-bold font-display text-foreground">
            Analyze Your Audio
          </h1>
          <p className="mt-2 text-muted-foreground text-sm">
            Upload an audio file and let AI analyze it for you.
          </p>
        </motion.div>

        {/* Main Card */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="rounded-xl border border-border bg-card p-6 shadow-sm space-y-5"
        >
          {/* API Key */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-foreground">Claude API Key *</label>
            <div className="relative">
              <Key className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <input
                type={showKey ? "text" : "password"}
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                disabled={isWorking}
                placeholder="sk-ant-..."
                className="w-full rounded-lg border border-input bg-background pl-10 pr-10 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
              />
              <button
                type="button"
                onClick={() => setShowKey(!showKey)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
              >
                {showKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>

          {/* Model Select */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-foreground">
              Model <span className="text-muted-foreground font-normal">(optional)</span>
            </label>
            <select
              value={model}
              onChange={(e) => setModel(e.target.value)}
              disabled={isWorking}
              className="w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
            >
              <option value="">Default</option>
              {CLAUDE_MODELS.map((m) => (
                <option key={m.value} value={m.value}>{m.label}</option>
              ))}
            </select>
          </div>

          {/* File Upload */}
          <AudioDropzone file={file} onFileSelect={setFile} disabled={isWorking} />

          {/* Submit / Reset */}
          <div className="flex gap-3">
            {state === "done" || state === "error" ? (
              <button
                onClick={() => { reset(); setFile(null); }}
                className="flex-1 flex items-center justify-center gap-2 rounded-lg bg-secondary px-4 py-2.5 text-sm font-semibold text-secondary-foreground hover:bg-secondary/80 transition-colors"
              >
                <RotateCcw className="h-4 w-4" />
                Start Over
              </button>
            ) : (
              <button
                onClick={handleSubmit}
                disabled={!canSubmit}
                className="flex-1 flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {isWorking ? (
                  <>
                    <div className="h-4 w-4 rounded-full border-2 border-primary-foreground/30 border-t-primary-foreground animate-spin" />
                    {state === "uploading" ? "Uploading…" : "Processing…"}
                  </>
                ) : (
                  <>
                    <Send className="h-4 w-4" />
                    Analyze
                  </>
                )}
              </button>
            )}
          </div>

          {/* Error */}
          {state === "error" && errorMsg && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="rounded-lg bg-destructive/10 border border-destructive/20 px-4 py-3"
            >
              <p className="text-sm text-destructive">{errorMsg}</p>
            </motion.div>
          )}

          {/* Progress Events */}
          <ProgressTracker events={events} />

          {/* Result */}
          {result && <ResultDisplay result={result} />}
        </motion.div>

        <p className="text-center text-xs text-muted-foreground mt-6">
          Your API key is sent directly to the backend and never stored.
        </p>
      </div>
    </div>
  );
}
