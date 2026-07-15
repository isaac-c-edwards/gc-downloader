const DEFAULT_API_BASE_URL = "http://localhost:8000";

export function getApiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? DEFAULT_API_BASE_URL;
}

/**
 * Carries the backend's error `code` (see docs/07 error format) alongside
 * the message, so callers can distinguish e.g. a genuinely-unavailable
 * translation (`LanguageUnavailable`) from a real failure worth retrying.
 */
export class ApiError extends Error {
  code: string;
  status: number;

  constructor(message: string, code: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
  }
}

async function apiFetch<T>(path: string, params?: Record<string, string>): Promise<T> {
  const url = new URL(`${getApiBaseUrl()}${path}`);
  if (params) {
    Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));
  }
  const res = await fetch(url.toString(), { cache: "no-store" });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(
      body?.error?.message ?? `HTTP ${res.status}`,
      body?.error?.code ?? "Internal",
      res.status,
    );
  }
  return res.json() as Promise<T>;
}

// ── Types (mirror docs/09) ────────────────────────────────────────────────────

export type Language = { code: string; name: string };

export type LanguagesResponse = {
  languages: Language[];
  default: string;
};

export type Conference = {
  id: string;
  year: number;
  month: number;
  name: string;
  image_url?: string;
};

export type Talk = {
  id: string;
  uri: string;
  order: number;
  title: string;
  speaker: string;
  image_url?: string;
};

export type Session = {
  id: string;
  order: number;
  name: string;
  talks: Talk[];
};

export type ConferenceDetail = Conference & { sessions: Session[] };

export type CatalogResponse = { conferences: Conference[] };

export type HealthResponse = { status: string };

// ── Fetch functions ───────────────────────────────────────────────────────────

export const fetchHealth = () => apiFetch<HealthResponse>("/api/health");

export const fetchLanguages = () => apiFetch<LanguagesResponse>("/api/languages");

export const fetchCatalog = (lang: string) =>
  apiFetch<CatalogResponse>("/api/catalog", { lang });

export const fetchConference = (id: string, lang: string) =>
  apiFetch<ConferenceDetail>(`/api/conferences/${id}`, { lang });

export type DownloadSelection = {
  conference_id: string;
  session_ids?: string[];
  talk_ids?: string[];
};

// ── Mode B: async jobs ────────────────────────────────────────────────────────

export type JobStatus = {
  job_id: string;
  state: "queued" | "running" | "done" | "error";
  total: number;
  completed: number;
  skipped: { talk_id: string; reason: string }[];
  download_ready: boolean;
  error_msg: string | null;
  /** 1-based place in line while waiting for a free slot; 0 once running/done. */
  queue_position: number;
};

export async function createJob(
  lang: string,
  selection: DownloadSelection[],
): Promise<{ job_id: string; total: number }> {
  const res = await fetch(`${getApiBaseUrl()}/api/jobs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ lang, selection }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.error?.message ?? `Failed to create job (${res.status})`);
  }
  return res.json();
}

export async function pollJob(job_id: string): Promise<JobStatus> {
  const res = await fetch(`${getApiBaseUrl()}/api/jobs/${job_id}`);
  if (!res.ok) throw new Error(`Job poll failed (${res.status})`);
  return res.json();
}

export async function downloadJobResult(job_id: string): Promise<void> {
  const res = await fetch(`${getApiBaseUrl()}/api/jobs/${job_id}/download`);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.error?.message ?? `Download failed (${res.status})`);
  }
  const disposition = res.headers.get("Content-Disposition") ?? "";
  const match = disposition.match(/filename="([^"]+)"/);
  const contentType = res.headers.get("Content-Type") ?? "";
  const ext = contentType.includes("audio") ? ".mp3" : ".zip";
  const filename = match?.[1] ?? `gc-downloader${ext}`;
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

// ── Mode A: direct streaming ──────────────────────────────────────────────────

export async function triggerDownload(
  lang: string,
  selection: DownloadSelection[],
): Promise<void> {
  const res = await fetch(`${getApiBaseUrl()}/api/download`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ lang, selection }),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.error?.message ?? `Download failed (${res.status})`);
  }

  // Extract filename from Content-Disposition header if present.
  // Content-Disposition is a non-simple CORS header — the backend must expose
  // it via Access-Control-Expose-Headers for the browser to read it here.
  const disposition = res.headers.get("Content-Disposition") ?? "";
  const match = disposition.match(/filename="([^"]+)"/);
  const contentType = res.headers.get("Content-Type") ?? "";
  const ext = contentType.includes("audio") ? ".mp3" : ".zip";
  const filename = match?.[1] ?? `gc-downloader${ext}`;

  // Stream the ZIP into a blob and trigger a browser download
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
