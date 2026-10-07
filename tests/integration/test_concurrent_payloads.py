from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Lock

import pytest
from sqlmodel import Session, select

from app.db.models import Payload, TransformCache
from app.services.payload_service import PayloadService


@pytest.mark.parametrize("shared_payload", [True, False])
def test_concurrent_requests_reuse_cache(engine, monkeypatch, shared_payload):
    barrier = Barrier(4)
    calls = []
    lock = Lock()

    def transform(value):
        with lock:
            calls.append(value)
        return value.upper()

    monkeypatch.setattr("app.services.payload_service.transform", transform)

    def request(index):
        barrier.wait(timeout=10)
        with Session(engine) as session:
            other = "other" if shared_payload else f"other-{index}"
            return PayloadService(session).create_or_get(["shared"], [other]).id

    with ThreadPoolExecutor(max_workers=4) as pool:
        ids = list(pool.map(request, range(4)))
    assert calls.count("shared") == 1
    assert len(set(ids)) == (1 if shared_payload else 4)
    with Session(engine) as session:
        assert len(session.exec(select(Payload)).all()) == len(set(ids))
        assert len(session.exec(select(TransformCache)).all()) == (2 if shared_payload else 5)
