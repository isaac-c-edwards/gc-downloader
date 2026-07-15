from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    source_base_url: str = "https://www.churchofjesuschrist.org"
    http_user_agent: str = (
        "GC-Downloader/0.1 (unofficial personal tool; contact via GitHub)"
    )
    max_concurrency: int = 12
    # How many download jobs may *build* at the same time. Extra jobs queue
    # (fairly, FIFO) instead of being rejected, so many users are served in
    # parallel. Keep small on Render's free tier; raise it after upgrading.
    max_concurrent_jobs: int = 3
    # Admission cap: running + waiting jobs. Beyond this, new job requests are
    # rejected with a 503 "server busy" instead of piling on until the
    # instance runs out of RAM/disk.
    max_queued_jobs: int = 20
    # Per-job outbound concurrency. The global `max_concurrency` is the true
    # politeness cap on the source site; this smaller per-job slice keeps one
    # big job from monopolizing every slot while others starve.
    per_job_concurrency: int = 4
    request_delay_ms: int = 100
    catalog_ttl: int = 43200
    catalog_cache_maxsize: int = 128
    http_timeout: int = 30
    cors_origins: str = "http://localhost:3000"
    delivery_mode: str = "auto"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
