from datetime import UTC, datetime, timedelta

from src.domain.entities.scan_run import ScanFailure, ScanRun

START = datetime(2026, 6, 30, 10, 0, 0, tzinfo=UTC)


def build(success: int, failure: int, seconds: float = 12.5) -> ScanRun:
    return ScanRun(
        job_name="scan",
        started_at=START,
        finished_at=START + timedelta(seconds=seconds),
        total_users=success + failure,
        success_count=success,
        failure_count=failure,
        failures=[ScanFailure(moodle_user_id=1, error="boom")] * failure,
    )


def test_status_ok_when_no_failures():
    assert build(success=5, failure=0).status == "ok"


def test_status_partial_when_some_fail():
    assert build(success=3, failure=2).status == "partial"


def test_status_failed_when_all_fail():
    assert build(success=0, failure=4).status == "failed"


def test_duration_ms():
    assert build(success=1, failure=0, seconds=2.5).duration_ms == 2500
