from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "FRONTIÈRE - INSTITUT POUR L’INTÉRÊT PUBLIC -"
    database_url: str = "sqlite:///./data/frontiere.db"
    env: str = "development"
    secret_key: str = "development-only"

    model_config = SettingsConfigDict(env_prefix="FRONTIERE_", env_file=".env", extra="ignore")


settings = Settings()
