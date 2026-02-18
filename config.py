import os
from pydantic import BaseSettings

class Settings(BaseSettings):
    # Define your settings with type hints here
    database_url: str
    api_key: str
    debug: bool = False

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'

# Create a settings instance, automatically loading from environment variables
settings = Settings()  

# Validate environment variables
if not settings.database_url:
    raise ValueError("DATABASE_URL is not set in the environment.")
if not settings.api_key:
    raise ValueError("API_KEY is not set in the environment.")
