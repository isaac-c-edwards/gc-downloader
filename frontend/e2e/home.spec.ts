import { expect, test } from "@playwright/test";

test("homepage shows the app shell", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "GC Downloader" })).toBeVisible();
  await expect(page.getByText("Choose your sessions")).toBeVisible();
});

test("language selector is available", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByLabel("Audio language")).toBeVisible();
});

test("backend health endpoint responds", async ({ request }) => {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
  const res = await request.get(`${base}/api/health`);
  expect(res.ok()).toBeTruthy();
  const body = await res.json();
  expect(body).toEqual({ status: "ok" });
});
