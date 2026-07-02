from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    source_base_url: str = "https://www.churchofjesuschrist.org"
    http_user_agent: str = (
        "GC-Downloader/0.1 (personal educational project; contact via GitHub)"
    )
    max_concurrency: int = 12
    request_delay_ms: int = 100
    catalog_ttl: int = 43200
    http_timeout: int = 30
    cors_origins: str = "http://localhost:3000"
    delivery_mode: str = "auto"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
