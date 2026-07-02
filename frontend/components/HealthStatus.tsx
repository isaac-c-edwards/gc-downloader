"use client";

import { useEffect, useState } from "react";

import { fetchHealth, getApiBaseUrl } from "@/lib/api";

type Status = "loading" | "ok" | "error";

export function HealthStatus() {
  const [status, setStatus] = useState<Status>("loading");
  const [message, setMessage] = useState("Checking backend…");

  useEffect(() => {
    let cancelled = false;

    async function checkHealth() {
      try {
        const result = await fetchHealth();
        if (cancelled) return;
        setStatus("ok");
        setMessage(`Backend connected (${result.status})`);
      } catch (error) {
        if (cancelled) return;
        setStatus("error");
        setMessage(
          error instanceof Error
            ? error.message
            : "Unable to reach the backend",
        );
      }
    }

    void checkHealth();

    return () => {
      cancelled = true;
    };
  }, []);

  const statusStyles = {
    loading: "border-zinc-200 bg-zinc-50 text-zinc-700 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-300",
    ok: "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950 dark:text-emerald-200",
    error: "border-red-200 bg-red-50 text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-200",
  } as const;

  return (
    <div className="space-y-3">
      <div
        className={`rounded-xl border px-4 py-3 text-sm ${statusStyles[status]}`}
        role="status"
      >
        {message}
      </div>
      <p className="text-sm text-zinc-500 dark:text-zinc-400">
        API base URL: <code className="text-zinc-700 dark:text-zinc-300">{getApiBaseUrl()}</code>
      </p>
    </div>
  );
}
