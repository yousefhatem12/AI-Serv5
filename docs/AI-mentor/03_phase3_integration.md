# STEP 3 — Phase 3: Final Integration (Schema + API Route)

> Send this only after Phase 2 is complete and its tests pass.

---

## Files to create in this phase

```diff
AI-Serv5/
├── src/
│   ├── api/
+   │   └── mentor_routes.py               # POST /mentor/chat/stream (SSE)
│   └── schemas/
+       └── mentor_schema.py               # MentorChatRequest / MentorChatEvent
```

---

**`src/schemas/mentor_schema.py`**
```python
from pydantic import BaseModel


class MentorChatRequest(BaseModel):
    message: str
    conversation_id: str
    user_id: str


class MentorChatEvent(BaseModel):
    type: str  # "token" | "suggested_prompts" | "error"
    content: str | None = None
    agent: str | None = None
    prompts: list[str] | None = None
```

**`src/api/mentor_routes.py`**
```python
import json
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from src.schemas.mentor_schema import MentorChatRequest
from src.ai.memory.context_builder import build_mentor_context
from src.ai.memory.chat_history import save_turn
from src.ai.crew.crew import run_mentor_crew_stream
from src.ai.suggested_prompts.fallback import get_fallback_with_timeout
from src.middleware.auth import get_current_user

router = APIRouter()


def sse_event(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/mentor/chat/stream")
async def mentor_chat_stream(
    payload: MentorChatRequest,
    current_user=Depends(get_current_user),
):
    context = await build_mentor_context(payload.user_id, payload.conversation_id)

    async def generator():
        full_answer = ""
        active_agent_type = None

        async for token, agent_type in run_mentor_crew_stream(payload.message, context):
            if token:
                full_answer += token
                yield sse_event({"type": "token", "content": token})
            active_agent_type = agent_type

        prompts = await get_fallback_with_timeout(active_agent_type, full_answer)
        yield sse_event(
            {
                "type": "suggested_prompts",
                "agent": active_agent_type.value,
                "prompts": prompts,
            }
        )

        await save_turn(payload.conversation_id, payload.message, full_answer)
        yield "data: [DONE]\n\n"

    return StreamingResponse(generator(), media_type="text/event-stream")
```

**Definition of Done (Phase 3):**
- [ ] The endpoint is protected by the same `get_current_user` middleware used across the rest of the API.
- [ ] Order of events in the stream: `token` (repeated) → `suggested_prompts` (once) → `[DONE]`.
- [ ] `save_turn` runs **after** all events have been sent, not before, so it doesn't delay the streaming.
- [ ] Router is registered on the main FastAPI app (check how other routers in `src/api/` are included, and follow the same pattern).

---

## Final Integration Checklist (run through this once Phase 3 is done)

| # | Check | Status |
|---|---|---|
| 1 | `pip install crewai instructor openai fastapi pytest pytest-asyncio` added to `requirements.txt` | ☐ |
| 2 | An actual migration for the `mentor_conversations` and `mentor_messages` tables | ☐ |
| 3 | `roadmap_service.py` exists or was added following the same pattern as the other `services/*` | ☐ |
| 4 | Manual test on `/mentor/chat/stream`, confirming the event order (token → suggested_prompts → DONE) | ☐ |
| 5 | All unit tests in `test_suggested_prompts.py` pass | ☐ |
| 6 | OpenTelemetry tracing (OpenInference/OpenLLMetry) enabled on top of the Crew before deployment | ☐ |
| 7 | Review confirming there is no business-logic line inside `src/ai/` — everything is just calls to `services/*` | ☐ |
