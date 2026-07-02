import { LanguageSelect } from "./LanguageSelect";

export function Header() {
  return (
    <header className="sticky top-0 z-20 border-b border-zinc-200 bg-white/90 backdrop-blur-sm dark:border-zinc-800 dark:bg-zinc-950/90">
      <div className="mx-auto flex max-w-4xl items-center justify-between px-4 py-3 sm:px-6">
        <div className="flex items-center gap-3">
          {/* Logo mark */}
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 text-xs font-bold text-white shadow-sm">
            GC
          </div>
          <div>
            <h1 className="text-sm font-bold leading-none text-zinc-900 dark:text-zinc-50">
              GC Downloader
            </h1>
            <p className="mt-0.5 text-[10px] leading-none text-zinc-400">
              General Conference MP3s
            </p>
          </div>
        </div>
        <LanguageSelect />
      </div>
    </header>
  );
}
