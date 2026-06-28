import logging
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Request, status
from pydantic import BaseModel, EmailStr, Field

router = APIRouter(prefix="/demo", tags=["demo"])

logger = logging.getLogger(__name__)

_demo_requests: dict[str, dict[str, object]] = {}


class DemoRequestCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    phone: str = Field(min_length=1, max_length=50)
    industry: str = Field(min_length=1, max_length=100)
    notes: str = Field(default="", max_length=2000)


class DemoRequestResponse(BaseModel):
    id: str
    name: str
    email: str
    phone: str
    industry: str
    notes: str
    status: str
    created_at: datetime


@router.post(
    "/request",
    response_model=DemoRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_demo_request(
    payload: DemoRequestCreate,
    request: Request,
) -> DemoRequestResponse:
    request_id = str(uuid4())
    ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")

    logger.info(
        "New demo request received",
        extra={
            "request_id": request_id,
            "email": payload.email,
            "industry": payload.industry,
            "ip": ip,
            "user_agent": user_agent,
        },
    )

    now = datetime.now(UTC)
    demo_id = str(uuid4())

    record: dict[str, object] = {
        "id": demo_id,
        "name": payload.name,
        "email": payload.email,
        "phone": payload.phone,
        "industry": payload.industry,
        "notes": payload.notes,
        "status": "new",
        "created_at": now,
        "updated_at": now,
    }
    _demo_requests[demo_id] = record

    return DemoRequestResponse(
        id=str(record["id"]),
        name=str(record["name"]),
        email=str(record["email"]),
        phone=str(record["phone"]),
        industry=str(record["industry"]),
        notes=str(record["notes"]),
        status=str(record["status"]),
        created_at=now,
    )
