"use client";

import { useRef, useEffect, useState } from "react";
import { ChevronDown } from "lucide-react";
import { useSelectionStore } from "@/lib/store";
import { TalkRow } from "./TalkRow";
import type { Session } from "@/lib/api";

export function SessionRow({ session }: { session: Session }) {
  const { sessionState, toggleSession } = useSelectionStore();
  const state = sessionState(session);
  const [open, setOpen] = useState(false);
  const checkboxRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (checkboxRef.current) {
      checkboxRef.current.indeterminate = state === "partial";
    }
  }, [state]);

  return (
    <div className="border-b border-zinc-100 last:border-0 dark:border-zinc-800">
      <div className="flex items-center gap-3 px-4 py-3">
        <input
          ref={checkboxRef}
          type="checkbox"
          checked={state === "all"}
          onChange={() => toggleSession(session)}
          className="h-4 w-4 flex-shrink-0 accent-blue-500"
          aria-label={`Select all talks in ${session.name}`}
        />
        <button
          onClick={() => setOpen((o) => !o)}
          className="flex flex-1 items-center justify-between gap-2 text-left"
          aria-expanded={open}
          aria-label={`${open ? "Collapse" : "Expand"} ${session.name}`}
        >
          <span className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
            {session.name}
          </span>
          <span className="flex items-center gap-1.5 text-xs text-zinc-400 dark:text-zinc-500">
            {session.talks.length} talks
            <ChevronDown
              className={`h-3.5 w-3.5 flex-shrink-0 transition-transform duration-150 ${open ? "rotate-180" : ""}`}
            />
          </span>
        </button>
      </div>

      {open && (
        <div className="ml-7 border-l-2 border-blue-100 pb-1 dark:border-blue-900/40">
          {session.talks.map((talk) => (
            <TalkRow key={talk.id} talk={talk} />
          ))}
        </div>
      )}
    </div>
  );
}
