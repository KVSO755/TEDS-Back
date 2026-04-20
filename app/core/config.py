from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Base de datos — Railway MySQL con aiomysql
    DATABASE_URL: str = "mysql+aiomysql://root:pcYdGqNQqXhrudxTKVfRPbRKKCfExkcC@mysql.railway.internal:3306/railway"

    # JWT
    SECRET_KEY: str = "65b90e784de1a987221685645a729c4954e120306778403e9ba50b899b5e1eb1a64648c985ff62937ccc96de8b3b48bbb1168d08f29b11a80ff70e60c3957c21"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Azure Storage (opcional)
    AZURE_STORAGE_CONNECTION_STRING: str = ""
    AZURE_STORAGE_CONTAINER: str = "session-logs"

    # App
    ENVIRONMENT: str = "production"
    ALLOWED_ORIGINS: str = "*"

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]


settings = Settings()
