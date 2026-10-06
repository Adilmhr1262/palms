from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    env: str = "development"
    database_url: str = "postgresql+psycopg://palms:palms@localhost:5432/palms"
    jwt_secret: str = "change-me-to-a-long-random-string"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 120
    upload_dir: str = "uploads"
    max_upload_mb: int = 10


settings = Settings()
