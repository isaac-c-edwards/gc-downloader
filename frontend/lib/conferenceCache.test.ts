import { QueryClient } from "@tanstack/react-query";
import { describe, expect, it } from "vitest";

import type { ConferenceDetail } from "./api";
import { conferenceDetailQueryKey, getCachedConferenceDetails } from "./conferenceCache";

const stubDetail = (id: string): ConferenceDetail => ({
  id,
  year: 2026,
  month: 4,
  name: "April 2026 General Conference",
  sessions: [],
});

describe("getCachedConferenceDetails", () => {
  it("returns only conference details for the requested language", () => {
    const client = new QueryClient();
    client.setQueryData(conferenceDetailQueryKey("2026-04", "eng"), stubDetail("2026-04"));
    client.setQueryData(conferenceDetailQueryKey("2026-04", "por"), stubDetail("2026-04"));

    const eng = getCachedConferenceDetails(client, "eng");
    const por = getCachedConferenceDetails(client, "por");

    expect(eng).toHaveLength(1);
    expect(por).toHaveLength(1);
    expect(eng[0].id).toBe("2026-04");
    expect(por[0].id).toBe("2026-04");
  });
});
