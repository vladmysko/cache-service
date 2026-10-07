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