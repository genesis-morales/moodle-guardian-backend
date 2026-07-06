from datetime import UTC, datetime

from src.domain.entities.moodle_connection import MoodleConnection


def _conn(**kw) -> MoodleConnection:
    base = dict(id=1, account_id=10, site_key="aprende", moodle_user_id=42,
                moodle_token="tok", is_active=True)
    base.update(kw)
    return MoodleConnection(**base)


def test_base_url_from_catalog():
    assert _conn(site_key="aprende").base_url.endswith("/webservice/rest/server.php")
    assert "educa" in _conn(site_key="educa").base_url


def test_token_failure_counter():
    c = _conn(token_failure_count=0)
    c.register_token_failure()
    c.register_token_failure()
    assert c.token_failure_count == 2
    c.clear_token_failures()
    assert c.token_failure_count == 0


def test_relink_reactivates_and_clears_failures():
    c = _conn(is_active=False, token_failure_count=3, moodle_token="viejo")
    c.relink("nuevo")
    assert (c.moodle_token, c.is_active, c.token_failure_count) == ("nuevo", True, 0)


def test_deactivate_clears_failures():
    c = _conn(is_active=True, token_failure_count=2)
    c.deactivate()
    assert c.is_active is False and c.token_failure_count == 0


def test_mark_scanned():
    now = datetime(2026, 7, 6, tzinfo=UTC)
    c = _conn()
    c.mark_scanned(now)
    assert c.last_scan_at == now
