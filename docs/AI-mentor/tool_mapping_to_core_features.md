# AI Mentor: Tool Mapping to Core Features

This document details how the **AI Mentor** feature integrates with and consumes all existing platform features as CrewAI tools, following the strict zero-duplication architectural pattern.

---

## 1. Architectural Overview & Design Principles

1. **Zero Service Modification**: Logic in `src/services/*` is treated as immutable.
2. **Thin Wrappers**: Every tool in `src/ai/crew/tools/*` is a direct delegate function calling service methods or repositories.
3. **Prompt Grounding**: Each tool has precise, LLM-targeted docstrings instructing the CrewAI agents when and how to invoke it.
4. **Canonical LLM Configuration**: All agents and chains dynamically inherit configuration from `src/core/config.py` via `src/core/llm.py:get_llm()`.

---

## 2. Summary Tool Mapping Matrix

| Feature Area | Underlying Service Layer | AI Mentor Tool Wrapper | Assigned Agents | Description |
| :--- | :--- | :--- | :--- | :--- |
| **Feature 1: CV Extraction & Profile** | `src/services/cv_service.py`<br>`src/db/repositories/candidate_repository.py` | `get_cv_profile_tool` | `mentor_agent`<br>`roadmap_agent` | Retrieves candidate skills, experience, education, and projects from CV profile. |
| **Feature 2: Explainable Match & Skill Gaps** | `src/services/matching_service.py` | `get_job_match_tool` | `mentor_agent`<br>`job_insights_agent` | Evaluates compatibility, matching skills, and missing skill gaps for a specific job. |
| **Feature 3: Personalized Job Recommendations** | `src/services/recommendation_service.py`<br>`src/services/recommendation_scoring.py` | `get_job_recommendations_tool` | `mentor_agent` | Delivers top candidate-matched jobs ranked by composite scoring. |
| **Feature 3: Recommendation Explanation** | `src/services/recommendation_explanation.py` | `explain_recommendation_tool` | `mentor_agent`<br>`job_insights_agent` | Explains why a specific job was recommended using evidence-grounded reasons. |
| **Feature 4: Technical Interview Prep** | `src/services/interview_service.py` | `get_interview_prep_tool` | `mentor_agent` | Generates targeted interview questions and study topics for candidate gaps. |
| **Feature 5: Career Roadmap & Learning Path** | `src/services/roadmap_service.py` | `get_roadmap_tool` | `mentor_agent`<br>`roadmap_agent` | Retrieves the candidate's staged roadmap, milestones, and weekly tasks. |

---

## 3. Detailed Tool Specifications

### 3.1 CV Profile Tool
- **File**: `src/ai/crew/tools/cv_tool.py`
- **Tool Name**: `"Get Candidate CV Profile"`
- **Signature**: `get_cv_profile_tool(user_id: str) -> dict`
- **Underlying Call**: `candidate_repository.get_candidate(user_id)` / `cv_service.get_extracted_profile(user_id)`
- **Assigned Agents**: `mentor_agent`, `roadmap_agent`
- **Purpose**: Provides ground truth candidate background without LLM hallucination.

### 3.2 Matching Tool
- **File**: `src/ai/crew/tools/matching_tool.py`
- **Tool Name**: `"Get Job Match & Skill Gaps"`
- **Signature**: `get_job_match_tool(user_id: str, job_id: str) -> dict`
- **Underlying Call**: `matching_service.evaluate_match(candidate_profile, job_requirements)`
- **Assigned Agents**: `mentor_agent`, `job_insights_agent`
- **Purpose**: Gives deterministic match percentages and specific missing skill gaps.

### 3.3 Recommendation Tools
- **File**: `src/ai/crew/tools/recommendation_tool.py`
- **Tool Name**: `"Get Personalized Job Recommendations"`
  - **Signature**: `get_job_recommendations_tool(user_id: str, limit: int = 5) -> list[dict]`
  - **Underlying Call**: `recommendation_service.get_recommendations(candidate, limit=limit)`
  - **Assigned Agents**: `mentor_agent`
- **Tool Name**: `"Explain Why a Job Was Recommended"`
  - **Signature**: `explain_recommendation_tool(user_id: str, job_id: str) -> str`
  - **Underlying Call**: `recommendation_explanation.build_recommendation_explanation(...)`
  - **Assigned Agents**: `mentor_agent`, `job_insights_agent`

### 3.4 Interview Prep Tool
- **File**: `src/ai/crew/tools/interview_tool.py`
- **Tool Name**: `"Get Interview Preparation"`
- **Signature**: `get_interview_prep_tool(user_id: str, job_id: str) -> dict`
- **Underlying Call**: `interview_service.create_prep_session(QuestionGenerationRequest(...))`
- **Assigned Agents**: `mentor_agent`
- **Purpose**: Delivers job-aligned practice questions and topics addressing identified gaps.

### 3.5 Roadmap Tool
- **File**: `src/ai/crew/tools/roadmap_tool.py`
- **Tool Name**: `"Get or Update Career Roadmap"`
- **Signature**: `get_roadmap_tool(user_id: str) -> dict`
- **Underlying Call**: `roadmap_service.get_candidate_roadmap(user_id)`
- **Assigned Agents**: `mentor_agent`, `roadmap_agent`
- **Purpose**: Fetches learning stages, active milestones, and progress.

---

## 4. Agent Tool Provisioning Breakdown

### `mentor_agent` (Role: General Career Mentor)
- **Assigned Tools**:
  1. `get_cv_profile_tool`
  2. `get_job_match_tool`
  3. `get_job_recommendations_tool`
  4. `explain_recommendation_tool`
  5. `get_interview_prep_tool`
  6. `get_roadmap_tool`
- **Behavior**: Answers high-level user career questions using all available context.

### `roadmap_agent` (Role: Career Roadmap Specialist)
- **Assigned Tools**:
  1. `get_cv_profile_tool`
  2. `get_roadmap_tool`
- **Behavior**: Scoped exclusively to assessing gaps and building/progressing learning plans.

### `job_insights_agent` (Role: Job Fit & Application Specialist)
- **Assigned Tools**:
  1. `get_job_match_tool`
  2. `explain_recommendation_tool`
- **Behavior**: Scoped to deep-diving into specific job requirements, match breakdown, and readiness.

---

## 5. Automated Verification

All tools and agent associations are covered by automated unit tests in:
- `tests/test_phase1_crew.py::test_tools_import_and_execution`
- `tests/test_phase1_crew.py::test_agents_configuration`

Run tests using:
```bash
pytest -v tests/test_phase1_crew.py
```
