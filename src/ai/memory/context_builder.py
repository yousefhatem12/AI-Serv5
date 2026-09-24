from __future__ import annotations
from src.ai.memory.chat_history import get_recent_messages
from src.ai.crew.tools.cv_tool import get_cv_profile_tool


async def build_mentor_context(user_id: str, conversation_id: str) -> dict:
    """
    Assembles user conversation history and CV profile summary for Crew context.
    """
    recent_messages = await get_recent_messages(conversation_id)
    if hasattr(get_cv_profile_tool, "func"):
        cv_profile = get_cv_profile_tool.func(user_id=user_id)
    else:
        cv_profile = get_cv_profile_tool.invoke({"user_id": user_id})
    return {"recent_messages": recent_messages, "cv_summary": cv_profile}
