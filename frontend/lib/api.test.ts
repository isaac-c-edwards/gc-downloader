import { describe, expect, it } from "vitest";

import { ApiError } from "./api";

describe("ApiError", () => {
  it("exposes backend error code and HTTP status", () => {
    const err = new ApiError("Not available", "LanguageUnavailable", 404);
    expect(err).toBeInstanceOf(Error);
    expect(err.code).toBe("LanguageUnavailable");
    expect(err.status).toBe(404);
    expect(err.message).toBe("Not available");
  });
});
