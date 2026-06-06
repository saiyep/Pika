from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # WeChat Mini Program
    wx_appid: str = ""
    wx_secret: str = ""

    # Azure OpenAI (gpt-5.4-mini, vision)
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_api_version: str = "2024-10-21"
    azure_openai_deployment: str = "gpt-5.4-mini"

    # Runtime paths
    data_dir: str = "./data"
    upload_dir: str = "./data/uploads/medical"
    db_path: str = "./data/db/pika.db"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
