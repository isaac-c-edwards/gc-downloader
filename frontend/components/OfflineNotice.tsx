/**
 * Flip to false (or remove this component from the page) when the
 * backend is back online.
 */
export const SERVICE_OFFLINE = true;

export function OfflineNotice() {
  return (
    <div
      className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-4 text-amber-950 dark:border-amber-900/60 dark:bg-amber-950/40 dark:text-amber-100"
      role="status"
    >
      <p className="text-sm font-semibold">Temporarily offline</p>
      <p className="mt-1.5 text-sm leading-relaxed text-amber-900/90 dark:text-amber-100/90">
        The download service hit its free hosting bandwidth limit. I&apos;ll
        bring it back when the quota resets (or when I can host it elsewhere).
        Thanks for understanding :)
      </p>
    </div>
  );
}
