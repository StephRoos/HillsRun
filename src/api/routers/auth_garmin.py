"""Garmin account connection endpoints (connect/status/disconnect)."""

import logging
import os
import uuid
import time
from typing import Optional, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from garminconnect import Garmin, GarminConnectAuthenticationError
import garth

from ..auth import get_api_key
from ..dependencies import get_db
from ...token_manager import TokenManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth_garmin"], dependencies=[Depends(get_api_key)])

# Temporary in-memory store for pending MFA sessions (TTL: 5 minutes)
_mfa_sessions: dict[str, dict[str, Any]] = {}
_MFA_TTL = 300


def _cleanup_expired_mfa():
    now = time.time()
    expired = [k for k, v in _mfa_sessions.items() if now - v["created"] > _MFA_TTL]
    for k in expired:
        del _mfa_sessions[k]


class ConnectRequest(BaseModel):
    email: str
    password: str
    better_auth_user_id: str


class ConnectResponse(BaseModel):
    connected: bool
    needs_mfa: bool = False
    mfa_session_id: Optional[str] = None
    garmin_display_name: Optional[str] = None
    user_id: Optional[int] = None


class MfaRequest(BaseModel):
    mfa_session_id: str
    mfa_code: str
    better_auth_user_id: str


class StatusResponse(BaseModel):
    connected: bool
    garmin_display_name: Optional[str] = None
    user_id: Optional[int] = None
    last_sync: Optional[str] = None


class DisconnectRequest(BaseModel):
    better_auth_user_id: str


async def _finalize_connect(garmin_client: Garmin, request_email: str, better_auth_user_id: str, db) -> ConnectResponse:
    """Extract tokens from authenticated Garmin client, store in DB, return response."""
    token_key = os.environ.get("GARMIN_TOKEN_KEY", "")

    display_name = garmin_client.display_name or garmin_client.full_name
    garmin_user_id = str(display_name or request_email)

    token_data = garmin_client.garth.dumps()
    tm = TokenManager(token_key)
    encrypted = tm.encrypt(token_data)

    try:
        user_id = await db.get_or_create_user_with_link(
            garmin_user_id=garmin_user_id,
            better_auth_user_id=better_auth_user_id,
            display_name=display_name,
            email=request_email,
        )
    except Exception as e:
        logger.exception("Failed to link Garmin account in database")
        raise HTTPException(status_code=500, detail=f"Failed to link Garmin account: {e}")

    await db.store_encrypted_tokens(user_id, encrypted)
    logger.info(f"Garmin account connected for better_auth_user={better_auth_user_id}, garmin_user_id={user_id}")

    return ConnectResponse(
        connected=True,
        garmin_display_name=display_name,
        user_id=user_id,
    )


@router.post("/connect", response_model=ConnectResponse)
async def connect_garmin(request: ConnectRequest, db=Depends(get_db)):
    """Authenticate with Garmin Connect, store encrypted tokens, link to Better-Auth user."""
    token_key = os.environ.get("GARMIN_TOKEN_KEY", "")
    if not token_key:
        raise HTTPException(status_code=500, detail="Token encryption not configured")

    # Check if this Better-Auth user already has a linked Garmin account
    existing = await db.get_user_by_better_auth_id(request.better_auth_user_id)
    if existing:
        existing_info = await db.get_user_info(existing)
        if existing_info and existing_info.get("encrypted_tokens"):
            return ConnectResponse(
                connected=True,
                garmin_display_name=existing_info.get("display_name"),
                user_id=existing,
            )
        # Link exists but no tokens — clean up before re-connecting
        await db.unlink_better_auth_user(existing)

    # Authenticate with Garmin (MFA-aware)
    try:
        garmin_client = Garmin(request.email, request.password, return_on_mfa=True)
        result = garmin_client.login()
    except GarminConnectAuthenticationError as e:
        raise HTTPException(status_code=401, detail=f"Garmin authentication failed: {e}")
    except Exception as e:
        logger.exception("Garmin login error")
        raise HTTPException(status_code=502, detail=f"Failed to connect to Garmin: {e}")

    # Check if MFA is required
    if isinstance(result, tuple) and len(result) == 2 and result[0] == "needs_mfa":
        _cleanup_expired_mfa()
        session_id = str(uuid.uuid4())
        _mfa_sessions[session_id] = {
            "client_state": result[1],
            "email": request.email,
            "better_auth_user_id": request.better_auth_user_id,
            "garmin_client": garmin_client,
            "created": time.time(),
        }
        logger.info(f"MFA required for {request.email}, session_id={session_id}")
        return ConnectResponse(connected=False, needs_mfa=True, mfa_session_id=session_id)

    # No MFA — finalize
    return await _finalize_connect(garmin_client, request.email, request.better_auth_user_id, db)


@router.post("/connect/mfa", response_model=ConnectResponse)
async def connect_garmin_mfa(request: MfaRequest, db=Depends(get_db)):
    """Complete Garmin Connect login with MFA code."""
    token_key = os.environ.get("GARMIN_TOKEN_KEY", "")
    if not token_key:
        raise HTTPException(status_code=500, detail="Token encryption not configured")

    _cleanup_expired_mfa()
    session = _mfa_sessions.pop(request.mfa_session_id, None)
    if not session:
        raise HTTPException(status_code=400, detail="MFA session expired or invalid — please restart connection")

    if session["better_auth_user_id"] != request.better_auth_user_id:
        raise HTTPException(status_code=403, detail="MFA session does not match user")

    try:
        oauth1, oauth2 = garth.sso.resume_login(session["client_state"], request.mfa_code)
    except Exception as e:
        logger.exception("MFA verification failed")
        raise HTTPException(status_code=401, detail=f"MFA verification failed: {e}")

    garmin_client = session["garmin_client"]
    # Set the real OAuth tokens (login() with return_on_mfa stored intermediate state)
    garmin_client.garth.oauth1_token = oauth1
    garmin_client.garth.oauth2_token = oauth2

    # Load profile after MFA completion
    try:
        prof = garmin_client.garth.connectapi(
            "/userprofile-service/usersettings"
        )
        garmin_client.display_name = prof.get("displayName")
        garmin_client.full_name = prof.get("fullName") or prof.get("displayName")
    except Exception:
        logger.warning("Could not load Garmin profile after MFA")

    return await _finalize_connect(garmin_client, session["email"], request.better_auth_user_id, db)


@router.get("/status", response_model=StatusResponse)
async def garmin_status(better_auth_user_id: str, db=Depends(get_db)):
    """Check if a Better-Auth user has a connected Garmin account."""
    user_id = await db.get_user_by_better_auth_id(better_auth_user_id)
    if not user_id:
        return StatusResponse(connected=False)

    info = await db.get_user_info(user_id)
    if not info or not info.get("encrypted_tokens"):
        return StatusResponse(connected=False, user_id=user_id)

    # Get last sync timestamp
    last_sync = None
    rows = await db.query_sync_status(user_id=user_id)
    if rows:
        timestamps = [r["last_sync_timestamp"] for r in rows if r.get("last_sync_timestamp")]
        if timestamps:
            last_sync = max(timestamps).isoformat()

    return StatusResponse(
        connected=True,
        garmin_display_name=info.get("display_name"),
        user_id=user_id,
        last_sync=last_sync,
    )


@router.post("/disconnect")
async def disconnect_garmin(request: DisconnectRequest, db=Depends(get_db)):
    """Disconnect a Garmin account from a Better-Auth user."""
    user_id = await db.get_user_by_better_auth_id(request.better_auth_user_id)
    if not user_id:
        raise HTTPException(status_code=404, detail="No Garmin account linked")

    await db.unlink_better_auth_user(user_id)
    logger.info(f"Garmin account disconnected for better_auth_user={request.better_auth_user_id}")

    return {"disconnected": True}
