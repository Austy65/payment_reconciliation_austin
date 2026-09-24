from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.schemas import EventIn, EventIngestResponse
from app.services.event_service import ingest_event

router = APIRouter(prefix="/events", tags=["Events"])


@router.post(
    "",
    response_model=EventIngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a payment lifecycle event",
    description=(
        "Accepts a single payment event. Idempotent: submitting the same "
        "`event_id` twice returns `status=duplicate` and does not alter "
        "transaction state."
    ),
)
def post_event(payload: EventIn, db: Session = Depends(get_db)):
    result = ingest_event(db, payload)
    return result
