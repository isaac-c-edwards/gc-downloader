"""Regression tests for the bounded-concurrency job scheduler.

These lock in the Tier-1 scalability fix: many jobs may run concurrently
(bounded by a semaphore, not a single global mutex), extra jobs queue with a
reported position, and the server rejects work once the queue is saturated.
"""

from __future__ import annotations

import asyncio
import time

import pytest

import app.jobs as jobs
from app.config import settings
from app.errors import ServerBusy
from app.jobs import Job, ensure_capacity, queue_position


@pytest.fixture(autouse=True)
def _clear_jobs():
    jobs._jobs.clear()
    yield
    jobs._jobs.clear()


def _make(state: str, order: float) -> Job:
    # created_at must be recent so _evict_old() (TTL-based) doesn't drop it.
    job = Job(job_id=f"job-{order}", request=None, total=1)  # type: ignore[arg-type]
    job.state = state
    job.created_at = time.time() + order
    jobs._jobs[job.job_id] = job
    return job


def test_scheduler_is_bounded_not_serialized():
    """The scheduler allows several jobs at once, not one-at-a-time."""
    assert settings.max_concurrent_jobs >= 1
    assert jobs._job_semaphore._value == settings.max_concurrent_jobs
    # A value > 1 is what lets multiple users be served in parallel.
    assert settings.max_concurrent_jobs > 1


def test_ensure_capacity_rejects_when_saturated():
    for i in range(settings.max_queued_jobs):
        _make("queued", order=float(i))
    with pytest.raises(ServerBusy):
        ensure_capacity()


def test_ensure_capacity_ignores_finished_jobs():
    # Done/error jobs don't count against the live capacity budget.
    for i in range(settings.max_queued_jobs + 5):
        _make("done", order=float(i))
    ensure_capacity()  # should not raise


def test_queue_position_reflects_arrival_order():
    running = _make("running", order=0.0)
    first = _make("queued", order=1.0)
    second = _make("queued", order=2.0)

    assert queue_position(running) == 0  # running jobs aren't "in line"
    assert queue_position(first) == 1
    assert queue_position(second) == 2


@pytest.mark.asyncio
async def test_semaphore_permits_concurrent_execution():
    """Two tasks hold the job semaphore at the same time (given >=2 slots)."""
    active = 0
    peak = 0

    async def fake_job():
        nonlocal active, peak
        async with jobs._job_semaphore:
            active += 1
            peak = max(peak, active)
            await asyncio.sleep(0.05)
            active -= 1

    await asyncio.gather(*(fake_job() for _ in range(settings.max_concurrent_jobs)))
    assert peak == settings.max_concurrent_jobs
