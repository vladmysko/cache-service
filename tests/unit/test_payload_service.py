from sqlmodel import select

from app.db.models import TransformCache
from app.services.payload_service import PayloadService


def test_generates_interleaved_payload(session):
    service = PayloadService(session)

    payload = service.create_or_get(
        ["first", "second"],
        ["other", "another"],
    )

    assert payload.output == (
        "FIRST, OTHER, SECOND, ANOTHER"
    )


def test_reuses_payload_identifier(session):
    service = PayloadService(session)

    first = service.create_or_get(
        ["hello"],
        ["world"],
    )

    second = service.create_or_get(
        ["hello"],
        ["world"],
    )

    assert first.id == second.id


def test_duplicate_values_are_cached_once(session):
    service = PayloadService(session)

    service.create_or_get(
        ["same", "same", "same"],
        ["other", "same", "other"],
    )

    entries = session.exec(
        select(TransformCache)
    ).all()

    assert len(entries) == 2


def test_reuses_transform_cache_across_payloads(session):
    service = PayloadService(session)

    service.create_or_get(
        ["shared"],
        ["first"],
    )

    service.create_or_get(
        ["shared"],
        ["second"],
    )

    shared_entries = session.exec(
        select(TransformCache).where(
            TransformCache.input_value == "shared"
        )
    ).all()

    assert len(shared_entries) == 1


def test_rejects_lists_with_different_lengths(session):
    service = PayloadService(session)

    try:
        service.create_or_get(
            ["a", "b"],
            ["c"],
        )
    except ValueError as exc:
        assert str(exc) == "Input lists must have the same length"
    else:
        raise AssertionError("ValueError was not raised")

def test_same_output_reuses_existing_identifier(session):
    from app.db.models import Payload

    import hashlib

    # Pre-existing payloads are found through their output fingerprint.
    fingerprint = hashlib.sha256(b"HELLO, WORLD").hexdigest()
    session.add(Payload(id="existing-id", fingerprint=fingerprint, output="HELLO, WORLD"))
    session.commit()
    service = PayloadService(session)
    assert service.create_or_get(["hello"], ["world"]).id == "existing-id"
    assert service.create_or_get(["HELLO"], ["WORLD"]).id == "existing-id"


def test_transform_called_once_per_unique_input(session, monkeypatch):
    from unittest.mock import Mock

    transformer = Mock(side_effect=str.upper)
    monkeypatch.setattr("app.services.payload_service.transform", transformer)
    service = PayloadService(session)
    service.create_or_get(["same", "same"], ["other", "same"])
    service.create_or_get(["same"], ["new"])
    assert [call.args[0] for call in transformer.call_args_list] == ["same", "other", "new"]


def test_transform_failure_rolls_back_and_allows_retry(session, monkeypatch):
    import pytest

    def fail(value):
        if value == "bad":
            raise RuntimeError("transform failed")
        return value.upper()

    monkeypatch.setattr("app.services.payload_service.transform", fail)
    service = PayloadService(session)
    with pytest.raises(RuntimeError, match="transform failed"):
        service.create_or_get(["good"], ["bad"])
    assert session.exec(select(TransformCache)).all() == []
    assert service.create_or_get(["good"], ["other"]).output == "GOOD, OTHER"
