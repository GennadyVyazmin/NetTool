from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str = Field(alias="BOT_TOKEN")
    public_webapp_url: str = Field(alias="PUBLIC_WEBAPP_URL")
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    db_path: str = Field(default="./data/nettool.db", alias="DB_PATH")
    geolookup_url: str = Field(default="https://ipwho.is", alias="GEOLOOKUP_URL")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
