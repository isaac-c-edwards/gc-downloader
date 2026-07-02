"use client";

import { useState, useRef, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { ChevronDown } from "lucide-react";
import { fetchConference } from "@/lib/api";
import { useSelectionStore } from "@/lib/store";
import { SessionRow } from "./SessionRow";
import type { Conference } from "@/lib/api";

function Skeleton() {
  return (
    <div className="space-y-2 px-4 py-4">
      {[1, 2, 3].map((i) => (
        <div
          key={i}
          className="h-9 animate-pulse rounded-lg bg-zinc-100 dark:bg-zinc-800"
          style={{ animationDelay: `${i * 80}ms` }}
        />
      ))}
    </div>
  );
}

const MONTH_LABELS: Record<number, string> = { 4: "APR", 10: "OCT" };

export function ConferenceRow({ conference }: { conference: Conference }) {
  const [open, setOpen] = useState(false);
  const language = useSelectionStore((s) => s.language);
  const { selectAllConference, deselectAllConference, conferenceState } =
    useSelectionStore();

  // Tracks a "Select all" click that arrived before the detail was loaded.
  const pendingSelectAll = useRef(false);

  const { data: detail, isLoading, isError } = useQuery({
    queryKey: ["conference", conference.id, language],
    queryFn: () => fetchConference(conference.id, language),
    enabled: open,
    staleTime: 1000 * 60 * 30,
  });

  // Once detail arrives, fulfill any pending "Select all" action.
  useEffect(() => {
    if (pendingSelectAll.current && detail) {
      pendingSelectAll.current = false;
      selectAllConference(detail);
    }
  }, [detail, selectAllConference]);

  // When the language changes, reset the pending flag so stale intents don't carry over.
  useEffect(() => {
    pendingSelectAll.current = false;
  }, [language]);

  const confState = detail ? conferenceState(detail) : "none";
  // Use the localized name from detail once loaded, fall back to catalog name.
  const displayName = detail?.name ?? conference.name;

  function handleSelectAll(e: React.MouseEvent) {
    e.stopPropagation();
    if (!detail) {
      // Open the accordion so the query fires; flag that we want to select all
      // once the data arrives (handled by the useEffect above).
      setOpen(true);
      pendingSelectAll.current = true;
      return;
    }
    confState === "all" ? deselectAllConference(detail) : selectAllConference(detail);
  }

  return (
    <div
      className={`overflow-hidden rounded-2xl border transition-shadow ${
        open
          ? "border-blue-200 shadow-md dark:border-blue-900"
          : "border-zinc-200 shadow-sm hover:border-zinc-300 dark:border-zinc-800 dark:hover:border-zinc-700"
      } bg-white dark:bg-zinc-900`}
    >
      {/* Header row */}
      <div className="flex items-center gap-3 px-4 py-3.5">
        {/* Year + month badge */}
        <div className="flex w-12 flex-shrink-0 flex-col items-center rounded-lg bg-zinc-50 py-1.5 dark:bg-zinc-800">
          <span className="text-[10px] font-bold tracking-widest text-blue-500">
            {MONTH_LABELS[conference.month] ?? conference.month}
          </span>
          <span className="text-sm font-bold tabular-nums text-zinc-700 dark:text-zinc-200">
            {conference.year}
          </span>
        </div>

        {/* Expand toggle */}
        <button
          onClick={() => setOpen((o) => !o)}
          className="flex flex-1 items-center justify-between gap-2 text-left"
          aria-expanded={open}
          aria-label={`${open ? "Collapse" : "Expand"} ${displayName}`}
        >
          <span className="text-sm font-semibold leading-snug text-zinc-900 dark:text-zinc-50">
            {displayName}
          </span>
          <ChevronDown
            className={`h-4 w-4 flex-shrink-0 text-zinc-400 transition-transform duration-200 ${open ? "rotate-180" : ""}`}
          />
        </button>

        {/* Select all button */}
        <button
          onClick={handleSelectAll}
          className={`flex-shrink-0 rounded-lg px-3 py-1.5 text-xs font-semibold transition-all ${
            confState === "all"
              ? "bg-blue-500 text-white shadow-sm hover:bg-blue-600"
              : confState === "partial"
                ? "bg-amber-100 text-amber-700 hover:bg-amber-200 dark:bg-amber-900/40 dark:text-amber-300"
                : "bg-zinc-100 text-zinc-500 hover:bg-zinc-200 dark:bg-zinc-800 dark:text-zinc-400 dark:hover:bg-zinc-700"
          }`}
          aria-label={`${confState === "all" ? "Deselect all" : "Select all"} talks in ${displayName}`}
        >
          {confState === "all" ? "Deselect all" : "Select all"}
        </button>
      </div>

      {/* Sessions panel */}
      {open && (
        <div className="border-t border-zinc-100 dark:border-zinc-800">
          {isLoading && <Skeleton />}
          {isError && (
            <p className="px-4 py-3 text-sm text-red-500">
              Failed to load sessions. Try again.
            </p>
          )}
          {detail && (
            <div>
              {detail.sessions.map((session) => (
                <SessionRow key={session.id} session={session} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
