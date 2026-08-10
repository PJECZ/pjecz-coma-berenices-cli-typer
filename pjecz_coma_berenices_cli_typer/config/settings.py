"""
Config Settings
"""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Settings"""

    AGENDAMIENTO_AUDIENCIAS_FECHA_API_URL: str = ""
    AGENDAMIENTO_AUDIENCIAS_PANTALLA_API_URL: str = ""
    AGENDAMIENTO_AUDIENCIAS_API_KEY: str = ""
    TZ: str = "America/Mexico_City"
    VOCEADOR_URL: str = ""
    VOCEADOR_VOZ: int = 1
    VOCEADOR_VOZ_VELOCIDAD: str = "1.0"

    class Config:
        """Config"""

        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Get settings"""
    return Settings()
