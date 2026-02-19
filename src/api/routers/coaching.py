"""Coaching endpoints: invite codes, athlete linking, access check."""

import secrets
import string
from fastapi import APIRouter, Depends, HTTPException, Request, status
from ..auth import get_api_key
from ..dependencies import get_db, get_user_id
from ..schemas import (
    InviteCodeResponse,
    RedeemCodeRequest,
    CoachAthlete,
    CoachInfo,
    CoachingStatus,
)

router = APIRouter(
    prefix="/api/v1/coaching",
    tags=["coaching"],
    dependencies=[Depends(get_api_key)],
)


def _generate_code(length: int = 8) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _get_better_auth_id(request: Request) -> str:
    value = request.headers.get("X-Better-Auth-User-Id")
    if not value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-Better-Auth-User-Id header required")
    return value


@router.post("/invite-codes", status_code=status.HTTP_201_CREATED)
async def create_invite_code(
    request: Request,
    db=Depends(get_db),
):
    coach_id = _get_better_auth_id(request)
    # Auto-enable coaching on first invite code generation
    await db.enable_coaching(coach_id)
    code = _generate_code()
    row = await db.create_invite_code(coach_id, code)
    return InviteCodeResponse.model_validate(row)


@router.get("/invite-codes")
async def list_invite_codes(
    request: Request,
    db=Depends(get_db),
):
    coach_id = _get_better_auth_id(request)
    rows = await db.get_invite_codes_for_coach(coach_id)
    return [InviteCodeResponse.model_validate(r) for r in rows]


@router.delete("/invite-codes/{code}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_invite_code(
    code: str,
    request: Request,
    db=Depends(get_db),
):
    coach_id = _get_better_auth_id(request)
    revoked = await db.revoke_invite_code(code, coach_id)
    if not revoked:
        raise HTTPException(status_code=404, detail="Invite code not found or already used")


@router.post("/redeem")
async def redeem_invite_code(
    body: RedeemCodeRequest,
    db=Depends(get_db),
    user_id: int = Depends(get_user_id),
):
    result = await db.redeem_invite_code(body.code, user_id)
    if not result:
        raise HTTPException(status_code=400, detail="Invalid, expired, or already redeemed invite code")
    return {"message": "Successfully linked to coach", "coach_better_auth_id": result["coach_better_auth_id"]}


@router.get("/athletes")
async def list_athletes(
    request: Request,
    db=Depends(get_db),
):
    coach_id = _get_better_auth_id(request)
    rows = await db.get_athletes_for_coach(coach_id)
    return [CoachAthlete.model_validate(r) for r in rows]


@router.delete("/athletes/{athlete_user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_athlete(
    athlete_user_id: int,
    request: Request,
    db=Depends(get_db),
):
    coach_id = _get_better_auth_id(request)
    removed = await db.unlink_coach_athlete(coach_id, athlete_user_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Athlete link not found")


@router.get("/coaches")
async def list_coaches(
    db=Depends(get_db),
    user_id: int = Depends(get_user_id),
):
    rows = await db.get_coaches_for_athlete(user_id)
    return [CoachInfo.model_validate(r) for r in rows]


@router.delete("/coaches/{coach_better_auth_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_coach(
    coach_better_auth_id: str,
    db=Depends(get_db),
    user_id: int = Depends(get_user_id),
):
    removed = await db.unlink_coach_athlete(coach_better_auth_id, user_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Coach link not found")


@router.get("/check-access")
async def check_access(
    athlete_user_id: int,
    request: Request,
    db=Depends(get_db),
):
    coach_id = _get_better_auth_id(request)
    has_access = await db.is_coach_of_athlete(coach_id, athlete_user_id)
    return {"has_access": has_access}


@router.get("/status")
async def coaching_status(
    request: Request,
    db=Depends(get_db),
    user_id: int = Depends(get_user_id),
):
    better_auth_id = _get_better_auth_id(request)
    enabled = await db.get_coaching_enabled(better_auth_id)
    athletes = await db.get_athletes_for_coach(better_auth_id)
    coaches = await db.get_coaches_for_athlete(user_id)
    return CoachingStatus(
        coaching_enabled=enabled,
        athletes=[CoachAthlete.model_validate(a) for a in athletes],
        coaches=[CoachInfo.model_validate(c) for c in coaches],
    )
