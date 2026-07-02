"use client";

import { useEffect } from "react";
import { CheckCircle, X } from "lucide-react";

type Props = {
  completed: number;
  skipped: number;
  languageName: string;
  onDismiss: () => void;
};

export function SummaryToast({ completed, skipped, languageName, onDismiss }: Props) {
  useEffect(() => {
    const timer = setTimeout(onDismiss, 6000);
    return () => clearTimeout(timer);
  }, [onDismiss]);

  const skipNote =
    skipped > 0
      ? ` (${skipped} skipped — not available in ${languageName})`
      : "";
  const message = `Downloaded ${completed} talk${completed !== 1 ? "s" : ""}${skipNote}.`;

  return (
    <div
      role="status"
      aria-live="polite"
      className="fixed bottom-20 left-1/2 z-50 flex w-max max-w-sm -translate-x-1/2 items-start gap-3 rounded-2xl border border-green-200 bg-white px-4 py-3 shadow-xl dark:border-green-800 dark:bg-zinc-900"
    >
      <CheckCircle className="mt-0.5 h-5 w-5 flex-shrink-0 text-green-500" />
      <p className="text-sm font-medium text-zinc-800 dark:text-zinc-200">{message}</p>
      <button
        onClick={onDismiss}
        className="ml-1 rounded-lg p-1 text-zinc-400 hover:text-zinc-600 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:hover:text-zinc-200"
        aria-label="Dismiss notification"
      >
        <X className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}
