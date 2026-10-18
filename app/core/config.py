from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "samesy"
    API_V1_STR: str = "/api"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    MONGO_URL: str = ""
    MONGO_DB_NAME: str = "loukarver"
    
    # JWT Secrets
    SECRET_KEY: str = ""
    REFRESH_SECRET_KEY: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    ADMIN_CREATION_SECRET: str = ""
    
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
    

    
    # OneSignal Integration
    ONESIGNAL_APP_ID: str = ""
    ONESIGNAL_REST_API_KEY: str = ""
    
    FRONTEND_URL: str = ""
    
    # AWS S3 Configuration
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "eu-north-1"
    AWS_S3_BUCKET_NAME: str = ""
    
    # MapTiler Configuration
    MAPTILER_API_KEY: str = ""
    
    # Read from .env if present
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
