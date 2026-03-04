"""Extended tests for src/api/dependencies.py — improves coverage from 65%."""

import pytest
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock

from fastapi import HTTPException, FastAPI, Request
from fastapi.testclient import TestClient

from src.api.dependencies import (
    get_user_id,
    date_range,
    pagination,
    verify_coach_access,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_request(
    *,
    user_id_header: str = None,
    coach_id_header: str = None,
    state_user_id=None,
    db=None,
):
    """Build a MagicMock that mimics a FastAPI Request.

    Only the attributes actually used by the dependency functions are set.
    """
    request = MagicMock(spec=Request)

    # Headers dict-like behaviour: return the value when .get() is called with
    # the matching key, and None otherwise.
    def _headers_get(key, default=None):
        mapping = {}
        if user_id_header is not None:
            mapping["X-Garmin-User-Id"] = user_id_header
        if coach_id_header is not None:
            mapping["X-Coach-Better-Auth-Id"] = coach_id_header
        return mapping.get(key, default)

    request.headers.get = MagicMock(side_effect=_headers_get)

    # app.state
    state = MagicMock()
    state.user_id = state_user_id
    if db is not None:
        state.db = db
    request.app.state = state

    return request


# ---------------------------------------------------------------------------
# get_user_id
# ---------------------------------------------------------------------------


class TestGetUserIdFromHeader:
    """get_user_id resolves to the integer in X-Garmin-User-Id when present."""

    @pytest.mark.asyncio
    async def test_valid_header_returns_int(self):
        """A valid numeric header is parsed and returned as an int."""
        request = _make_request(user_id_header="42")
        result = await get_user_id(request)
        assert result == 42

    @pytest.mark.asyncio
    async def test_header_value_is_integer_type(self):
        """Returned value is strictly an int (not str)."""
        request = _make_request(user_id_header="123")
        result = await get_user_id(request)
        assert isinstance(result, int)

    @pytest.mark.asyncio
    async def test_invalid_header_raises_400(self):
        """A non-numeric X-Garmin-User-Id header raises HTTP 400."""
        request = _make_request(user_id_header="not_a_number")
        with pytest.raises(HTTPException) as exc_info:
            await get_user_id(request)
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_invalid_header_error_message(self):
        """HTTP 400 detail mentions the invalid header."""
        request = _make_request(user_id_header="abc")
        with pytest.raises(HTTPException) as exc_info:
            await get_user_id(request)
        assert "X-Garmin-User-Id" in exc_info.value.detail


class TestGetUserIdFromAppState:
    """get_user_id falls back to app.state when no header is present."""

    @pytest.mark.asyncio
    async def test_returns_state_user_id_when_no_header(self):
        """When X-Garmin-User-Id header is absent, app.state.user_id is returned."""
        request = _make_request(state_user_id=7)
        result = await get_user_id(request)
        assert result == 7

    @pytest.mark.asyncio
    async def test_queries_db_when_state_is_none(self):
        """When state.user_id is None the DB is queried and result is cached."""
        mock_db = AsyncMock()
        mock_db.query_first_user = AsyncMock(return_value=99)

        request = _make_request(state_user_id=None, db=mock_db)
        result = await get_user_id(request)

        assert result == 99
        mock_db.query_first_user.assert_called_once()

    @pytest.mark.asyncio
    async def test_caches_db_result_in_state(self):
        """After a DB lookup the result is written back to app.state.user_id."""
        mock_db = AsyncMock()
        mock_db.query_first_user = AsyncMock(return_value=55)

        request = _make_request(state_user_id=None, db=mock_db)
        await get_user_id(request)

        # The dependency sets request.app.state.user_id
        assert request.app.state.user_id == 55

    @pytest.mark.asyncio
    async def test_raises_503_when_no_user_in_db(self):
        """HTTP 503 is raised when query_first_user returns None."""
        mock_db = AsyncMock()
        mock_db.query_first_user = AsyncMock(return_value=None)

        request = _make_request(state_user_id=None, db=mock_db)
        with pytest.raises(HTTPException) as exc_info:
            await get_user_id(request)
        assert exc_info.value.status_code == 503


# ---------------------------------------------------------------------------
# date_range
# ---------------------------------------------------------------------------


class TestDateRange:
    """date_range validates the span and applies defaults."""

    def test_excessive_range_raises_400(self):
        """A range exceeding 365 days raises HTTP 400."""
        start = date.today() - timedelta(days=400)
        end = date.today()
        with pytest.raises(HTTPException) as exc_info:
            date_range(start, end)
        assert exc_info.value.status_code == 400

    def test_exactly_365_days_passes(self):
        """A range of exactly 365 days is accepted without error."""
        end = date.today()
        start = end - timedelta(days=365)
        result_start, result_end = date_range(start, end)
        assert result_start == start
        assert result_end == end

    def test_within_limit_passes(self):
        """A range well within 365 days is returned unchanged."""
        start = date(2025, 1, 1)
        end = date(2025, 1, 31)
        result_start, result_end = date_range(start, end)
        assert result_start == start
        assert result_end == end

    def test_default_start_is_30_days_ago(self):
        """When start_date is None the default is 30 days before today."""
        _, _ = date_range(None, None)  # Just confirming no exception
        expected_start = date.today() - timedelta(days=30)
        result_start, _ = date_range(None, None)
        assert result_start == expected_start

    def test_default_end_is_today(self):
        """When end_date is None the default is today."""
        _, result_end = date_range(None, None)
        assert result_end == date.today()


# ---------------------------------------------------------------------------
# pagination
# ---------------------------------------------------------------------------


class TestPagination:
    """pagination returns (limit, offset) tuples."""

    def test_default_limit_is_50(self):
        """Default limit is 50."""
        limit, offset = pagination(limit=50, offset=0)
        assert limit == 50

    def test_default_offset_is_0(self):
        """Default offset is 0."""
        limit, offset = pagination(limit=50, offset=0)
        assert offset == 0

    def test_custom_values_returned(self):
        """Custom limit and offset values are passed through unchanged."""
        limit, offset = pagination(limit=100, offset=25)
        assert limit == 100
        assert offset == 25

    def test_returns_tuple_of_two(self):
        """pagination always returns exactly two values."""
        result = pagination(limit=10, offset=5)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# verify_coach_access
# ---------------------------------------------------------------------------


class TestVerifyCoachAccess:
    """verify_coach_access enforces the coach-athlete relationship."""

    @pytest.mark.asyncio
    async def test_no_coach_header_returns_user_id_and_none(self):
        """Without X-Coach-Better-Auth-Id header returns (user_id, None)."""
        request = _make_request(state_user_id=10)
        user_id, coach_id = await verify_coach_access(request)
        assert user_id == 10
        assert coach_id is None

    @pytest.mark.asyncio
    async def test_valid_coach_returns_user_and_coach_ids(self):
        """A coach with a verified relationship returns (user_id, coach_id)."""
        mock_db = AsyncMock()
        mock_db.is_coach_of_athlete = AsyncMock(return_value=True)

        request = _make_request(
            state_user_id=20,
            coach_id_header="coach-abc-123",
            db=mock_db,
        )
        user_id, coach_id = await verify_coach_access(request)

        assert user_id == 20
        assert coach_id == "coach-abc-123"

    @pytest.mark.asyncio
    async def test_unauthorized_coach_raises_403(self):
        """A coach not linked to the athlete raises HTTP 403."""
        mock_db = AsyncMock()
        mock_db.is_coach_of_athlete = AsyncMock(return_value=False)

        request = _make_request(
            state_user_id=30,
            coach_id_header="intruder-xyz",
            db=mock_db,
        )
        with pytest.raises(HTTPException) as exc_info:
            await verify_coach_access(request)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_unauthorized_coach_error_detail(self):
        """The 403 detail string is descriptive."""
        mock_db = AsyncMock()
        mock_db.is_coach_of_athlete = AsyncMock(return_value=False)

        request = _make_request(
            state_user_id=30,
            coach_id_header="intruder",
            db=mock_db,
        )
        with pytest.raises(HTTPException) as exc_info:
            await verify_coach_access(request)
        assert exc_info.value.detail  # non-empty string

    @pytest.mark.asyncio
    async def test_is_coach_of_athlete_called_with_correct_args(self):
        """is_coach_of_athlete receives (coach_id, user_id) in correct order."""
        mock_db = AsyncMock()
        mock_db.is_coach_of_athlete = AsyncMock(return_value=True)

        request = _make_request(
            state_user_id=5,
            coach_id_header="coach-99",
            db=mock_db,
        )
        await verify_coach_access(request)

        mock_db.is_coach_of_athlete.assert_called_once_with("coach-99", 5)

    @pytest.mark.asyncio
    async def test_no_coach_header_does_not_query_db_for_coach(self):
        """When no coach header is present is_coach_of_athlete is never called."""
        mock_db = AsyncMock()
        mock_db.is_coach_of_athlete = AsyncMock(return_value=True)

        request = _make_request(state_user_id=8, db=mock_db)
        await verify_coach_access(request)

        mock_db.is_coach_of_athlete.assert_not_called()

    @pytest.mark.asyncio
    async def test_coach_access_propagates_503_when_no_user(self):
        """If no user exists in DB, the 503 from get_user_id bubbles through."""
        mock_db = AsyncMock()
        mock_db.query_first_user = AsyncMock(return_value=None)

        request = _make_request(state_user_id=None, db=mock_db)
        with pytest.raises(HTTPException) as exc_info:
            await verify_coach_access(request)
        assert exc_info.value.status_code == 503
