from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.db.database import get_session
from app.schemas.payload import (
    PayloadCreateRequest,
    PayloadCreateResponse,
    PayloadResponse,
)
from app.services.payload_service import PayloadService


router = APIRouter(
    prefix="/payload",
    tags=["payload"],
)


@router.post(
    "",
    response_model=PayloadCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_payload(
    request: PayloadCreateRequest,
    session: Session = Depends(get_session),
) -> PayloadCreateResponse:
    service = PayloadService(session)

    payload = service.create_or_get(
        request.list_1,
        request.list_2,
    )

    return PayloadCreateResponse(id=payload.id)


@router.get(
    "/{payload_id}",
    response_model=PayloadResponse,
)
def get_payload(
    payload_id: str,
    session: Session = Depends(get_session),
) -> PayloadResponse:
    service = PayloadService(session)

    payload = service.get(payload_id)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payload not found",
        )

    return PayloadResponse(output=payload.output)