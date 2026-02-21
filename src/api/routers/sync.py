"""Sync status and trigger endpoints."""

import asyncio
import logging
import threading
import uuid
from collections import OrderedDict
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from ..auth import get_api_key
from ..dependencies import get_db, get_user_id
from ..schemas import (
    SyncJobResponse,
    SyncJobStatus,
    SyncStatus,
    SyncTriggerRequest,
    SyncTriggerResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/sync", tags=["sync"], dependencies=[Depends(get_api_key)])

# In-memory job store (OrderedDict to maintain insertion order, capped at 50)
MAX_JOBS = 50
_jobs: OrderedDict[str, SyncJobResponse] = OrderedDict()
_jobs_lock = threading.Lock()


class _JobLogHandler(logging.Handler):
    """Captures log records into a job's log list."""

    def __init__(self, job: SyncJobResponse):
        super().__init__()
        self.job = job

    def emit(self, record: logging.LogRecord):
        try:
            msg = self.format(record)
            self.job.logs.append(msg)
        except Exception:
            pass


def _store_job(job: SyncJobResponse) -> None:
    with _jobs_lock:
        _jobs[job.job_id] = job
        while len(_jobs) > MAX_JOBS:
            _jobs.popitem(last=False)


def _run_sync_in_thread(job: SyncJobResponse, target_user_id: Optional[int] = None) -> None:
    """Run sync in a separate thread with its own event loop.

    garminconnect/garth use synchronous HTTP calls that block the event loop.
    Running in a thread prevents blocking FastAPI's main event loop.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_run_sync(job, target_user_id))
    except Exception as e:
        logger.exception(f"Sync thread failed for user_id={target_user_id}")
        job.status = SyncJobStatus.failed
        job.error = str(e)
        job.finished_at = datetime.now(timezone.utc)
    finally:
        loop.close()


async def _run_sync(job: SyncJobResponse, target_user_id: Optional[int] = None) -> None:
    """Execute sync and update job status."""
    from ...config import Config
    from ...sync_manager import SyncManager

    # Attach a log handler to capture sync logs for this job
    handler = _JobLogHandler(job)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root_logger = logging.getLogger("src")
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(handler)

    try:
        job.status = SyncJobStatus.running
        job.started_at = datetime.now(timezone.utc)

        config = Config.from_env()
        manager = SyncManager(config)
        await manager.initialize(user_id=target_user_id)

        try:
            req = job.request
            report = await manager.sync(
                categories=req.categories,
                mode=req.mode,
                days_back=req.days_back,
                start_date=req.start_date,
                end_date=req.end_date,
                dry_run=req.dry_run,
            )
            job.result = report
            job.status = SyncJobStatus.completed
        finally:
            await manager.cleanup()

    except Exception as e:
        logger.exception(f"Sync job {job.job_id} failed")
        job.status = SyncJobStatus.failed
        job.error = str(e)
    finally:
        job.finished_at = datetime.now(timezone.utc)
        root_logger.removeHandler(handler)


@router.get("/status")
async def sync_status(
    db=Depends(get_db),
    user_id: int = Depends(get_user_id),
):
    rows = await db.query_sync_status(user_id=user_id)
    return {"data": [SyncStatus.model_validate(dict(r)) for r in rows]}


@router.post("/trigger", response_model=SyncTriggerResponse)
async def trigger_sync(
    request: SyncTriggerRequest,
    raw_request: Request,
    db=Depends(get_db),
):
    """Trigger an async sync job. Returns a job_id for polling."""
    # Resolve target user: body better_auth_user_id > X-Garmin-User-Id header > legacy singleton
    target_user_id: Optional[int] = None

    if request.better_auth_user_id:
        target_user_id = await db.get_user_by_better_auth_id(request.better_auth_user_id)
        if target_user_id is None:
            raise HTTPException(status_code=404, detail="No Garmin account linked to this user")
    else:
        # Fallback: read X-Garmin-User-Id header (set by Next.js proxy)
        header_value = raw_request.headers.get("X-Garmin-User-Id")
        if header_value:
            try:
                target_user_id = int(header_value)
            except ValueError:
                pass

    # Anti-flood: check if there's already a running job for this user
    with _jobs_lock:
        for j in _jobs.values():
            if j.status in (SyncJobStatus.pending, SyncJobStatus.running):
                # Per-user anti-flood: if we know the target, only block same user
                if target_user_id is not None:
                    if getattr(j, '_target_user_id', None) == target_user_id:
                        raise HTTPException(
                            status_code=409,
                            detail=f"A sync job is already running for this user (job_id={j.job_id})",
                        )
                else:
                    # Legacy mode: block any running job
                    raise HTTPException(
                        status_code=409,
                        detail=f"A sync job is already running (job_id={j.job_id})",
                    )

    # Validate categories
    valid_categories = {"daily_health", "activities", "body_composition", "advanced_metrics", "wellness"}
    if request.categories:
        invalid = set(request.categories) - valid_categories
        if invalid:
            raise HTTPException(status_code=400, detail=f"Invalid categories: {invalid}")

    job = SyncJobResponse(
        job_id=str(uuid.uuid4()),
        status=SyncJobStatus.pending,
        created_at=datetime.now(timezone.utc),
        request=request,
    )
    job._target_user_id = target_user_id  # type: ignore[attr-defined]
    _store_job(job)

    thread = threading.Thread(target=_run_sync_in_thread, args=(job, target_user_id), daemon=True)
    thread.start()

    return SyncTriggerResponse(job_id=job.job_id, message="Sync job started")


@router.get("/jobs", response_model=List[SyncJobResponse])
async def list_jobs(limit: int = 10):
    """List the most recent sync jobs."""
    jobs = list(reversed(_jobs.values()))
    return jobs[:limit]


@router.get("/jobs/{job_id}", response_model=SyncJobResponse)
async def get_job(job_id: str):
    """Get status and logs for a specific sync job."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
