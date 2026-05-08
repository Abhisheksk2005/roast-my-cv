from __future__ import annotations

from types import SimpleNamespace

import pytest

from backend.services import research_concurrency as rc


class _Req:
    def __init__(self, ip: str) -> None:
        self.headers = {}
        self.client = SimpleNamespace(host=ip)
        self.app = SimpleNamespace(state=SimpleNamespace())


@pytest.mark.asyncio
async def test_session_cap_blocks_parallel_same_session(monkeypatch):
    monkeypatch.setattr(rc, "research_concurrency_disabled", lambda: False)
    monkeypatch.setattr(rc, "redis_enabled", lambda: False)
    monkeypatch.setattr(rc, "RESEARCH_MAX_INFLIGHT_PER_IP", 10)
    monkeypatch.setattr(rc, "RESEARCH_MAX_INFLIGHT_PER_SESSION", 1)
    monkeypatch.setattr(rc, "RESEARCH_INFLIGHT_TTL_SEC", 60)

    req = _Req("1.2.3.4")
    ok1, retry1, detail1, lease1 = await rc.acquire_research_lease(req, "sess-a")
    assert ok1 is True
    assert retry1 == 0
    assert detail1 is None
    assert lease1 is not None

    ok2, retry2, detail2, lease2 = await rc.acquire_research_lease(req, "sess-a")
    assert ok2 is False
    assert retry2 > 0
    assert detail2 is not None and "session" in detail2.lower()
    assert lease2 is None

    await rc.release_lease_async(req, lease1)

    ok3, _, _, lease3 = await rc.acquire_research_lease(req, "sess-a")
    assert ok3 is True
    await rc.release_lease_async(req, lease3)


@pytest.mark.asyncio
async def test_ip_cap_blocks_parallel_same_ip(monkeypatch):
    monkeypatch.setattr(rc, "research_concurrency_disabled", lambda: False)
    monkeypatch.setattr(rc, "redis_enabled", lambda: False)
    monkeypatch.setattr(rc, "RESEARCH_MAX_INFLIGHT_PER_IP", 1)
    monkeypatch.setattr(rc, "RESEARCH_MAX_INFLIGHT_PER_SESSION", 10)
    monkeypatch.setattr(rc, "RESEARCH_INFLIGHT_TTL_SEC", 60)

    req = _Req("5.6.7.8")
    ok1, _, _, lease1 = await rc.acquire_research_lease(req, "sess-a")
    assert ok1 is True
    assert lease1 is not None

    ok2, retry2, detail2, lease2 = await rc.acquire_research_lease(req, "sess-b")
    assert ok2 is False
    assert retry2 > 0
    assert detail2 is not None and "ip" in detail2.lower()
    assert lease2 is None

    await rc.release_lease_async(req, lease1)


def test_release_lease_sync_redis_decrements_and_deletes(monkeypatch):
    class _FakeRedis:
        def __init__(self):
            self.values = {"k1": 1, "k2": 2}
            self.deleted: list[str] = []

        def decr(self, key: str) -> int:
            self.values[key] = int(self.values.get(key, 0)) - 1
            return self.values[key]

        def delete(self, key: str) -> None:
            self.deleted.append(key)

    fake = _FakeRedis()
    monkeypatch.setattr(rc, "get_sync_redis", lambda: fake)

    rc.release_lease_sync({"backend": "redis", "ip_key": "k1", "session_key": "k2"})

    assert "k1" in fake.deleted
    assert "k2" not in fake.deleted
    assert fake.values["k2"] == 1
