"""AI Controller V2 with streaming support via Server-Sent Events."""

from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import StreamingResponse
from src.middlewares.events import tracked_stream
from src.dependencies import WideEvent, CurrentUser, AgentService, RateLimit
from src.schemas.ai import GenerateRequest
from src.tasks.compaction_task import post_message_hook

router = APIRouter(prefix="/api/v2", tags=["ai-v2"])


@router.post("/generate/stream")
async def generate_stream(
    payload: GenerateRequest,
    current_user: CurrentUser,
    wide_event: WideEvent,
    agent_service: AgentService,
    background_tasks: BackgroundTasks,
    _: RateLimit,
) -> StreamingResponse:
    """Stream AI response using Server-Sent Events."""

    wide_event.add_context(
        user_id=current_user.user_id,
        conversation_id=str(payload.conversation_id),
        user_message_length=len(payload.content),
        streaming=True,
    )

    streaming_response = agent_service.process_agent_query_stream(
        user_id=current_user.user_id,
        conversation_id=payload.conversation_id,
        content=payload.content,
    )

    # Spawn background task for token counting and compaction
    background_tasks.add_task(
        post_message_hook,
        str(payload.conversation_id),
        correlation_id=wide_event.correlation_id,
    )

    return StreamingResponse(
        content=tracked_stream(streaming_response, wide_event),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
