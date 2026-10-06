from datetime import datetime, timezone
from sqlmodel import Field, SQLModel


class TransformCache(SQLModel, table=True):
    __tablename__ = "transform_cache"

    id: int | None = Field(default=None, primary_key=True)

    input_value: str = Field(
        index=True,
        unique=True,
    )

    output_value: str

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class Payload(SQLModel, table=True):
    __tablename__ = "payload"

    id: str = Field(primary_key=True)

    fingerprint: str = Field(
        index=True,
        unique=True,
    )

    output: str

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )