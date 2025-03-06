from dotenv import load_dotenv
import os

# Load .env file
load_dotenv()


class Settings:
    DATABASE_NAME: str = os.getenv("DBNAME")
    DATABASE_PASSWORD: str = os.getenv("DBPASS")
    DATABASE_PORT: str = os.getenv("DBPORT")
    DATABASE_USER: str = os.getenv("DBUSER")
    DATABASE_HOST: str = os.getenv("DBHOST")

settings = Settings()
