from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://lifelog:lifelog@db:5432/lifelog"

    model_config = {"env_file": ".env"}


settings = Settings()
