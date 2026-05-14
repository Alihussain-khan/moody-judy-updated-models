import { motion } from "framer-motion";
import { Loader2, CheckCircle2, AlertCircle } from "lucide-react";

export interface ProgressEvent {
  id: string;
  message: string;
  status: "pending" | "active" | "done" | "error";
}

interface ProgressTrackerProps {
  events: ProgressEvent[];
}

export default function ProgressTracker({ events }: ProgressTrackerProps) {
  if (events.length === 0) return null;

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-semibold font-display text-foreground">Pipeline Progress</h3>
      <div className="space-y-1">
        {events.map((evt, i) => (
          <motion.div
            key={evt.id}
            initial={{ opacity: 0, x: -12 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.05 }}
            className="flex items-center gap-3 rounded-md px-3 py-2 text-sm bg-card"
          >
            {evt.status === "active" && (
              <Loader2 className="h-4 w-4 text-primary animate-spin shrink-0" />
            )}
            {evt.status === "done" && (
              <CheckCircle2 className="h-4 w-4 text-accent shrink-0" />
            )}
            {evt.status === "error" && (
              <AlertCircle className="h-4 w-4 text-destructive shrink-0" />
            )}
            {evt.status === "pending" && (
              <div className="h-4 w-4 rounded-full border-2 border-muted shrink-0" />
            )}
            <span className={evt.status === "done" ? "text-muted-foreground" : "text-foreground"}>
              {evt.message}
            </span>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
