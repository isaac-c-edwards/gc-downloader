"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchLanguages } from "@/lib/api";
import { useSelectionStore } from "@/lib/store";

export function LanguageSelect() {
  const { language, setLanguage } = useSelectionStore();
  const queryClient = useQueryClient();

  const { data } = useQuery({
    queryKey: ["languages"],
    queryFn: fetchLanguages,
    staleTime: Infinity,
  });

  function handleChange(newLang: string) {
    setLanguage(newLang);
    // Drop stale conference details from other languages so downloads can't
    // match the same talk_id twice (SelectionBar reads from this cache).
    queryClient.removeQueries({
      queryKey: ["conference"],
      predicate: (query) => query.queryKey[2] !== newLang,
    });
    // Re-fetch open accordions in the new language.
    queryClient.invalidateQueries({ queryKey: ["conference"] });
  }

  return (
    <select
      value={language}
      onChange={(e) => handleChange(e.target.value)}
      className="rounded-lg border border-zinc-200 bg-white px-3 py-1.5 text-sm text-zinc-700 shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-200"
      aria-label="Audio language"
    >
      {(data?.languages ?? [{ code: "eng", name: "English" }]).map((lang) => (
        <option key={lang.code} value={lang.code}>
          {lang.name}
        </option>
      ))}
    </select>
  );
}
