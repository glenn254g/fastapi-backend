from dotenv import load_dotenv
from pathlib import Path
from pydantic_settings import BaseSettings

# Load .env from backend folder
BASE_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = BASE_DIR / ".env"
load_dotenv(ENV_PATH)

class Settings(BaseSettings):
    PROJECT_NAME: str
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    ADMIN_EMAIL: str
    ADMIN_PASSWORD: str
    SQLALCHEMY_DATABASE_URI: str
    API_V1_STR: str
    SENTRY_DSN: str = ""
    ENVIRONMENT: str = "local"

settings = Settings()
