"""Configuration management using pydantic-settings."""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


# Default to workspace in the current working directory
DEFAULT_WORKSPACE = Path.cwd() / "workspace"
DEFAULT_THREADS = Path.cwd() / "threads"
DEFAULT_PI_PATH = Path.cwd() / "node_modules" / ".bin" / "pi"


class Settings(BaseSettings):
    """Application settings loaded from environment."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    # Telegram
    TELEGRAM_BOT_TOKEN: str
    
    # Paths - default to ./workspace and ./threads in current directory
    WORKSPACE_DIR: Path = DEFAULT_WORKSPACE
    THREADS_DIR: Path = DEFAULT_THREADS
    PI_PATH: Path = DEFAULT_PI_PATH
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    # Pi agent
    PI_TIMEOUT: int = 300
    
    # LLM Provider (passed to pi)
    LLM_PROVIDER: str = "zai"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = ""
    
    # ZAI specific (backwards compat)
    ZAI_API_KEY: str = ""
    
    # Limits
    MAX_THREADS: int = 50
    
    # Convenience properties for backwards compatibility
    @property
    def telegram_bot_token(self) -> str:
        return self.TELEGRAM_BOT_TOKEN
    
    @property
    def workspace_dir(self) -> Path:
        return self.WORKSPACE_DIR
    
    @property
    def threads_dir(self) -> Path:
        return self.THREADS_DIR
    
    @property
    def pi_path(self) -> Path:
        return self.PI_PATH
    
    @property
    def log_level(self) -> str:
        return self.LOG_LEVEL
    
    @property
    def pi_timeout(self) -> int:
        return self.PI_TIMEOUT
    
    @property
    def llm_provider(self) -> str:
        return self.LLM_PROVIDER
    
    @property
    def llm_api_key(self) -> str:
        return self.LLM_API_KEY or self.ZAI_API_KEY
    
    @property
    def llm_model(self) -> str:
        return self.LLM_MODEL
    
    @property
    def max_threads(self) -> int:
        return self.MAX_THREADS
