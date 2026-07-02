"use client";

import { useCallback, useState } from "react";
import { ConferenceList } from "@/components/ConferenceList";
import { SelectionBar } from "@/components/SelectionBar";
import { ProgressModal, type DownloadSummary } from "@/components/ProgressModal";
import { SummaryToast } from "@/components/SummaryToast";
import { useSelectionStore } from "@/lib/store";

type ActiveJob = { jobId: string; total: number };
type ToastInfo = DownloadSummary & { languageName: string };

export default function Home() {
  const [activeJob, setActiveJob] = useState<ActiveJob | null>(null);
  const [toast, setToast] = useState<ToastInfo | null>(null);
  const language = useSelectionStore((s) => s.language);

  // Resolve human-readable language name from store (fetched via LanguageSelect)
  // We keep a local map for the toast; the full list comes from the API but we
  // store only the selected code, so we resolve the label from the DOM selector.
  function getLanguageName(code: string): string {
    const map: Record<string, string> = {
      eng: "English", spa: "Español", por: "Português", fra: "Français",
      deu: "Deutsch", ita: "Italiano", jpn: "日本語", kor: "한국어",
      zho: "中文", rus: "Русский", tgl: "Tagalog", smo: "Gagana Samoa",
      ton: "Lea Faka-Tonga",
    };
    return map[code] ?? code;
  }

  const handleComplete = useCallback(
    (summary: DownloadSummary) => {
      setToast({ ...summary, languageName: getLanguageName(language) });
    },
    [language],
  );

  return (
    <>
      <main className="mx-auto w-full max-w-4xl flex-1 px-4 py-6 sm:px-6">
        <div className="mb-6">
          <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">
            Choose your sessions
          </h2>
          <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
            Expand a conference, pick sessions or individual talks, then hit{" "}
            <span className="font-medium text-zinc-600 dark:text-zinc-300">
              Download
            </span>
            .
          </p>
        </div>
        <ConferenceList />
      </main>

      <SelectionBar
        onJobStart={(jobId, total) => setActiveJob({ jobId, total })}
      />

      {activeJob && (
        <ProgressModal
          jobId={activeJob.jobId}
          totalHint={activeJob.total}
          onClose={() => setActiveJob(null)}
          onComplete={handleComplete}
        />
      )}

      {toast && (
        <SummaryToast
          completed={toast.completed}
          skipped={toast.skipped}
          languageName={toast.languageName}
          onDismiss={() => setToast(null)}
        />
      )}
    </>
  );
}
