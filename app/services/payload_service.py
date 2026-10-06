import hashlib
import json
from uuid import uuid4

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

        fingerprint = self._build_fingerprint(list_1, list_2)

        existing_payload = self.payload_repository.get_by_fingerprint(
            fingerprint
        )

        if existing_payload is not None:
            return existing_payload

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

    @staticmethod
    def _build_fingerprint(
        list_1: list[str],
        list_2: list[str],
    ) -> str:
        canonical_input = json.dumps(
            {
                "list_1": list_1,
                "list_2": list_2,
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )

        return hashlib.sha256(
            canonical_input.encode("utf-8")
        ).hexdigest()