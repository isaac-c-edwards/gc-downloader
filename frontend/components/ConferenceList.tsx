"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchCatalog } from "@/lib/api";
import { useSelectionStore } from "@/lib/store";
import { ConferenceRow } from "./ConferenceRow";

function SkeletonList() {
  return (
    <div className="space-y-3">
      {[1, 2, 3, 4, 5].map((i) => (
        <div
          key={i}
          className="h-[62px] animate-pulse rounded-2xl border border-zinc-100 bg-white dark:border-zinc-800 dark:bg-zinc-900"
          style={{ animationDelay: `${i * 60}ms` }}
        />
      ))}
    </div>
  );
}

export function ConferenceList() {
  const language = useSelectionStore((s) => s.language);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["catalog", language],
    queryFn: () => fetchCatalog(language),
    staleTime: 1000 * 60 * 30,
  });

  if (isLoading) return <SkeletonList />;

  if (isError) {
    return (
      <div className="rounded-2xl border border-red-200 bg-red-50 px-5 py-8 text-center dark:border-red-900 dark:bg-red-950/30">
        <p className="text-sm font-medium text-red-700 dark:text-red-300">
          Could not load conferences.
        </p>
        <p className="mt-1 text-xs text-red-500">Make sure the backend is running.</p>
        <button
          onClick={() => refetch()}
          className="mt-4 rounded-lg bg-red-100 px-4 py-2 text-xs font-semibold text-red-700 hover:bg-red-200 dark:bg-red-900 dark:text-red-200"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!data?.conferences.length) {
    return (
      <p className="text-center text-sm text-zinc-500">No conferences found.</p>
    );
  }

  return (
    <div className="space-y-3">
      {data.conferences.map((conference) => (
        <ConferenceRow key={conference.id} conference={conference} />
      ))}
    </div>
  );
}
