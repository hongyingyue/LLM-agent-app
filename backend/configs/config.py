import os
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@dataclass
class LLMConfig:
    """Configuration for LLM settings"""
    temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    top_p: float = float(os.getenv("LLM_TOP_P", "1.0"))
    model_name: str = os.getenv("LLM_MODEL_NAME", "gpt-4.1-mini")
    api_key: str = os.getenv("OPENAI_API_KEY", "")
    max_tokens: Optional[int] = int(os.getenv("LLM_MAX_TOKENS", "2000")) if os.getenv("LLM_MAX_TOKENS") else None
    timeout: int = int(os.getenv("LLM_TIMEOUT", "60"))
    retry_attempts: int = int(os.getenv("LLM_RETRY_ATTEMPTS", "3"))

@dataclass
class AppConfig:
    """Main application configuration"""
    environment: str = os.getenv("APP_ENV", "development")
    debug: bool = os.getenv("APP_DEBUG", "False").lower() == "true"
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    # LLM Configuration
    llm: LLMConfig = field(default_factory=LLMConfig)

    def __post_init__(self):
        """Validate configuration after initialization"""
        if not self.llm.api_key:
            raise ValueError("OPENAI_API_KEY is required but not set in environment variables")
        
        if self.environment not in ["development", "staging", "production"]:
            raise ValueError(f"Invalid environment: {self.environment}")

# Create a singleton instance
config = AppConfig()

# Export the configuration
__all__ = ["config", "AppConfig", "LLMConfig"]
