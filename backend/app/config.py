from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", env_file_encoding="utf-8")

    host: str = "0.0.0.0"
    port: int = 8000

    ollama_host: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen3-14b-tr"

    supabase_url: str = ""
    supabase_anon_key: str = ""

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = "FinansAjani/1.0"

    bist_tickers: str = "THYAO.IS,ASELS.IS,BIMAS.IS,AKBNK.IS,EREGL.IS,GARAN.IS,ISCTR.IS,SAHOL.IS,SISE.IS,TOASO.IS"

    scan_interval: int = 3600

    @property
    def tickers(self) -> list[str]:
        return [t.strip() for t in self.bist_tickers.split(",") if t.strip()]


settings = Settings()
