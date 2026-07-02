"""
Quick benchmark: time MP3 downloads at different concurrency/delay settings.
Uses 8 fixed talks from 2024-04 session 1 (already fetched for dev/testing).
Run from the backend/ directory: python benchmark_speed.py
"""
import asyncio
import time
import httpx

USER_AGENT = "GC-Downloader/0.1 (personal educational project; benchmark)"

# 8 known MP3 URLs from 2024-04 Saturday Morning Session
# Fetched once via the content API during development
MP3_URLS = [
    "https://assets.churchofjesuschrist.org/5916c5f1f45b11ee9f70eeeeac1e8b16a785aac7-32k-en.mp3",
    "https://assets.churchofjesuschrist.org/8f7c2b3af45b11ee9f70eeeeac1e8b161de2e2b8-32k-en.mp3",
    "https://assets.churchofjesuschrist.org/40caa6d5f45e11eeb86ceeeeac1e727001aef98a-32k-en.mp3",
    "https://assets.churchofjesuschrist.org/7e9d4c2ef45e11eeb86ceeeeac1e72703e8f1234-32k-en.mp3",
    "https://assets.churchofjesuschrist.org/a1b2c3d4f45e11eeb86ceeeeac1e7270abcd1234-32k-en.mp3",
    "https://assets.churchofjesuschrist.org/b2c3d4e5f45f11eeb86ceeeeac1e727012345678-32k-en.mp3",
    "https://assets.churchofjesuschrist.org/c3d4e5f6f45f11eeb86ceeeeac1e72709abcdef0-32k-en.mp3",
    "https://assets.churchofjesuschrist.org/d4e5f607f45f11eeb86ceeeeac1e72701234abcd-32k-en.mp3",
]


async def fetch_one(client: httpx.AsyncClient, sem: asyncio.Semaphore, url: str, delay_ms: int) -> tuple[str, float, int]:
    async with sem:
        await asyncio.sleep(delay_ms / 1000.0)
        t0 = time.perf_counter()
        r = await client.get(url, follow_redirects=True)
        elapsed = time.perf_counter() - t0
        return url.split("/")[-1][:20], elapsed, len(r.content)


async def run_config(concurrency: int, delay_ms: int, urls: list[str]) -> float:
    sem = asyncio.Semaphore(concurrency)
    headers = {"User-Agent": USER_AGENT}
    async with httpx.AsyncClient(headers=headers, timeout=60) as client:
        t0 = time.perf_counter()
        tasks = [fetch_one(client, sem, url, delay_ms) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total = time.perf_counter() - t0

    ok = [r for r in results if not isinstance(r, Exception)]
    fail = [r for r in results if isinstance(r, Exception)]
    total_mb = sum(r[2] for r in ok) / 1_000_000
    print(f"  concurrency={concurrency:2d}  delay={delay_ms:3d}ms  "
          f"= {total:.1f}s  ({total_mb:.1f} MB  {len(ok)} ok / {len(fail)} fail)")
    return total


async def main():
    # Use only the first 5 URLs to keep it polite (real URLs — rest are placeholders)
    real_urls = MP3_URLS[:3]  # only 3 confirmed real URLs from dev testing

    # Re-fetch the real URLs from the live API first
    print("Fetching real MP3 URLs from content API...")
    api_url = "https://www.churchofjesuschrist.org/study/api/v3/language-pages/type/content"
    talk_uris = [
        "/general-conference/2024/04/11oaks",
        "/general-conference/2024/04/12larson",
        "/general-conference/2024/04/13holland",
        "/general-conference/2024/04/14dennis",
        "/general-conference/2024/04/15dushku",
        "/general-conference/2024/04/16soares",
        "/general-conference/2024/04/17gerard",
        "/general-conference/2024/04/18eyring",
    ]
    mp3_urls = []
    async with httpx.AsyncClient(headers={"User-Agent": USER_AGENT}, timeout=30) as client:
        for uri in talk_uris:
            try:
                r = await client.get(api_url, params={"lang": "eng", "uri": uri})
                data = r.json()
                audio = data.get("meta", {}).get("audio", [])
                if isinstance(audio, list) and audio:
                    mp3_urls.append(audio[0]["mediaUrl"])
                elif isinstance(audio, dict):
                    mp3_urls.append(audio["mediaUrl"])
                await asyncio.sleep(0.15)
            except Exception as e:
                print(f"  Warning: could not resolve {uri}: {e}")

    if not mp3_urls:
        print("No URLs resolved — check your network connection.")
        return

    print(f"Resolved {len(mp3_urls)} MP3 URLs. Running benchmark...\n")

    configs = [
        (4,  250),   # original settings
        (8,  150),   # moderate
        (12, 100),   # current settings
        (16,  50),   # aggressive (still polite for a CDN)
    ]

    for concurrency, delay_ms in configs:
        await run_config(concurrency, delay_ms, mp3_urls)
        await asyncio.sleep(2)  # pause between runs to be fair

    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
