# STEP 1 — Phase 1: Core Crew (Agents + Tools + Memory)

> Send this only after Antigravity has acknowledged the system context from Step 0.
> Do not send Phase 2 or Phase 3 content yet — this message should contain only what's below.

---

## Files to create in this phase

```diff
AI-Serv5/
├── src/
│   ├── ai/
+   │   └── crew/
+   │       ├── __init__.py
+   │       ├── agents.py                  # The 3 Agents (Mentor/Roadmap/JobInsights)
+   │       ├── tasks.py                   # The Tasks associated with each Agent
+   │       ├── crew.py                    # Assembles the Crew + the streaming function
+   │       └── tools/
+   │           ├── __init__.py
+   │           ├── cv_tool.py             # Wraps services/cv_service.py
+   │           ├── matching_tool.py       # Wraps services/matching_service.py
+   │           ├── recommendation_tool.py # Wraps recommendation_scoring/_explanation
+   │           ├── interview_tool.py      # Wraps services/interview_service.py
+   │           └── roadmap_tool.py        # Wraps services/roadmap_service.py (if it doesn't exist, add it following the same pattern as the other services)
│   ├── ai/
+   │   └── memory/
+   │       ├── __init__.py
+   │       ├── chat_history.py            # Reads/writes conversation history from the DB
+   │       └── context_builder.py         # Assembles the user context before sending it to the Crew
│   └── models/
+       ├── mentor_conversation.py         # Conversations table
+       └── mentor_message.py              # Messages table
```

---

## Task 1.1 — Tools: a wrapper around each existing service

**`src/ai/crew/tools/cv_tool.py`**
```python
from crewai.tools import tool
from src.services import cv_service


@tool("Get Candidate CV Profile")
def get_cv_profile_tool(user_id: str) -> dict:
    """
    Returns the profile extracted from the CV: skills, experience, projects,
    and education. Use this as soon as you need to know the user's
    background before making any suggestion.
    """
    return cv_service.get_extracted_profile(user_id)
```

**`src/ai/crew/tools/matching_tool.py`**
```python
from crewai.tools import tool
from src.services import matching_service


@tool("Get Job Match & Skill Gaps")
def get_job_match_tool(user_id: str, job_id: str) -> dict:
    """
    Calculates the match percentage between the user and a specific job, and
    returns the matching skills and the missing gaps. Use this when the user
    asks about a specific job.
    """
    return matching_service.calculate_match(user_id=user_id, job_id=job_id)
```

**`src/ai/crew/tools/recommendation_tool.py`**
```python
from crewai.tools import tool
from src.services import recommendation_scoring, recommendation_explanation


@tool("Get Personalized Job Recommendations")
def get_job_recommendations_tool(user_id: str, limit: int = 5) -> list[dict]:
    """
    Returns the top candidate jobs for the user, ranked by match. Use this
    when the user asks for general job suggestions.
    """
    return recommendation_scoring.get_top_recommendations(user_id=user_id, limit=limit)


@tool("Explain Why a Job Was Recommended")
def explain_recommendation_tool(user_id: str, job_id: str) -> str:
    """
    Explains why a specific job was recommended to the user. Use this when
    the user asks "why was this one recommended to me specifically?".
    """
    return recommendation_explanation.explain(user_id=user_id, job_id=job_id)
```

**`src/ai/crew/tools/interview_tool.py`**
```python
from crewai.tools import tool
from src.services import interview_service


@tool("Get Interview Preparation")
def get_interview_prep_tool(user_id: str, job_id: str) -> dict:
    """
    Generates interview questions and study topics related to a specific job
    and the user's gaps. Use this when interview preparation is requested.
    """
    return interview_service.generate_prep(user_id=user_id, job_id=job_id)
```

**`src/ai/crew/tools/roadmap_tool.py`**
```python
from crewai.tools import tool
from src.services import roadmap_service


@tool("Get or Update Career Roadmap")
def get_roadmap_tool(user_id: str) -> dict:
    """
    Returns the user's current roadmap: stages, milestones, and weekly tasks.
    Use this when the user asks about their plan or their next step.
    """
    return roadmap_service.get_current_roadmap(user_id=user_id)
```

**Definition of Done (Task 1.1):**
- [ ] Every file imports without errors.
- [ ] The docstring in each tool is precise and aimed at the LLM (this isn't an ordinary comment — it's read as part of the prompt).
- [ ] There is no real business logic inside the tools files — all of them are direct calls only.

---

## Task 1.2 — The Agents

**`src/ai/crew/agents.py`**
```python
from crewai import Agent

from src.ai.crew.tools.cv_tool import get_cv_profile_tool
from src.ai.crew.tools.matching_tool import get_job_match_tool
from src.ai.crew.tools.recommendation_tool import (
    get_job_recommendations_tool,
    explain_recommendation_tool,
)
from src.ai.crew.tools.interview_tool import get_interview_prep_tool
from src.ai.crew.tools.roadmap_tool import get_roadmap_tool


mentor_agent = Agent(
    role="Mentor Agent",
    goal=(
        "Help the user make practical career decisions based on their real "
        "data (CV, jobs they've viewed, their roadmap) — without inventing "
        "any information not present in the available tools."
    ),
    backstory=(
        "You are an expert career mentor inside the SkillMatch platform. "
        "You don't give generic advice — every response of yours is based "
        "on real data fetched from the tools available to you."
    ),
    tools=[
        get_cv_profile_tool,
        get_job_match_tool,
        get_job_recommendations_tool,
        explain_recommendation_tool,
        get_interview_prep_tool,
        get_roadmap_tool,
    ],
    memory=True,
    verbose=True,
    allow_delegation=False,
)

roadmap_agent = Agent(
    role="Roadmap Agent",
    goal="Build and update a practical, staged career plan based on real skill gaps.",
    backstory="A specialist in building actionable career-development plans, broken into stages and weekly goals.",
    tools=[get_cv_profile_tool, get_roadmap_tool],
    memory=True,
    verbose=True,
    allow_delegation=False,
)

job_insights_agent = Agent(
    role="Job Insights Agent",
    goal="Explain how well-suited the user is for a specific job and whether they should apply now or wait.",
    backstory="A specialist in analyzing the fit between candidates and jobs with transparency and clear evidence.",
    tools=[get_job_match_tool, explain_recommendation_tool],
    memory=True,
    verbose=True,
    allow_delegation=False,
)
```

**Definition of Done (Task 1.2):**
- [ ] Every Agent has precisely scoped Tools (no Agent carries every tool).
- [ ] `allow_delegation=False` on all three — so routing is decided explicitly in `tasks.py`, not by the Agents deciding among themselves.
- [ ] `verbose=True` is enabled on all Agents (needed for debugging during development; turn it off in production if the logs get too large).

---

## Task 1.3 — Tasks + Crew

**`src/ai/crew/tasks.py`**
```python
from crewai import Task
from src.ai.crew.agents import mentor_agent, roadmap_agent, job_insights_agent


def build_mentor_task(user_message: str, context: dict) -> Task:
    return Task(
        description=(
            f"User message: {user_message}\n\n"
            f"Available context: {context}\n\n"
            "Answer using only the available tools. If you need data that "
            "isn't in the context, use the appropriate tool."
        ),
        expected_output="A direct, useful response to the user based on real data.",
        agent=mentor_agent,
    )


def build_roadmap_task(user_message: str, context: dict) -> Task:
    return Task(
        description=f"User message: {user_message}\n\nAvailable context: {context}",
        expected_output="A plan or update to the roadmap based on real gaps.",
        agent=roadmap_agent,
    )


def build_job_insights_task(user_message: str, context: dict) -> Task:
    return Task(
        description=f"User message: {user_message}\n\nAvailable context: {context}",
        expected_output="A clear compatibility analysis with the job mentioned.",
        agent=job_insights_agent,
    )
```

**`src/ai/crew/crew.py`**
```python
from crewai import Crew, Process

from src.ai.crew.agents import mentor_agent, roadmap_agent, job_insights_agent
from src.ai.crew.tasks import (
    build_mentor_task,
    build_roadmap_task,
    build_job_insights_task,
)
from src.ai.suggested_prompts.agent_context import AgentType


def _classify_intent(user_message: str) -> AgentType:
    """
    A lightweight initial classification (rule-based or a fast model) to
    determine who should respond. Start with simple rule-based logic, and
    it can later be switched to a small classification model if needed.
    """
    lowered = user_message.lower()
    if any(k in lowered for k in ["roadmap", "plan", "milestone", "stage"]):
        return AgentType.ROADMAP
    if any(k in lowered for k in ["this job", "apply", "match", "fit"]):
        return AgentType.JOB_INSIGHTS
    return AgentType.MENTOR


async def run_mentor_crew_stream(user_message: str, context: dict):
    """
    Determines the appropriate Agent, runs its Task inside a separate Crew
    (so the streaming source is clear), and yields (token, agent_type)
    incrementally.
    """
    intent = _classify_intent(user_message)

    task_builders = {
        AgentType.MENTOR: build_mentor_task,
        AgentType.ROADMAP: build_roadmap_task,
        AgentType.JOB_INSIGHTS: build_job_insights_task,
    }
    task = task_builders[intent](user_message, context)

    crew = Crew(
        agents=[task.agent],
        tasks=[task],
        process=Process.sequential,
        verbose=True,
    )

    # CrewAI supports streaming either via kickoff with a callback or via
    # the underlying LLM client used internally (depending on the CrewAI
    # version). The following is simplified and assumes a supported stream
    # function exists — if the version used doesn't support direct
    # streaming, use a regular kickoff() and split the output into chunks
    # manually.
    async for token in crew.kickoff_stream():
        yield token, intent

    yield "", intent  # end-of-stream signal to guarantee agent_type is sent even if the response is empty
```

> **Note:** `crew.py` imports `AgentType` from `src/ai/suggested_prompts/agent_context.py`, which is created in Phase 2. For this phase, either stub a minimal `AgentType` enum in a placeholder file so `crew.py` imports cleanly, or leave `crew.py` written but not yet wired into any route (the route comes in Phase 3). Do not build out the rest of `suggested_prompts/` yet — that's Phase 2.

**Definition of Done (Task 1.3):**
- [ ] `_classify_intent` returns the correct `AgentType` for clear-cut cases, with `MENTOR` as a safe default.
- [ ] `run_mentor_crew_stream` continuously yields `(token, agent_type)` so a later route can correctly build the `suggested_prompts`.
- [ ] There's a clear comment in the code if `kickoff_stream()` doesn't exist in the CrewAI version actually used in the project — along with the fallback (splitting up the regular `kickoff()`).

---

## Task 1.4 — Memory / Chat History

**`src/ai/memory/chat_history.py`**
```python
from src.db.session import get_session
from src.models.mentor_message import MentorMessage


async def get_recent_messages(conversation_id: str, limit: int = 10) -> list[dict]:
    async with get_session() as session:
        rows = await session.execute(
            MentorMessage.select()
            .where(MentorMessage.conversation_id == conversation_id)
            .order_by(MentorMessage.created_at.desc())
            .limit(limit)
        )
        return [row.to_dict() for row in reversed(rows.fetchall())]


async def save_turn(conversation_id: str, user_message: str, assistant_message: str) -> None:
    async with get_session() as session:
        session.add_all(
            [
                MentorMessage(conversation_id=conversation_id, role="user", content=user_message),
                MentorMessage(conversation_id=conversation_id, role="assistant", content=assistant_message),
            ]
        )
        await session.commit()
```

**`src/ai/memory/context_builder.py`**
```python
from src.ai.memory.chat_history import get_recent_messages
from src.ai.crew.tools.cv_tool import get_cv_profile_tool


async def build_mentor_context(user_id: str, conversation_id: str) -> dict:
    recent_messages = await get_recent_messages(conversation_id)
    cv_profile = get_cv_profile_tool.run(user_id=user_id)
    return {"recent_messages": recent_messages, "cv_summary": cv_profile}
```

**`src/models/mentor_conversation.py`**
```python
from sqlalchemy import Column, String, DateTime, func
from src.db.base import Base


class MentorConversation(Base):
    __tablename__ = "mentor_conversations"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    active_agent = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
```

**`src/models/mentor_message.py`**
```python
from sqlalchemy import Column, String, Text, DateTime, func
from src.db.base import Base


class MentorMessage(Base):
    __tablename__ = "mentor_messages"

    id = Column(String, primary_key=True)
    conversation_id = Column(String, nullable=False, index=True)
    role = Column(String, nullable=False)  # "user" | "assistant" | "tool"
    content = Column(Text, nullable=False)
    tool_name = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
```

**Definition of Done (Task 1.4):**
- [ ] Both tables get an actual migration (Alembic or whatever migration tool is used in the project) — not just the model class.
- [ ] `get_recent_messages` returns messages in ascending chronological order (oldest first) so they're placed correctly in the context.
- [ ] If `src/db/base.py` uses an ORM other than SQLAlchemy, the syntax is adjusted accordingly, keeping the same field names.

---

## Before moving to Phase 2

Confirm all of Phase 1's Definition of Done items are checked, and that:
- `pip install crewai` (plus whatever CrewAI needs) is in `requirements.txt`.
- The migration for `mentor_conversations` / `mentor_messages` actually ran.
- No file inside `src/services/*` was touched.

Only send Phase 2 once this is confirmed.
