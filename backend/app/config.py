"""
Application configuration settings.
Loads from environment variables with sensible defaults.
"""

import os
from typing import List
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""
    
    def __init__(self):
        # Environment
        self.environment: str = os.getenv("ENVIRONMENT", "development")
        self.debug: bool = os.getenv("DEBUG", "false").lower() == "true"
        self.port: int = int(os.getenv("PORT", "5050"))
        
        # OpenAI Configuration
        self.openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
        self.openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-realtime-preview-2024-12-17")
        self.openai_voice: str = os.getenv("OPENAI_VOICE", "alloy")
        
        # Twilio Configuration (for reference, actual auth handled by Twilio)
        self.twilio_account_sid: str = os.getenv("TWILIO_ACCOUNT_SID", "")
        self.twilio_auth_token: str = os.getenv("TWILIO_AUTH_TOKEN", "")
        
        # CORS
        cors_origins_str = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")
        self.cors_origins: List[str] = [origin.strip() for origin in cors_origins_str.split(",")]
        
        # Data paths
        self.data_dir: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        
    def validate(self) -> List[str]:
        """Validate required settings and return list of errors."""
        errors = []
        
        if not self.openai_api_key:
            errors.append("OPENAI_API_KEY is required")
            
        return errors
    
    @property
    def is_production(self) -> bool:
        return self.environment == "production"


# Global settings instance
settings = Settings()
