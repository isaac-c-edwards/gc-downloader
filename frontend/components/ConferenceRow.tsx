"use client";

import { useState, useRef, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { ChevronDown, RotateCw } from "lucide-react";
import { ApiError, fetchConference } from "@/lib/api";
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

  const { data: detail, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["conference", conference.id, language],
    queryFn: () => fetchConference(conference.id, language),
    enabled: open,
    staleTime: 1000 * 60 * 30,
    retry: (failureCount, err) =>
      // Don't retry a confirmed "no translation in this language" — retrying
      // is pointless (it will never succeed) and would just be an unneeded
      // extra request against the source (docs/11).
      !(err instanceof ApiError && err.code === "LanguageUnavailable") && failureCount < 3,
  });

  // We only learn a conference has no translation in this language the first
  // time someone expands it (see DECISIONS.md — checking every conference
  // upfront for every language would mean ~110 extra requests per language
  // change, which violates the politeness rules in docs/11). Once we know,
  // we degrade the row from an interactive dropdown into a flat, disabled
  // line — effectively "no dropdown for that one" from then on.
  const isLangUnavailable = error instanceof ApiError && error.code === "LanguageUnavailable";

  // Once detail arrives, fulfill any pending "Select all" action.
  useEffect(() => {
    if (pendingSelectAll.current && detail) {
      pendingSelectAll.current = false;
      selectAllConference(detail);
    }
    // A pending "Select all" can never resolve for a conference with no
    // translation in this language — clear the flag instead of leaving it
    // waiting forever for data that will never arrive.
    if (pendingSelectAll.current && isError) {
      pendingSelectAll.current = false;
    }
  }, [detail, isError, selectAllConference]);

  // When the language changes, reset the pending flag so stale intents don't carry over.
  useEffect(() => {
    pendingSelectAll.current = false;
  }, [language]);

  const confState = detail ? conferenceState(detail) : "none";
  // Use the localized name from detail once loaded, fall back to catalog name.
  const displayName = detail?.name ?? conference.name;

  function handleSelectAll(e: React.MouseEvent) {
    e.stopPropagation();
    if (isLangUnavailable) return; // nothing to select
    if (!detail) {
      // Open the accordion so the query fires; flag that we want to select all
      // once the data arrives (handled by the useEffect above).
      setOpen(true);
      pendingSelectAll.current = true;
      return;
    }
    if (confState === "all") {
      deselectAllConference(detail);
    } else {
      selectAllConference(detail);
    }
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

        {/* Expand toggle — once we know this conference has no translation in
            the current language, it's no longer presented as a dropdown at
            all: plain text + a small "not available" note instead. */}
        {isLangUnavailable ? (
          <div className="flex flex-1 items-center justify-between gap-2">
            <span className="text-sm font-semibold leading-snug text-zinc-400 dark:text-zinc-600">
              {displayName}
            </span>
            <span className="text-xs italic text-zinc-400 dark:text-zinc-600">
              Not available in this language
            </span>
          </div>
        ) : (
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
        )}

        {/* Select all button — hidden once we know there's nothing to select */}
        {!isLangUnavailable && (
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
        )}
      </div>

      {/* Sessions panel */}
      {open && !isLangUnavailable && (
        <div className="border-t border-zinc-100 dark:border-zinc-800">
          {isLoading && <Skeleton />}
          {isError && (
            <div className="flex items-center justify-between gap-3 px-4 py-3 text-sm text-red-500">
              <span>Failed to load sessions.</span>
              <button
                onClick={() => refetch()}
                className="flex flex-shrink-0 items-center gap-1.5 rounded-lg bg-red-100 px-3 py-1.5 text-xs font-semibold text-red-700 hover:bg-red-200 dark:bg-red-900 dark:text-red-200"
              >
                <RotateCw className="h-3 w-3" />
                Retry
              </button>
            </div>
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
