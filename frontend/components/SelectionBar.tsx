"use client";

import { useState } from "react";
import { Download, Loader2, AlertCircle } from "lucide-react";
import { useSelectionStore } from "@/lib/store";
import { triggerDownload, createJob } from "@/lib/api";
import { getCachedConferenceDetails } from "@/lib/conferenceCache";
import { useQueryClient } from "@tanstack/react-query";

type Props = {
  onJobStart?: (jobId: string, total: number) => void;
};

const DELIVERY_MODE = process.env.NEXT_PUBLIC_DELIVERY_MODE ?? "job";

export function SelectionBar({ onJobStart }: Props) {
  const { selectedTalkIds, language, buildSelection } = useSelectionStore();
  const count = selectedTalkIds.size;
  const empty = count === 0;
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const queryClient = useQueryClient();

  async function handleDownload() {
    setError(null);
    setLoading(true);
    try {
      const allDetails = getCachedConferenceDetails(queryClient, language);
      const selection = buildSelection(allDetails);
      if (!selection.length) {
        setError("Expand and select conferences first.");
        return;
      }

      if (DELIVERY_MODE === "job") {
        const { job_id, total } = await createJob(language, selection);
        onJobStart?.(job_id, total);
      } else {
        await triggerDownload(language, selection);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Download failed.");
    } finally {
      setLoading(false);
    }
  }

  const downloadLabel = loading
    ? "Preparing…"
    : count === 1
      ? "Download MP3"
      : "Download ZIP";
  const downloadHint = loading
    ? "Preparing download…"
    : count === 1
      ? "Ready as a tagged MP3"
      : `${count} talks packaged as MP3s in a ZIP`;
  const ariaLabel =
    count === 1
      ? "Download selected talk as MP3"
      : `Download ${count} selected talks as ZIP`;

  return (
    <div className="sticky bottom-0 z-10 border-t border-zinc-200 bg-white/95 backdrop-blur-sm dark:border-zinc-800 dark:bg-zinc-950/95">
      {error && (
        <div className="flex items-center gap-2 border-b border-red-100 bg-red-50 px-4 py-2 text-xs text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
          <AlertCircle className="h-3.5 w-3.5 flex-shrink-0" />
          {error}
        </div>
      )}
      <div className="mx-auto flex max-w-4xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
        {empty ? (
          <p className="text-sm text-zinc-400 dark:text-zinc-500" aria-live="polite">
            Expand a conference to select sessions or talks.
          </p>
        ) : (
          <div aria-live="polite" aria-atomic="true">
            <p className="text-sm font-semibold text-zinc-800 dark:text-zinc-200">
              {count} {count === 1 ? "talk" : "talks"} selected
            </p>
            <p className="text-xs text-zinc-400">
              {downloadHint}
            </p>
          </div>
        )}

        <button
          disabled={empty || loading}
          onClick={handleDownload}
          className={`flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-semibold shadow-sm transition-all ${
            empty || loading
              ? "cursor-not-allowed bg-zinc-100 text-zinc-300 dark:bg-zinc-800 dark:text-zinc-600"
              : "bg-blue-600 text-white hover:bg-blue-700 active:scale-95"
          }`}
          aria-label={ariaLabel}
        >
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Download className="h-4 w-4" />
          )}
          {downloadLabel}
        </button>
      </div>
    </div>
  );
}
