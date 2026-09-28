"""
Configuración centralizada de la aplicación.
Lee variables de entorno desde .env usando pydantic-settings.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Base de datos ---
    DATABASE_URL: str = "postgresql+asyncpg://usuario:password@localhost:5432/obras_db"

    @property
    def get_database_url(self) -> str:
        # Railway (y otros servicios) a menudo proveen 'postgresql://...' 
        # pero SQLAlchemy requiere 'postgresql+asyncpg://...' para llamadas asíncronas
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://") and not url.startswith("postgresql+asyncpg://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    # --- Autenticación JWT ---
    SECRET_KEY: str = "CAMBIA_ESTA_CLAVE_EN_PRODUCCION"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 horas

    # --- App ---
    APP_NAME: str = "Obras ERP API"
    DEBUG: bool = True

    # --- Almacenamiento de archivos (local por ahora) ---
    STORAGE_DIR: str = "storage"

    # --- CORS ---
    # Orígenes permitidos, separados por coma. "*" (por defecto, solo
    # cómodo para desarrollo) permite cualquiera — cámbialo por la URL
    # real de tu app/panel web antes de producción, ej.:
    # ALLOWED_ORIGINS=https://app.tuempresa.com,https://admin.tuempresa.com
    ALLOWED_ORIGINS: str = "*"

    # --- Correo (Resend) ---
    RESEND_API_KEY: str | None = None
    FROM_EMAIL: str = "onboarding@resend.dev"

    @property
    def allowed_origins_list(self) -> list[str]:
        if self.ALLOWED_ORIGINS.strip() == "*":
            return ["*"]
        return [origen.strip() for origen in self.ALLOWED_ORIGINS.split(",") if origen.strip()]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
