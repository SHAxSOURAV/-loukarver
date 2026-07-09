from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "loukarver"
    API_V1_STR: str = "/api"
    MONGO_URL: str = ""
    MONGO_DB_NAME: str = "loukarver"
    
    # JWT Secrets
    SECRET_KEY: str = ""
    REFRESH_SECRET_KEY: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = ""
    REFRESH_TOKEN_EXPIRE_DAYS: int = ""
    
    # SMTP Settings
    SMTP_HOST: str = ""
    SMTP_PORT: int = ""
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    FROM_EMAIL: str = ""
    
    # YouTube Integration
    YOUTUBE_CLIENT_ID: str = ""
    YOUTUBE_CLIENT_SECRET: str = ""
    YOUTUBE_REDIRECT_URI: str = ""
    YOUTUBE_API_KEY: str = ""
    
    # Gemini Integration
    GEMINI_API_KEY: str = ""
    
    # Local LLM Integration
    USE_LOCAL_LLM: bool = False
    LOCAL_LLM_URL: str = "http://127.0.0.1:1234/v1/chat/completions"
    LOCAL_LLM_MODEL: str = "llama-3.2-3b-instruct"
    
    # OneSignal Integration
    ONESIGNAL_APP_ID: str = ""
    ONESIGNAL_REST_API_KEY: str = ""
    
    FRONTEND_URL: str = ""
    
    # Read from .env if present
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
