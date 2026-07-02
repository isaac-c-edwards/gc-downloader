"use client";

import { useSelectionStore } from "@/lib/store";
import type { Talk } from "@/lib/api";

export function TalkRow({ talk }: { talk: Talk }) {
  const { isTalkSelected, toggleTalk } = useSelectionStore();
  const selected = isTalkSelected(talk.id);

  return (
    <label
      className={`flex cursor-pointer items-start gap-3 px-3 py-2 transition-colors hover:bg-blue-50/60 dark:hover:bg-blue-900/10 ${
        selected ? "bg-blue-50/40 dark:bg-blue-900/10" : ""
      }`}
    >
      <input
        type="checkbox"
        checked={selected}
        onChange={() => toggleTalk(talk.id)}
        className="mt-0.5 h-4 w-4 flex-shrink-0 accent-blue-500"
        aria-label={`${talk.title}${talk.speaker ? ` by ${talk.speaker}` : ""}`}
      />
      <div className="min-w-0">
        <p className="truncate text-sm text-zinc-800 dark:text-zinc-200">
          {talk.title}
        </p>
        {talk.speaker && (
          <p className="truncate text-xs text-zinc-400 dark:text-zinc-500">
            {talk.speaker}
          </p>
        )}
      </div>
    </label>
  );
}
