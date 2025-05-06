import os
from typing import List, Optional, Union, Dict, Any
from pydantic import BaseModel, field_validator, PostgresDsn, computed_field
from dotenv import load_dotenv
import urllib.parse

# Load environment variables
load_dotenv()


class Settings(BaseModel):
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Bantuv2"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "Bantu API for managing resources"

    # CORS Settings
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost",
        "http://localhost:8080",
        "http://localhost:3000",  # React default
        "http://localhost:8000",  # FastAPI default
    ]

    TRANSCRIPTION_BASE_WIDTH: int = 6
    TRANSLATION_BASE_WIDTH: int = 3
    ANNOTATION_BASE_WIDTH: int = 4

    DEFAULT_BASE_WIDTH: int = 4

    TTE: int = 30

    POINTS_PER_CONTRIBUTION: int = 10
    POINTS_PER_EVALUATION: int = 10
    POINTS_PER_AB_TEST: int = 5

    AB_TEST_WINNER_BONUS: int = 5

    POINTS_PER_CONTRIBUTION_ACCEPTANCE: int = 8
    POINTS_FOR_ACCURATE_EVALUATION: int = 8

    AB_TEST_PROFICIENCY_QUALIFICATION: int = 6
    EVALUATOR_PROFICIENCY_THRESHOLD: int = 7

    # Security settings
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "5"))
    ACCESS_SECRET_KEY: str = os.getenv("ACCESS_SECRET_KEY", "your_default_secret_key")
    REFRESH_SECRET_KEY: str = os.getenv("REFRESH_SECRET_KEY", "your_other_default_refresh_secret_key")

    # Admin user
    FIRST_SUPERUSER: Optional[str] = os.getenv("FIRST_SUPERUSER", "admin@bantu.com")
    FIRST_SUPERUSER_PASSWORD: Optional[str] = os.getenv("FIRST_SUPERUSER_PASSWORD", "admin")

    # Database settings
    POSTGRES_USER: str = os.getenv("DBUSER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("DBPASS", "postgres")
    POSTGRES_HOST: str = os.getenv("DBHOST", "localhost")
    POSTGRES_PORT: int = int (os.getenv("DBPORT", "5432"))
    POSTGRES_DB: str = os.getenv("DBNAME", "bantu_db")
    # SQLALCHEMY_DATABASE_URI: Optional[str] = None

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))

    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = ENVIRONMENT == "development"

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Computed SQLAlchemy Database URI
    @computed_field
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        print("Computing SQLALCHEMY_DATABASE_URI...")  # Debugging statement
        encoded_password = urllib.parse.quote_plus(self.POSTGRES_PASSWORD)
        return str(
            PostgresDsn.build(
                scheme="postgresql+asyncpg",
                username=self.POSTGRES_USER,
                password=encoded_password,
                host=self.POSTGRES_HOST,
                port=self.POSTGRES_PORT,
                path=f"{self.POSTGRES_DB or ''}",
            )
        )

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        raise ValueError("Invalid CORS origins format.")

    class Config:
        case_sensitive = True
        env_file = ".env"


# Create settings instance
settings = Settings()

# # Print to verify
# print(settings.SQLALCHEMY_DATABASE_URI)
