from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_session
from src.schemas.ai import GenerateRequest, GenerateResponse, MessageType

router = APIRouter(prefix="/api/v1", tags=["ai"])


@router.post("/generate", response_model=GenerateResponse)
async def generate(
    payload: GenerateRequest, session: AsyncSession = Depends(get_session)
) -> GenerateResponse:
    now = datetime.now(timezone.utc)
    return GenerateResponse(
        conversation_id=payload.conversation_id,
        content="AI response here",
        type=MessageType.ai,
        created_at=now,
        updated_at=now,
    )
