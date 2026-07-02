# 11 — Legal & Ethics

This app fetches publicly available content from `churchofjesuschrist.org` on
behalf of a user, for that user's personal offline use. Build it to be a good
citizen of the web.

## Copyright & ownership

- General Conference audio, images, and text are the property of their owner
  (Intellectual Reserve, Inc. / The Church of Jesus Christ of Latter-day Saints).
- This app **does not** re-host, sell, or claim ownership of any content. It
  fetches files on demand for the requesting user and hands them over; it does not
  build a public mirror.
- Downloaded files are for the user's **personal, non-commercial** offline use.
- Include a short disclaimer in the app footer and README, e.g.:
  > "Unofficial tool. General Conference audio and images are © Intellectual
  > Reserve, Inc. This app downloads publicly available files for personal use and
  > is not affiliated with or endorsed by The Church of Jesus Christ of Latter-day
  > Saints."

## Polite scraping rules (MUST follow)

1. **Identify yourself.** Send a descriptive `User-Agent` that includes the app
   name and a contact (e.g. a project URL or email). Do not spoof a browser to
   deceive.
2. **Respect `robots.txt`.** Check and honor it for the paths you fetch.
3. **Rate limit.** Cap concurrency (`MAX_CONCURRENCY`, default 4) and add a small
   jittered delay between source requests (`REQUEST_DELAY_MS`). Never burst.
4. **Back off on errors.** On HTTP 429/503, honor `Retry-After`; use exponential
   backoff (tenacity). If the server signals overload, slow down.
5. **Cache aggressively for metadata.** The catalog rarely changes — cache it
   (NFR-3) so browsing the UI doesn't generate repeated source requests.
6. **Fetch only what's requested.** Resolve and download audio only for talks the
   user explicitly selected. Do not pre-crawl the entire archive.
7. **Avoid peak times for bulk jobs.** Community guidance specifically warns
   against heavy automated requests during peak traffic (notably Sundays).
   Consider this in any scheduled refresh.
8. **No login/paywall circumvention.** Only access content that is freely public.

## Reliability/ethics of the hybrid approach

- Prefer the structured content path; fall back to HTML only when needed. This
  reduces load and is more stable than aggressive DOM scraping.
- Fail soft: skip a missing/unavailable talk and report it rather than retrying
  endlessly.

## Privacy

- No user accounts, no tracking, no PII collection in v1.
- Do not log full request bodies containing anything sensitive (there shouldn't
  be any). Log only URLs/status/timings at debug level.

## Disclaimer for the maintainer

This is an unofficial personal tool. If usage ever grew beyond personal scale,
revisit terms of use and reach out to the content owner. Keep the footprint small,
respectful, and on-demand.
