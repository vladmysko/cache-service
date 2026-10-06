from sqlmodel import Session, select
from app.db.models import TransformCache

class TransformCacheRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_input(self, input_value: str) -> TransformCache | None:
        statement = select(TransformCache).where(
            TransformCache.input_value == input_value
        )
        return self.session.exec(statement).first()

    def create(self, input_value: str, output_value: str) -> TransformCache:
        cache_entry = TransformCache(input_value=input_value, output_value=output_value)

        self.session.add(cache_entry)
        return cache_entry