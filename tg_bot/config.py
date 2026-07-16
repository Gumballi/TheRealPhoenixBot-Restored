import os
from tg_bot.sample_config import Config as SampleConfig


class Config(SampleConfig):
    # REQUIRED - Pulls safely from VPS environment variables
    API_KEY = os.environ.get("API_KEY", "PLACEHOLDER_TOKEN")
    OWNER_ID = int(os.environ.get("OWNER_ID", "0"))
    OWNER_USERNAME = os.environ.get("OWNER_USERNAME", "PLACEHOLDER_USER")

    # Add Mistral key fallback
    MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY", None)
    
    # MyAnimeList Configuration
    MAL_CLIENT_ID = os.environ.get("MAL_CLIENT_ID", "")
    MAL_ACCESS_TOKEN = os.environ.get("MAL_ACCESS_TOKEN", "")
    MAL_REFRESH_TOKEN = os.environ.get("MAL_REFRESH_TOKEN", "")
    MAL_CLIENT_SECRET = os.environ.get("MAL_CLIENT_SECRET", "")

    # RECOMMENDED
    SQLALCHEMY_DATABASE_URI = os.environ.get("SQLALCHEMY_DATABASE_URI", "postgresql://user:pass@host/db")


class Production(Config):
    LOGGER = False


class Development(Config):
    LOGGER = True
