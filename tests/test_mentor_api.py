from __future__ import annotations
import json
from unittest.mock import AsyncMock, patch, MagicMock
import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.ai.suggested_prompts.agent_context import AgentType
from src.schemas.mentor_schema import MentorChatRequest, MentorChatEvent

client = TestClient(app)


def test_mentor_schemas():
    req = MentorChatRequest(
        message="Help me with my career plan",
        conversation_id="conv_123",
        user_id="user_456",
    )
    assert req.message == "Help me with my career plan"
    assert req.conversation_id == "conv_123"
    assert req.user_id == "user_456"

    event_token = MentorChatEvent(type="token", content="Hello")
    assert event_token.type == "token"
    assert event_token.content == "Hello"

    event_prompts = MentorChatEvent(
        type="suggested_prompts",
        agent="Mentor Agent",
        prompts=["Step 1?", "Step 2?"],
    )
    assert event_prompts.type == "suggested_prompts"
    assert len(event_prompts.prompts) == 2


def test_mentor_chat_stream_event_ordering():
    """
    Verifies that SSE events are sent in the exact required order:
    token (repeated) -> suggested_prompts (once) -> [DONE]
    and that save_turn is called after generation.
    """
    async def mock_stream(message, context):
        yield "Hello ", AgentType.MENTOR
        yield "world!", AgentType.MENTOR
        yield "", AgentType.MENTOR

    mock_prompts = ["What should I do next?", "How to prepare?"]
    saved_turns = []

    async def mock_save_turn(conv_id, user_msg, assistant_msg):
        saved_turns.append((conv_id, user_msg, assistant_msg))

    with patch("src.api.mentor_routes.run_mentor_crew_stream", side_effect=mock_stream), \
         patch("src.api.mentor_routes.get_fallback_with_timeout", new=AsyncMock(return_value=mock_prompts)), \
         patch("src.api.mentor_routes.save_turn", new=mock_save_turn), \
         patch("src.api.mentor_routes.build_mentor_context", new=AsyncMock(return_value={"recent_messages": []})):

        payload = {
            "message": "Hello mentor",
            "conversation_id": "test_conv_stream",
            "user_id": "test_user_stream",
        }
        response = client.post("/api/v1/mentor/chat/stream", json=payload)
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

        # Parse SSE stream
        raw_text = response.text
        lines = [line.strip() for line in raw_text.split("\n") if line.strip().startswith("data:")]

        events = []
        for line in lines:
            data_str = line[5:].strip()
            if data_str == "[DONE]":
                events.append({"type": "DONE"})
            else:
                events.append(json.loads(data_str))

        # 1. Event count and ordering check
        event_types = [e.get("type") for e in events]
        assert event_types[0] == "token"
        assert event_types[1] == "token"
        assert event_types[2] == "suggested_prompts"
        assert event_types[3] == "DONE"

        # 2. Check token contents
        assert events[0]["content"] == "Hello "
        assert events[1]["content"] == "world!"

        # 3. Check suggested_prompts payload
        assert events[2]["prompts"] == mock_prompts
        assert events[2]["agent"] == AgentType.MENTOR.value

        # 4. Check save_turn was called with complete assembled message
        assert len(saved_turns) == 1
        assert saved_turns[0] == ("test_conv_stream", "Hello mentor", "Hello world!")


def test_mentor_chat_stream_validation_error():
    """Missing payload fields must yield a 422 Unprocessable Entity error."""
    response = client.post("/api/v1/mentor/chat/stream", json={"message": "Incomplete"})
    assert response.status_code == 422


def test_api_v1_mentor_endpoint_available():
    """Endpoint must be available under /api/v1/mentor/chat/stream as well."""
    async def mock_stream(message, context):
        yield "OK", AgentType.MENTOR
        yield "", AgentType.MENTOR

    with patch("src.api.mentor_routes.run_mentor_crew_stream", side_effect=mock_stream), \
         patch("src.api.mentor_routes.get_fallback_with_timeout", new=AsyncMock(return_value=["Q1"])), \
         patch("src.api.mentor_routes.save_turn", new=AsyncMock()), \
         patch("src.api.mentor_routes.build_mentor_context", new=AsyncMock(return_value={})):

        payload = {
            "message": "Ping",
            "conversation_id": "c1",
            "user_id": "u1",
        }
        response = client.post("/api/v1/mentor/chat/stream", json=payload)
        assert response.status_code == 200
        assert "OK" in response.text
