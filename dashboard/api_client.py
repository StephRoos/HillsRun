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


# --- Health ---

def health_check() -> Dict:
    """Check API health (no auth required)."""
    resp = requests.get(_url("/health"), timeout=5)
    resp.raise_for_status()
    return resp.json()
