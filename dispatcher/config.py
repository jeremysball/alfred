"""Configuration management using pydantic-settings."""
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment."""
    
    # Telegram
    telegram_bot_token: str
    
    # Paths
    workspace_dir: Path = Path("./workspace")
    threads_dir: Path = Path("./threads")
    
    # Logging
    log_level: str = "INFO"
    
    # Pi agent
    pi_timeout: int = 300  # seconds
    
    # LLM Provider (passed to pi)
    llm_provider: str = "zai"  # zai, moonshot
    llm_api_key: str = ""
    llm_model: str = ""  # Optional override
    
    # Limits
    max_threads: int = 50
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
