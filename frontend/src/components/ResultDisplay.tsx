import { motion } from "framer-motion";
import { CheckCircle2, BarChart3, Brain, Tag, Percent } from "lucide-react";

interface AnalysisResult {
  analysis: string;
  model_signals: string;
  final_label: string;
  confidence: number;
}

interface ResultDisplayProps {
  result: AnalysisResult;
}

export default function ResultDisplay({ result }: ResultDisplayProps) {
  const confidencePct = Math.round(result.confidence * 100);

  const getConfidenceColor = (pct: number) => {
    if (pct >= 80) return "text-accent";
    if (pct >= 50) return "text-primary";
    return "text-destructive";
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="space-y-4"
    >
      <div className="flex items-center gap-2">
        <CheckCircle2 className="h-5 w-5 text-accent" />
        <h3 className="text-lg font-semibold font-display text-foreground">Analysis Complete</h3>
      </div>

      {/* Top stats row */}
      <div className="grid grid-cols-2 gap-3">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.1 }}
          className="rounded-lg border border-border bg-card p-4"
        >
          <div className="flex items-center gap-2 mb-2">
            <Tag className="h-4 w-4 text-primary" />
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Label</span>
          </div>
          <p className="text-lg font-semibold font-display text-foreground">{result.final_label || "—"}</p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.15 }}
          className="rounded-lg border border-border bg-card p-4"
        >
          <div className="flex items-center gap-2 mb-2">
            <Percent className="h-4 w-4 text-primary" />
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Confidence</span>
          </div>
          <p className={`text-2xl font-bold font-display ${getConfidenceColor(confidencePct)}`}>
            {confidencePct}%
          </p>
        </motion.div>
      </div>

      {/* Analysis */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="rounded-lg border border-border bg-card p-4"
      >
        <div className="flex items-center gap-2 mb-3">
          <Brain className="h-4 w-4 text-primary" />
          <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Analysis</span>
        </div>
        <p className="text-sm leading-relaxed text-foreground whitespace-pre-wrap">{result.analysis || "—"}</p>
      </motion.div>

      {/* Model Signals */}
      {result.model_signals && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25 }}
          className="rounded-lg border border-border bg-card p-4"
        >
          <div className="flex items-center gap-2 mb-3">
            <BarChart3 className="h-4 w-4 text-primary" />
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Model Signals</span>
          </div>
          <p className="text-sm leading-relaxed text-foreground whitespace-pre-wrap">{result.model_signals}</p>
        </motion.div>
      )}
    </motion.div>
  );
}
