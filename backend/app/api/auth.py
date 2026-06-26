"""
Integra — JWT Verification (ES256 asymmetric via JWKS)
Supabase projects now use ECC P-256 signing keys by default.
Verification is done via the JWKS endpoint — no more single HS256 secret.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from jwt import PyJWKClient, ExpiredSignatureError, InvalidTokenError

from app.core.config import settings

router = APIRouter()

# ── Global JWKS client (singleton, lifetime of the process) ─────
# PyJWKClient handles:
#   - Tier 1 cache: entire JWKS response, TTL 300s (default)
#   - Tier 2 cache: signing keys by kid (LRU, up to max_cached_keys)
#   - Multiple keys: JWKS array with different kid values
#     for smooth key rotation (current key + previous key)

_jwks_client: Optional[PyJWKClient] = None


def get_jwks_client() -> PyJWKClient:
    """Return the cached JWKS client. Refreshes automatically every 300s."""
    global _jwks_client
    if _jwks_client is None:
        if not settings.SUPABASE_JWKS_URL:
            raise RuntimeError("SUPABASE_JWKS_URL is not configured")
        _jwks_client = PyJWKClient(
            settings.SUPABASE_JWKS_URL,
            cache_keys=True,       # Cache individual signing keys (LRU)
            max_cached_keys=5,     # Current + up to 4 previous keys during rotation
            lifespan=300,          # Refresh JWKS every 5 minutes (default)
        )
    return _jwks_client


async def verify_jwt(authorization: Optional[str] = Header(None)):
    """
    Verify Supabase JWT (ES256) against the JWKS endpoint.

    Returns a dict with user info extracted from the JWT claims:
      - user_id (sub claim)
      - email
      - role (Supabase app_metadata.role)
      - company_id (custom claim, set in app_users.company_id)

    Raises 401 on missing/invalid/expired tokens.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid authorization header",
        )

    token = authorization.replace("Bearer ", "")

    try:
        client = get_jwks_client()

        # Step 1: resolve the signing key
        #   - Extracts `kid` from JWT header
        #   - Looks up matching key in the cached JWKS
        #   - If JWKS cache expired, fetches fresh and retries
        signing_key = client.get_signing_key_from_jwt(token)

        # Step 2: verify the token with the resolved public key
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256"],
            options={"verify_aud": False},  # Supabase doesn't set aud
        )

        # Extract claims — Supabase JWT structure
        user_metadata = payload.get("user_metadata", {})
        app_metadata = payload.get("app_metadata", {})

        return {
            "user_id": payload.get("sub"),
            "email": payload.get("email", user_metadata.get("email")),
            "role": app_metadata.get("role", user_metadata.get("role")),
            "company_id": user_metadata.get("company_id"),
        }

    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"JWKS configuration error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication error: {str(e)}")


@router.get("/auth/me")
async def get_current_user(user: dict = Depends(verify_jwt)):
    """Health-check endpoint: return the decoded user from the JWT."""
    return {"user": user}
