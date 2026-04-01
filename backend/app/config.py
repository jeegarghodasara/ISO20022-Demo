from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    mongodb_uri: str = "mongodb://localhost:27017"
    database_name: str = "iso20022_payments"
    host: str = "0.0.0.0"
    port: int = 8000
    voyage_api_key: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
