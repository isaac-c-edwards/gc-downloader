"use client";

import { useEffect, useRef, useState } from "react";
import { CheckCircle, AlertCircle, Loader2, X } from "lucide-react";
import { pollJob, downloadJobResult, type JobStatus } from "@/lib/api";

export type DownloadSummary = {
  completed: number;
  skipped: number;
};

type Props = {
  jobId: string;
  totalHint: number;
  onClose: () => void;
  /** Called with a summary when the download has finished successfully. */
  onComplete?: (summary: DownloadSummary) => void;
};

export function ProgressModal({ jobId, totalHint, onClose, onComplete }: Props) {
  const [status, setStatus] = useState<JobStatus | null>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [transferring, setTransferring] = useState(false);
  const didDownload = useRef(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    async function poll() {
      try {
        const s = await pollJob(jobId);
        setStatus(s);

        if (s.state === "done" && s.download_ready && !didDownload.current) {
          didDownload.current = true;
          clearInterval(intervalRef.current!);
          setTransferring(true);
          try {
            await downloadJobResult(jobId);
            onComplete?.({ completed: s.completed, skipped: s.skipped.length });
          } catch (err) {
            setDownloadError(err instanceof Error ? err.message : "Download failed.");
          } finally {
            setTransferring(false);
          }
        }

        if (s.state === "error" || s.state === "done") {
          clearInterval(intervalRef.current!);
        }
      } catch {
        // swallow poll errors — will retry next tick
      }
    }

    poll();
    intervalRef.current = setInterval(poll, 1500);
    return () => clearInterval(intervalRef.current!);
  }, [jobId, onComplete]);

  const total = status?.total ?? totalHint;
  const completed = status?.completed ?? 0;
  const pct = total > 0 ? Math.round((completed / total) * 100) : 0;
  const isDone = status?.state === "done";
  const isError = status?.state === "error";
  const skipped = status?.skipped ?? [];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl dark:bg-zinc-900">
        {/* Header */}
        <div className="mb-4 flex items-start justify-between gap-4">
          <div>
          <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">
            {isError
              ? "Download failed"
              : transferring
                ? "Saving to your device…"
                : isDone
                  ? "File saved!"
                  : "Preparing your download…"}
          </h2>
          <p className="mt-0.5 text-xs text-zinc-400">
            {isError
              ? status?.error_msg ?? "An unexpected error occurred."
              : transferring
                ? "Transferring the file to your browser — almost there"
                : isDone
                  ? `${completed} talk${completed !== 1 ? "s" : ""} ready${skipped.length ? `, ${skipped.length} skipped` : ""}`
                  : `Processing ${completed} of ${total} talks`}
          </p>
          </div>
          {(isDone || isError) && !transferring && (
            <button
              onClick={onClose}
              className="rounded-lg p-1 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-700 dark:hover:bg-zinc-800"
              aria-label="Close"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>

        {/* Progress bar */}
        {!isError && (
          <div className="mb-4">
            <div className="mb-1.5 flex justify-between text-xs text-zinc-500">
              <span>{completed} / {total}</span>
              <span>{pct}%</span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-zinc-100 dark:bg-zinc-800">
              <div
                className={`h-full rounded-full transition-all duration-500 ${
                  isDone ? "bg-green-500" : "bg-blue-500"
                }`}
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
        )}

        {/* Status icon */}
        <div className="flex justify-center py-2">
          {isError ? (
            <AlertCircle className="h-10 w-10 text-red-400" />
          ) : isDone && !transferring ? (
            <CheckCircle className="h-10 w-10 text-green-500" />
          ) : (
            <Loader2 className={`h-10 w-10 animate-spin ${transferring ? "text-green-400" : "text-blue-500"}`} />
          )}
        </div>

        {/* Skipped talks */}
        {skipped.length > 0 && (
          <div className="mt-4 rounded-xl border border-amber-100 bg-amber-50 p-3 dark:border-amber-900 dark:bg-amber-950">
            <p className="mb-1.5 text-xs font-semibold text-amber-800 dark:text-amber-300">
              {skipped.length} talk{skipped.length !== 1 ? "s" : ""} skipped
            </p>
            <ul className="space-y-1">
              {skipped.map((s) => (
                <li key={s.talk_id} className="text-xs text-amber-700 dark:text-amber-400">
                  <span className="font-mono">{s.talk_id}</span>
                  {s.reason ? ` — ${s.reason}` : ""}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Download error (after job succeeded but file download failed) */}
        {downloadError && (
          <div className="mt-3 flex items-start gap-2 rounded-xl border border-red-100 bg-red-50 p-3 text-xs text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
            <AlertCircle className="mt-0.5 h-3.5 w-3.5 flex-shrink-0" />
            {downloadError}
          </div>
        )}

        {/* Done: close button */}
        {(isDone || isError) && !transferring && (
          <button
            onClick={onClose}
            className="mt-4 w-full rounded-xl bg-zinc-100 py-2.5 text-sm font-semibold text-zinc-700 hover:bg-zinc-200 dark:bg-zinc-800 dark:text-zinc-200 dark:hover:bg-zinc-700"
          >
            Close
          </button>
        )}
      </div>
    </div>
  );
}
