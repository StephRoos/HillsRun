"""HTTP client for the HillsRun REST API."""

import os
from typing import Any, Dict, List, Optional

import requests

API_BASE_URL = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000")
API_KEY = os.environ.get("API_KEY", "")


def _headers() -> Dict[str, str]:
    return {"X-API-Key": API_KEY}


def _url(path: str) -> str:
    return f"{API_BASE_URL}{path}"


def _get(path: str, params: Optional[Dict] = None) -> Dict[str, Any]:
    resp = requests.get(_url(path), headers=_headers(), params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _post(path: str, json: Optional[Dict] = None) -> Dict[str, Any]:
    resp = requests.post(_url(path), headers=_headers(), json=json, timeout=30)
    resp.raise_for_status()
    return resp.json()


# --- Sync endpoints ---

def get_sync_status() -> List[Dict]:
    """Get sync status for all categories."""
    return _get("/api/v1/sync/status")["data"]


def trigger_sync(
    categories: Optional[List[str]] = None,
    mode: str = "incremental",
    days_back: int = 90,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    dry_run: bool = False,
) -> Dict:
    """Trigger a sync job. Returns {job_id, message}."""
    body = {"mode": mode, "days_back": days_back, "dry_run": dry_run}
    if categories:
        body["categories"] = categories
    if start_date:
        body["start_date"] = start_date
    if end_date:
        body["end_date"] = end_date
    return _post("/api/v1/sync/trigger", json=body)


def get_job(job_id: str) -> Dict:
    """Get a specific sync job by ID."""
    return _get(f"/api/v1/sync/jobs/{job_id}")


def list_jobs(limit: int = 10) -> List[Dict]:
    """List recent sync jobs."""
    return _get("/api/v1/sync/jobs", params={"limit": limit})


# --- Data endpoints ---


def _date_params(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 50,
    **extra: Any,
) -> Dict[str, Any]:
    """Build common query params for data endpoints."""
    params: Dict[str, Any] = {"limit": limit}
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    params.update({k: v for k, v in extra.items() if v is not None})
    return params


# Daily health

def get_daily_summary(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 50,
) -> List[Dict]:
    """Get daily summary data."""
    params = _date_params(start_date, end_date, limit)
    return _get("/api/v1/daily/summary", params=params)["data"]


def get_sleep_data(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 50,
) -> List[Dict]:
    """Get sleep data."""
    params = _date_params(start_date, end_date, limit)
    return _get("/api/v1/daily/sleep", params=params)["data"]


def get_stress_data(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 50,
) -> List[Dict]:
    """Get stress data."""
    params = _date_params(start_date, end_date, limit)
    return _get("/api/v1/daily/stress", params=params)["data"]


def get_body_battery(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 50,
) -> List[Dict]:
    """Get body battery data."""
    params = _date_params(start_date, end_date, limit)
    return _get("/api/v1/daily/body-battery", params=params)["data"]


def get_heart_rate(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 200,
) -> List[Dict]:
    """Get heart rate samples."""
    params = _date_params(start_date, end_date, limit)
    return _get("/api/v1/daily/heart-rate", params=params)["data"]


# Body & metrics

def get_body_composition(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 50,
) -> List[Dict]:
    """Get body composition data."""
    params = _date_params(start_date, end_date, limit)
    return _get("/api/v1/body/composition", params=params)["data"]


def get_hrv_data(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 50,
) -> List[Dict]:
    """Get HRV data."""
    params = _date_params(start_date, end_date, limit)
    return _get("/api/v1/metrics/hrv", params=params)["data"]


def get_training_readiness(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 50,
) -> List[Dict]:
    """Get training readiness data."""
    params = _date_params(start_date, end_date, limit)
    return _get("/api/v1/metrics/training-readiness", params=params)["data"]


def get_fitness_metrics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 50,
) -> List[Dict]:
    """Get fitness metrics (VO2max, lactate threshold, etc.)."""
    params = _date_params(start_date, end_date, limit)
    return _get("/api/v1/metrics/fitness", params=params)["data"]


# Activities

def get_activities(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 50,
    sport_type: Optional[str] = None,
) -> List[Dict]:
    """Get activities list."""
    params = _date_params(start_date, end_date, limit, sport_type=sport_type)
    return _get("/api/v1/activities", params=params)["data"]


def get_activity(activity_id: int) -> Dict:
    """Get a single activity detail."""
    return _get(f"/api/v1/activities/{activity_id}")["data"]


# --- Health ---

def health_check() -> Dict:
    """Check API health (no auth required)."""
    resp = requests.get(_url("/health"), timeout=5)
    resp.raise_for_status()
    return resp.json()
