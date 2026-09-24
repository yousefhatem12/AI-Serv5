# STEP 0 — Paste this first, as your opening message to Antigravity

```
You are working on AI-Serv5, the backend for the SkillMatch platform
(a smart job-discovery + AI-powered career mentoring platform).

The project already has an existing Python/FastAPI structure:

AI-Serv5/
├── scripts/
├── src/
│   ├── ai/
│   ├── api/
│   ├── core/
│   ├── cv_extractor/
│   ├── db/
│   ├── integrations/
│   ├── job_extractor/
│   ├── middleware/
│   ├── models/
│   ├── schemas/
│   └── services/
│       ├── cv_service.py
│       ├── interview_service.py
│       ├── matching_service.py
│       ├── recommendation_explanation.py
│       └── recommendation_scoring.py

The rule that must never be broken, no matter what:
- The logic inside src/services/* must not be touched, modified, or duplicated.
- The task at hand is to build an "AI Mentor" as a Feature Agent only, which
  uses the existing services as Tools (direct calls), without rewriting
  their logic.
- Any new file goes inside src/ai/, src/models/, src/schemas/, src/api/
  following the same naming pattern already used in the project. Moving or
  deleting anything existing is forbidden.
- The framework used to build the Agents is CrewAI exclusively.

In short, what's required across the whole feature (I will send it to you in
three separate phases, one at a time — do not start phases you haven't
received yet):
1. Build 3 CrewAI Agents: Mentor Agent, Roadmap Agent, Job Insights Agent.
2. Each Agent is equipped with thin tools (thin wrappers) around the
   existing services/*.
3. Real memory: every conversation and every message is stored in the DB
   (only two new tables).
4. Live streaming of the response via an SSE endpoint in FastAPI.
5. After each response, generate 3 "Suggested Prompts" (follow-up questions)
   using a fast model (gpt-4o-mini) as Structured Output via Pydantic, with a
   guaranteed fallback if generation fails or exceeds the time limit.

Acknowledge you understand this context and the constraint on src/services/*,
then wait for Phase 1.
```

---

**Why this file exists on its own:** it gives Antigravity the full picture and the hard constraint up front, without asking it to build anything yet. Wait for it to acknowledge before sending Phase 1 — that confirms it actually read the repo structure and the rule about `services/*` before touching any code.
