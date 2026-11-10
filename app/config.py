from typing import List, Union
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "HR Management Platform API"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    # Security
    SECRET_KEY: str = "supersecretdevelopmentkeythatmustbechangedinproductionenvironment"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Database
    DATABASE_URL: str = "sqlite:///./hrms.db"

    # Seed Admin Defaults
    INITIAL_ADMIN_EMAIL: str = "admin@hrms.local"
    INITIAL_ADMIN_PASSWORD: str = "AdminPassword123!"
    INITIAL_ADMIN_FIRST_NAME: str = "System"
    INITIAL_ADMIN_LAST_NAME: str = "Administrator"

    # CORS
    CORS_ORIGINS: Union[str, List[str]] = "*"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    @property
    def cors_origins_list(self) -> List[str]:
        if isinstance(self.CORS_ORIGINS, list):
            return self.CORS_ORIGINS
        if self.CORS_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()
