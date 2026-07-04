import type { QueryClient } from "@tanstack/react-query";

import type { ConferenceDetail } from "./api";

/** React Query key: ["conference", conferenceId, lang] */
export function conferenceDetailQueryKey(conferenceId: string, lang: string) {
  return ["conference", conferenceId, lang] as const;
}

/** Conference details cached for download — current language only. */
export function getCachedConferenceDetails(
  queryClient: QueryClient,
  language: string,
): ConferenceDetail[] {
  const details: ConferenceDetail[] = [];
  for (const query of queryClient.getQueryCache().getAll()) {
    const key = query.queryKey as unknown[];
    if (
      key[0] === "conference" &&
      key[2] === language &&
      query.state.status === "success" &&
      query.state.data
    ) {
      details.push(query.state.data as ConferenceDetail);
    }
  }
  return details;
}
