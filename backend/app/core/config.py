import json
import os
from typing import List
from pydantic import BaseModel

class Settings(BaseModel):
    APP_NAME: str = "Integra Analytics API"
    DEBUG: bool = False

    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    SUPABASE_JWKS_URL: str = ""

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

# Load from environment
settings = Settings(
    SUPABASE_URL=os.getenv("SUPABASE_URL", ""),
    SUPABASE_SERVICE_KEY=os.getenv("SUPABASE_SERVICE_KEY", ""),
    SUPABASE_JWKS_URL=os.getenv("SUPABASE_JWKS_URL", ""),
    CORS_ORIGINS=json.loads(os.getenv("CORS_ORIGINS", '["http://localhost:3000"]')),
    DEBUG=os.getenv("DEBUG", "false").lower() == "true",
    HOST=os.getenv("HOST", "0.0.0.0"),
    PORT=int(os.getenv("PORT", "8000")),
)
