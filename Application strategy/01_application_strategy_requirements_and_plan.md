# Application Strategy Guidance — Requirements & Phased Implementation Plan

## 1. Feature Overview & Requirements

**Feature:** Application Strategy Guidance (Feature 10)  
**Objective:** Evaluate the candidate's verified profile against a specific target job to generate an actionable, evidence-based application strategy explaining whether the candidate should:
1. **Apply Now (`APPLY_NOW`)**: Strong match with low or negligible blockers.
2. **Apply While Improving (`APPLY_WHILE_IMPROVING` / `IMPROVE_FIRST`)**: Viable candidate with manageable gaps that can be tackled concurrently with applications.
3. **Prioritize Another Role First (`PRIORITIZE_ANOTHER_ROLE` / `ALTERNATIVE_ROLES`)**: Critical blocker gaps exist, making adjacent or alternative roles a higher-yield immediate focus.

---

### Key Requirements & Constraints (from Specification)
- **Truthfulness & Ethical Boundaries**: Guidance **MUST** be explicitly framed as professional advice, **NEVER** as a guarantee of hiring outcomes or placement probabilities.
- **Context-Grounded**: Strictly use the candidate's verified CV extraction, target role, match scores, and actual job requirements.
- **Action Plan Delivery**: Output must include a structured action plan attached to the specific job, detailing categorized gaps, concrete next steps, and alternative role suggestions.

---

## 2. Architecture & Data Flow

```mermaid
flowchart TD
    Req[POST /api/v1/jobs/{job_id}/application-strategy] --> Service[ApplicationStrategyService]
    Service --> CV[cv_service.get_extracted_profile]
    Service --> Match[matching_service.calculate_match]
    Service --> Rec[recommendation_scoring / alternative roles]
    Service --> DecisionEngine[Decision Matrix & LLM Synthesizer]
    DecisionEngine --> Resp[ApplicationStrategyResponse]
    Resp --> DB[(Persistence)]
    Resp --> MentorTool[get_application_strategy_tool] --> Crew[AI Mentor Crew]
```

---

## 3. Phased Implementation Plan

### Phase 1: Schemas & Data Contracts
**Location:** `src/schemas/application_strategy.py`
- Define `StrategyDecision` Enum: `APPLY_NOW`, `APPLY_WHILE_IMPROVING`, `PRIORITIZE_ANOTHER_ROLE`.
- Define `GapCategory` & `GapSeverity`: `BLOCKER`, `MODERATE`, `MINOR`.
- Define `StrategyActionItem`: Specific weekly tasks, CV tweaks, or portfolio additions.
- Define `AlternativeRole`: Suitable adjacent roles with fit scores and rationale.
- Define `ApplicationStrategyResponse`:
  - `decision: StrategyDecision`
  - `summary_reasoning: str`
  - `match_score: float`
  - `strengths: list[str]`
  - `blocker_gaps: list[str]`
  - `manageable_gaps: list[str]`
  - `action_plan: list[StrategyActionItem]`
  - `alternative_roles: list[AlternativeRole]`
  - `disclaimer: str` (Guaranteed advice framing)

---

### Phase 2: Core Strategy Service (`src/services/application_strategy_service.py`)
**Location:** `src/services/application_strategy_service.py`
- Direct integration with existing services (`src/services/cv_service.py`, `src/services/matching_service.py`, `src/services/recommendation_scoring.py`).
- **Deterministic Decision Guardrails**:
  - Score >= 75% & 0 blockers $\rightarrow$ `APPLY_NOW`
  - Score 50%–74% or minor/moderate gaps $\rightarrow$ `APPLY_WHILE_IMPROVING`
  - Score < 50% or critical prerequisite blockers $\rightarrow$ `PRIORITIZE_ANOTHER_ROLE`
- **Structured LLM Synthesis**: Use instructor / Pydantic structured outputs with prompt rules enforcing non-guaranteed advice language.

---

### Phase 3: AI Mentor Crew & Tool Integration
**Location:** `src/ai/crew/tools/strategy_tool.py`, `src/ai/crew/agents.py`
- Expose `@tool("Get Application Strategy Guidance")` wrapper around `application_strategy_service`.
- Equip `job_insights_agent` and `mentor_agent` with this tool to deliver live strategy advice inside the SSE chat stream.
- Add suggested prompt templates specifically for application strategies (e.g. *"Should I apply for this role now or improve first?"*).

---

### Phase 4: API Routes & Fast Endpoints
**Location:** `src/api/v1/endpoints/application_strategy.py`, `src/api/v1/routers.py`
- `POST /api/v1/jobs/{job_id}/application-strategy`
  - Input: Candidate profile / user_id, target `job_id`.
  - Output: Structured `ApplicationStrategyResponse`.
- Include in OpenAPI documentation and tag with `"Application Strategy"`.

---

### Phase 5: Test Suite & Validation
**Location:** `tests/test_application_strategy.py`
- **Decision Matrix Tests**: Verify correct classification across high-match, partial-match, and low-match scenarios.
- **Truthfulness & Disclaimer Tests**: Verify that output always contains the non-guarantee disclaimer and no fabricated requirements.
- **API Endpoint Tests**: Full endpoint validation with mock dependencies and FastAPI TestClient.
- **Mentor Crew Tool Tests**: Verify tool invocation within CrewAI execution.

---

## 4. Definition of Done
- [ ] Schema, service, API endpoint, and AI Mentor tool implemented cleanly without modifying existing `src/services/*` files.
- [ ] 100% test coverage on decision classification, fallback mechanisms, and API contracts.
- [ ] Non-guarantee disclaimer and truthfulness constraints strictly enforced in prompts and schema responses.
