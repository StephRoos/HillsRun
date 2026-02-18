"""Shared FastAPI dependencies."""

from datetime import date, timedelta
from typing import Optional
from fastapi import Query, HTTPException, status, Request


def get_db(request: Request):
    return request.app.state.db


async def get_user_id(request: Request) -> int:
    """Resolve user_id: X-Garmin-User-Id header takes priority, then singleton fallback."""
    header_value = request.headers.get("X-Garmin-User-Id")
    if header_value:
        try:
            return int(header_value)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid X-Garmin-User-Id header")

    # Fallback: singleton user (backward compat for Streamlit dashboard, direct API)
    user_id = request.app.state.user_id
    if user_id is None:
        db = request.app.state.db
        user_id = await db.query_first_user()
        if user_id is not None:
            request.app.state.user_id = user_id
        else:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="No user found in database")
    return user_id


def date_range(
    start_date: Optional[date] = Query(default=None, description="Start date (default: 30 days ago)"),
    end_date: Optional[date] = Query(default=None, description="End date (default: today)"),
):
    today = date.today()
    return (
        start_date or today - timedelta(days=30),
        end_date or today,
    )


def pagination(
    limit: int = Query(default=50, ge=1, le=200, description="Max results per page"),
    offset: int = Query(default=0, ge=0, description="Number of results to skip"),
):
    return limit, offset
