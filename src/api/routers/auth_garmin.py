"""Garmin account connection endpoints (connect/status/disconnect)."""

import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from garminconnect import Garmin, GarminConnectAuthenticationError
import garth

from ..auth import get_api_key
from ..dependencies import get_db
from ...token_manager import TokenManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth_garmin"], dependencies=[Depends(get_api_key)])


class ConnectRequest(BaseModel):
    email: str
    password: str
    better_auth_user_id: str


class ConnectResponse(BaseModel):
    connected: bool
    garmin_display_name: Optional[str] = None
    user_id: Optional[int] = None


class StatusResponse(BaseModel):
    connected: bool
    garmin_display_name: Optional[str] = None
    user_id: Optional[int] = None
    last_sync: Optional[str] = None


class DisconnectRequest(BaseModel):
    better_auth_user_id: str


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
        # Link exists but no tokens (partial state from a previous failed connect).
        # Clean up so the re-connect can proceed cleanly.
        await db.unlink_better_auth_user(existing)

    # Authenticate with Garmin
    try:
        garmin_client = Garmin(request.email, request.password)
        garmin_client.login()
    except GarminConnectAuthenticationError as e:
        raise HTTPException(status_code=401, detail=f"Garmin authentication failed: {e}")
    except Exception as e:
        logger.exception("Garmin login error")
        raise HTTPException(status_code=502, detail=f"Failed to connect to Garmin: {e}")

    # Extract profile info
    display_name = garmin_client.display_name or garmin_client.full_name
    garmin_user_id = str(display_name or request.email)

    # Serialize and encrypt tokens
    token_data = garmin_client.garth.dumps()
    tm = TokenManager(token_key)
    encrypted = tm.encrypt(token_data)

    # Create/link user (clears stale links in a transaction to handle account switching)
    try:
        user_id = await db.get_or_create_user_with_link(
            garmin_user_id=garmin_user_id,
            better_auth_user_id=request.better_auth_user_id,
            display_name=display_name,
            email=request.email,
        )
    except Exception as e:
        logger.exception("Failed to link Garmin account in database")
        raise HTTPException(status_code=500, detail=f"Failed to link Garmin account: {e}")

    # Store encrypted tokens
    await db.store_encrypted_tokens(user_id, encrypted)

    logger.info(f"Garmin account connected for better_auth_user={request.better_auth_user_id}, garmin_user_id={user_id}")

    return ConnectResponse(
        connected=True,
        garmin_display_name=display_name,
        user_id=user_id,
    )


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
