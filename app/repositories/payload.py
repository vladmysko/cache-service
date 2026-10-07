from sqlmodel import Session, select

from app.db.models import Payload


class PayloadRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, payload_id: str) -> Payload | None:
        return self.session.get(Payload, payload_id)

    def get_by_fingerprint(self, fingerprint: str) -> Payload | None:
        statement = select(Payload).where(Payload.fingerprint == fingerprint)
        return self.session.exec(statement).first()

    def create(
        self,
        payload_id: str,
        fingerprint: str,
        output: str,
    ) -> Payload:
        payload = Payload(
            id=payload_id,
            fingerprint=fingerprint,
            output=output,
        )

        self.session.add(payload)

        return payload
