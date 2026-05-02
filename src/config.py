"""配置管理模块"""
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # DeepSeek API
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    # Database
    database_url: str = "sqlite:///db/deep_reviser.db"
    chroma_persist_dir: str = "db/chroma"

    # Upload
    upload_dir: str = "data/uploads"
    max_upload_size_mb: int = 50

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def project_root(self) -> Path:
        return Path(__file__).parent.parent


settings = Settings()
