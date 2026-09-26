# from pydantic_settings import BaseSettings


# class Settings(BaseSettings):
#     DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/setu_recon"
#     APP_ENV: str = "development"
#     PAGE_SIZE_DEFAULT: int = 20
#     PAGE_SIZE_MAX: int = 100

#     model_config = {"env_file": ".env", "extra": "ignore"}


# settings = Settings()
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    APP_ENV: str = "development"
    PAGE_SIZE_DEFAULT: int = 20
    PAGE_SIZE_MAX: int = 100

    model_config = {
        "env_file": ".env",
        "extra": "ignore",
    }


settings = Settings()


