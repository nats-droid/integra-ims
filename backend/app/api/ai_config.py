"""
Integra — AI Config API Endpoint
Endpoint CRUD untuk company_ai_config dengan Fernet encryption.
Hanya bisa diakses via FastAPI (service_role ke Supabase).
RLS memblokir direct write dari frontend/supabase-js.
"""
import os
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from cryptography.fernet import Fernet

from app.api.auth import verify_jwt
from app.core.database import get_db

router = APIRouter()

# ── Fernet encryption ──────────────────────────────────────────
# Master key dari env var — TIDAK PERNAH di-commit ke git
_fernet = None


def get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        key = os.getenv("AI_MASTER_KEY")
        if not key:
            # Generate key untuk development pertama kali
            key = Fernet.generate_key().decode()
            print(f"[AI_CONFIG] AI_MASTER_KEY not set. Generated dev key: {key}")
            print("[AI_CONFIG] Save this to backend/.env as AI_MASTER_KEY=<key>")
        # Ensure key is bytes
        if isinstance(key, str):
            key = key.encode()
        _fernet = Fernet(key)
    return _fernet


# ── Pydantic models ────────────────────────────────────────────
class AIConfigUpdate(BaseModel):
    company_id: str
    llm_provider: str = "openai"  # openai | anthropic | google
    api_key: str
    is_enabled: bool = True


class AIConfigResponse(BaseModel):
    company_id: str
    llm_provider: str
    is_enabled: bool
    # API key plaintext TIDAK pernah dikembalikan ke frontend
    has_key: bool


# ── Endpoints ──────────────────────────────────────────────────

@router.get("/ai-config/{company_id}")
async def get_ai_config(
    company_id: str,
    user: dict = Depends(verify_jwt),
):
    """
    GET /api/v1/ai-config/{company_id}
    Ambil AI config milik tenant.
    Role check: user hanya bisa lihat config company-nya sendiri
    (super_admin boleh lihat company manapun).
    """
    # Role validation — jangan andalkan RLS doang
    if user["role"] != "super_admin" and user["company_id"] != company_id:
        raise HTTPException(status_code=403, detail="Forbidden: not your company")

    db = get_db()
    result = (
        db.table("company_ai_config")
        .select("company_id, llm_provider, is_enabled, api_key_encrypted")
        .eq("company_id", company_id)
        .maybe_single()
        .execute()
    )

    if not result.data:
        return {"configured": False, "company_id": company_id}

    row = result.data
    return AIConfigResponse(
        company_id=row["company_id"],
        llm_provider=row["llm_provider"],
        is_enabled=row["is_enabled"],
        has_key=bool(row.get("api_key_encrypted")),
    )


@router.put("/ai-config/{company_id}")
async def upsert_ai_config(
    company_id: str,
    body: AIConfigUpdate,
    user: dict = Depends(verify_jwt),
):
    """
    PUT /api/v1/ai-config/{company_id}
    Set atau update AI config tenant.
    - API key di-ENCRYPT pakai Fernet sebelum dikirim ke Supabase
    - Validasi: user hanya bisa set company-nya sendiri (kecuali super_admin)
    """
    # Role validation
    if user["role"] != "super_admin" and user["company_id"] != company_id:
        raise HTTPException(status_code=403, detail="Forbidden: not your company")

    # Validasi: company_id di body harus match URL
    if body.company_id != company_id:
        raise HTTPException(status_code=400, detail="company_id mismatch")

    # Encrypt API key
    fernet = get_fernet()
    encrypted_key = fernet.encrypt(body.api_key.encode()).decode()

    db = get_db()
    result = (
        db.table("company_ai_config")
        .upsert(
            {
                "company_id": company_id,
                "llm_provider": body.llm_provider,
                "api_key_encrypted": encrypted_key,
                "is_enabled": body.is_enabled,
            },
            on_conflict="company_id",
        )
        .execute()
    )

    return {
        "status": "updated",
        "company_id": company_id,
        "llm_provider": body.llm_provider,
        "is_enabled": body.is_enabled,
        "has_key": True,
    }


@router.delete("/ai-config/{company_id}")
async def delete_ai_config(
    company_id: str,
    user: dict = Depends(verify_jwt),
):
    """
    DELETE /api/v1/ai-config/{company_id}
    Hapus AI config tenant (revoke API key).
    Hanya super_admin atau user dari company tersebut.
    """
    if user["role"] != "super_admin" and user["company_id"] != company_id:
        raise HTTPException(status_code=403, detail="Forbidden: not your company")

    db = get_db()
    db.table("company_ai_config").delete().eq("company_id", company_id).execute()

    return {"status": "deleted", "company_id": company_id}
