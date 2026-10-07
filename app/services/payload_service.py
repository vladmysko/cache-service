import hashlib
from uuid import uuid4

from sqlalchemy import text
from sqlmodel import Session

from app.db.models import Payload
from app.repositories.payload import PayloadRepository
from app.repositories.transform_cache import TransformCacheRepository
from app.services.transformer import transform


class PayloadService:
    def __init__(self, session: Session):
        self.session = session
        self.cache_repository = TransformCacheRepository(session)
        self.payload_repository = PayloadRepository(session)

    def get(self, payload_id: str) -> Payload | None:
        return self.payload_repository.get_by_id(payload_id)

    def create_or_get(
        self,
        list_1: list[str],
        list_2: list[str],
    ) -> Payload:
        if len(list_1) != len(list_2):
            raise ValueError("Input lists must have the same length")

        try:
            dialect = self.session.get_bind().dialect.name
            if dialect == "sqlite":
                self.session.execute(text("BEGIN IMMEDIATE"))
            elif dialect == "postgresql":
                self.session.execute(text("SELECT pg_advisory_xact_lock(74192031)"))
            else:
                raise ValueError("Only SQLite and PostgreSQL are supported")
            return self._generate(list_1, list_2)
        except Exception:
            self.session.rollback()
            raise

    def _generate(self, list_1: list[str], list_2: list[str]) -> Payload:
        request_cache: dict[str, str] = {}

        output_values: list[str] = []

        for value_1, value_2 in zip(list_1, list_2):
            output_values.append(
                self._get_or_transform(value_1, request_cache)
            )
            output_values.append(
                self._get_or_transform(value_2, request_cache)
            )

        output = ", ".join(output_values)

        existing_payload = self.payload_repository.get_by_output(output)
        if existing_payload is not None:
            self.session.commit()
            return existing_payload

        fingerprint = hashlib.sha256(output.encode("utf-8")).hexdigest()
        payload = self.payload_repository.create(
            payload_id=str(uuid4()),
            fingerprint=fingerprint,
            output=output,
        )

        self.session.commit()
        self.session.refresh(payload)

        return payload

    def _get_or_transform(
        self,
        value: str,
        request_cache: dict[str, str],
    ) -> str:
        if value in request_cache:
            return request_cache[value]

        cached = self.cache_repository.get_by_input(value)

        if cached is not None:
            request_cache[value] = cached.output_value
            return cached.output_value

        transformed = transform(value)

        self.cache_repository.create(
            input_value=value,
            output_value=transformed,
        )

        request_cache[value] = transformed

        return transformed
