# Agent Action History

This document serves as a persistent memory of the agent's actions, decisions, and progress within the project.

## 2026-09-15 - Initial Setup
- Created this `Agent.md` file to track the history of actions and decisions.

## 2026-09-15 - Codebase Scan
- Scanned the root directory and `src/` directory to understand the project structure.
- Read the `README.md` which details the "SkillMatch — AI Features" technical report, including architecture, design patterns, and feature map.
- Identified the core stack: FastAPI, LangChain, LlamaIndex, Python 3.11+.
- Located key directories: `src/api` (FastAPI routes), `src/ai` (LangChain orchestration, chains, tools, prompts), `src/services`, `src/schemas`, `src/db`, and `src/workers`.
- The AI layer is designed with a strategy pattern for LLMs, facade pattern for capabilities, and heavily relies on Pydantic schemas for output parsing.

## 2026-09-15 - YouTube Learning Resources Pipeline
- Implemented an offline batch pipeline to fetch curated YouTube videos for skill gaps.
- Created `SkillResourceModel` in `src/db/models/skill_resource.py` to store fetched videos in the database.
- Registered the new model with SQLAlchemy in `src/db/base.py`.
- Enriched `RoadmapTask` and `SkillMatchItem` schemas in `src/schemas/roadmap.py` and `src/schemas/match.py` to include a rich `ResourceLinkSchema`.
- Developed `src/workers/youtube_fetcher.py` which iterates through the canonical taxonomy, searches YouTube via the Data API v3, and pushes pending items to the `ReviewQueueRepository`.
- Modified `ReviewQueueService.resolve_item` in `src/services/review_queue_service.py` to handle `youtube_resource` items. When approved by an admin, resources are written to the `skill_resources` table.
- Updated `RoadmapService._enrich_roadmap_with_resources` to automatically retrieve approved resources from the database and attach them to generated roadmaps.

## 2026-09-20 - Structural Consolidation & Architecture Refactoring (AI-Serv5)

Conducted a thorough structural cleanup and architectural consolidation of SkillMatch AI Services (`AI-Serv5`), aligning persistence with the target backend schema (`SkillMatch_Database_Schema.pdf`), de-duplicating architecture layers, and standardizing error handling and configuration, while strictly preserving the canonical `get_llm()` runtime and all AI business logic.

### 1. Provider-Neutral API Error Handling
- Removed direct provider-specific knowledge (`import groq`, `groq.GroqError`, `GROQ_API_KEY` messages) from [src/api/main.py](file:///c:/Users/NV_USER/Desktop/AI-Serv5/src/api/main.py).
- Implemented generic, provider-neutral LLM error inspection at the API layer returning `LLM_AUTHENTICATION_ERROR` (401), `LLM_RATE_LIMIT_ERROR` (429), and `LLM_GATEWAY_ERROR` (502).
- Removed legacy `DynamicLLMMiddleware` from FastAPI application mounting.

### 2. Router Consolidation
- Audited and merged legacy routers in `src/api/routers/` (`cv_router.py`, `job_router.py`) with [src/api/v1/endpoints/](file:///c:/Users/NV_USER/Desktop/AI-Serv5/src/api/v1/endpoints/).
- Added canonical endpoint [src/api/v1/endpoints/jobs.py](file:///c:/Users/NV_USER/Desktop/AI-Serv5/src/api/v1/endpoints/jobs.py) for `/api/v1/jobs/analyze`.
- Unified all 23 endpoints under canonical router aggregator [src/api/v1/routers.py](file:///c:/Users/NV_USER/Desktop/AI-Serv5/src/api/v1/routers.py).
- Deleted obsolete directory `src/api/routers/` with zero broken imports.

### 3. Schema Consolidation
- Audited schemas in `src/api/schemas/` (`cv_schemas.py`, `job_schemas.py`) against `src/schemas/`.
- Consolidated all DTOs, request models, response models, and error responses into canonical [src/schemas/cv.py](file:///c:/Users/NV_USER/Desktop/AI-Serv5/src/schemas/cv.py) and [src/schemas/job.py](file:///c:/Users/NV_USER/Desktop/AI-Serv5/src/schemas/job.py).
- Deleted obsolete directory `src/api/schemas/`.

### 4. Repository Consolidation
- Consolidated persistence repositories into canonical package [src/db/repositories/](file:///c:/Users/NV_USER/Desktop/AI-Serv5/src/db/repositories/).
- Merged abstract `JobRepository(ABC)` interface and `DatabaseJobRepository` inside [src/db/repositories/job_repository.py](file:///c:/Users/NV_USER/Desktop/AI-Serv5/src/db/repositories/job_repository.py).
- Moved `candidate_repository.py`, `behavior_repository.py`, and `mock_job_repository.py` into `src/db/repositories/`.
- Fixed project-root path resolution and timezone-aware datetime handling in `mock_job_repository.py`.
- Deleted obsolete directory `src/repositories/`.

### 5. Security & Rate-Limiting Harmonization
- Merged `src/api/security.py` into canonical [src/core/security.py](file:///c:/Users/NV_USER/Desktop/AI-Serv5/src/core/security.py) and deleted `src/api/security.py`.
- Preserved dual-layer rate limiting:
  - Central `RateLimitMiddleware` on feature endpoints.
  - Route-level `Depends(check_rate_limit)` on CV endpoints returning `ExtractionErrorResponse` (HTTP 429) to honor its established API contract.
- Added dual attribute resolution (`enable_api_key_auth`/`ENABLE_API_KEY_AUTH`, `rate_limit_per_minute`/`RATE_LIMIT_REQUESTS`) to support both environment configuration and pytest monkeypatching.

### 6. Settings Consolidation
- Consolidated all `AppSettings` fields directly onto the canonical [Settings](file:///c:/Users/NV_USER/Desktop/AI-Serv5/src/core/config.py#L155) class in [src/core/config.py](file:///c:/Users/NV_USER/Desktop/AI-Serv5/src/core/config.py).
- Created clean aliases `AppSettings = Settings` and `get_app_settings() -> Settings: return settings`.
- Updated `TAXONOMY_PATH` references across services to use `settings.TAXONOMY_PATH`.

### 7. Database Initialization & Alembic Migrations
- Cleaned up duplicate database initialization: removed module-level `init_db()` in `src/api/main.py`; retained canonical initialization inside the FastAPI `lifespan`.
- Audited backend database contract (`SkillMatch_Database_Schema.pdf`) and classified all entities by AI scope.
- Configured canonical Alembic migration architecture:
  - Created [alembic.ini](file:///c:/Users/NV_USER/Desktop/AI-Serv5/alembic.ini) pointing to `src/db/migrations`.
  - Created [src/db/migrations/env.py](file:///c:/Users/NV_USER/Desktop/AI-Serv5/src/db/migrations/env.py), [script.py.mako](file:///c:/Users/NV_USER/Desktop/AI-Serv5/src/db/migrations/script.py.mako), and package `__init__.py`.
# Agent Action History

This document serves as a persistent memory of the agent's actions, decisions, and progress within the project.

## 2026-09-15 - Initial Setup
- Created this `Agent.md` file to track the history of actions and decisions.

## 2026-09-15 - Codebase Scan
- Scanned the root directory and `src/` directory to understand the project structure.
- Read the `README.md` which details the "SkillMatch — AI Features" technical report, including architecture, design patterns, and feature map.
- Identified the core stack: FastAPI, LangChain, LlamaIndex, Python 3.11+.
- Located key directories: `src/api` (FastAPI routes), `src/ai` (LangChain orchestration, chains, tools, prompts), `src/services`, `src/schemas`, `src/db`, and `src/workers`.
- The AI layer is designed with a strategy pattern for LLMs, facade pattern for capabilities, and heavily relies on Pydantic schemas for output parsing.

## 2026-09-15 - YouTube Learning Resources Pipeline
- Implemented an offline batch pipeline to fetch curated YouTube videos for skill gaps.
- Created `SkillResourceModel` in `src/db/models/skill_resource.py` to store fetched videos in the database.
- Registered the new model with SQLAlchemy in `src/db/base.py`.
- Enriched `RoadmapTask` and `SkillMatchItem` schemas in `src/schemas/roadmap.py` and `src/schemas/match.py` to include a rich `ResourceLinkSchema`.
- Developed `src/workers/youtube_fetcher.py` which iterates through the canonical taxonomy, searches YouTube via the Data API v3, and pushes pending items to the `ReviewQueueRepository`.
- Modified `ReviewQueueService.resolve_item` in `src/services/review_queue_service.py` to handle `youtube_resource` items. When approved by an admin, resources are written to the `skill_resources` table.
- Updated `RoadmapService._enrich_roadmap_with_resources` to automatically retrieve approved resources from the database and attach them to generated roadmaps.

## 2026-09-20 - Structural Consolidation & Architecture Refactoring (AI-Serv5)

Conducted a thorough structural cleanup and architectural consolidation of SkillMatch AI Services (`AI-Serv5`), aligning persistence with the target backend schema (`SkillMatch_Database_Schema.pdf`), de-duplicating architecture layers, and standardizing error handling and configuration, while strictly preserving the canonical `get_llm()` runtime and all AI business logic.

### 1. Provider-Neutral API Error Handling
- Removed direct provider-specific knowledge (`import groq`, `groq.GroqError`, `GROQ_API_KEY` messages) from [src/api/main.py](file:///c:/Users/NV_USER/Desktop/AI-Serv5/src/api/main.py).
- Implemented generic, provider-neutral LLM error inspection at the API layer returning `LLM_AUTHENTICATION_ERROR` (401), `LLM_RATE_LIMIT_ERROR` (429), and `LLM_GATEWAY_ERROR` (502).
- Removed legacy `DynamicLLMMiddleware` from FastAPI application mounting.

### 2. Router Consolidation
- Audited and merged legacy routers in `src/api/routers/` (`cv_router.py`, `job_router.py`) with [src/api/v1/endpoints/](file:///c:/Users/NV_USER/Desktop/AI-Serv5/src/api/v1/endpoints/).
- Added canonical endpoint [src/api/v1/endpoints/jobs.py](file:///c:/Users/NV_USER/Desktop/AI-Serv5/src/api/v1/endpoints/jobs.py) for `/api/v1/jobs/analyze`.
- Unified all 23 endpoints under canonical router aggregator [src/api/v1/routers.py](file:///c:/Users/NV_USER/Desktop/AI-Serv5/src/api/v1/routers.py).
- Deleted obsolete directory `src/api/routers/` with zero broken imports.

### 3. Schema Consolidation
- Audited schemas in `src/api/schemas/` (`cv_schemas.py`, `job_schemas.py`) against `src/schemas/`.
- Consolidated all DTOs, request models, response models, and error responses into canonical [src/schemas/cv.py](file:///c:/Users/NV_USER/Desktop/AI-Serv5/src/schemas/cv.py) and [src/schemas/job.py](file:///c:/Users/NV_USER/Desktop/AI-Serv5/src/schemas/job.py).
- Deleted obsolete directory `src/api/schemas/`.

### 4. Repository Consolidation
- Consolidated persistence repositories into canonical package [src/db/repositories/](file:///c:/Users/NV_USER/Desktop/AI-Serv5/src/db/repositories/).
- Merged abstract `JobRepository(ABC)` interface and `DatabaseJobRepository` inside [src/db/repositories/job_repository.py](file:///c:/Users/NV_USER/Desktop/AI-Serv5/src/db/repositories/job_repository.py).
- Moved `candidate_repository.py`, `behavior_repository.py`, and `mock_job_repository.py` into `src/db/repositories/`.
- Fixed project-root path resolution and timezone-aware datetime handling in `mock_job_repository.py`.
- Deleted obsolete directory `src/repositories/`.

### 5. Security & Rate-Limiting Harmonization
- Merged `src/api/security.py` into canonical [src/core/security.py](file:///c:/Users/NV_USER/Desktop/AI-Serv5/src/core/security.py) and deleted `src/api/security.py`.
- Preserved dual-layer rate limiting:
  - Central `RateLimitMiddleware` on feature endpoints.
  - Route-level `Depends(check_rate_limit)` on CV endpoints returning `ExtractionErrorResponse` (HTTP 429) to honor its established API contract.
- Added dual attribute resolution (`enable_api_key_auth`/`ENABLE_API_KEY_AUTH`, `rate_limit_per_minute`/`RATE_LIMIT_REQUESTS`) to support both environment configuration and pytest monkeypatching.

### 6. Settings Consolidation
- Consolidated all `AppSettings` fields directly onto the canonical [Settings](file:///c:/Users/NV_USER/Desktop/AI-Serv5/src/core/config.py#L155) class in [src/core/config.py](file:///c:/Users/NV_USER/Desktop/AI-Serv5/src/core/config.py).
- Created clean aliases `AppSettings = Settings` and `get_app_settings() -> Settings: return settings`.
- Updated `TAXONOMY_PATH` references across services to use `settings.TAXONOMY_PATH`.

### 7. Database Initialization & Alembic Migrations
- Cleaned up duplicate database initialization: removed module-level `init_db()` in `src/api/main.py`; retained canonical initialization inside the FastAPI `lifespan`.
- Audited backend database contract (`SkillMatch_Database_Schema.pdf`) and classified all entities by AI scope.
- Configured canonical Alembic migration architecture:
  - Created [alembic.ini](file:///c:/Users/NV_USER/Desktop/AI-Serv5/alembic.ini) pointing to `src/db/migrations`.
  - Created [src/db/migrations/env.py](file:///c:/Users/NV_USER/Desktop/AI-Serv5/src/db/migrations/env.py), [script.py.mako](file:///c:/Users/NV_USER/Desktop/AI-Serv5/src/db/migrations/script.py.mako), and package `__init__.py`.
  - Created initial migration [src/db/migrations/versions/0001_initial_ai_persistence.py](file:///c:/Users/NV_USER/Desktop/AI-Serv5/src/db/migrations/versions/0001_initial_ai_persistence.py) declaring the 7 AI-owned persistence entities (`jobs`, `match_records`, `interview_sessions`, `interview_answer_evaluations`, `roadmaps`, `review_queue`, `skill_resources`).
- Exported all ORM models via [src/db/models/__init__.py](file:///c:/Users/NV_USER/Desktop/AI-Serv5/src/db/models/__init__.py).

### 8. Fixtures & Test Data
- Audited `src/fixtures/jobs_seed.json` and determined it is test/mock data; relocated to [tests/fixtures/jobs_seed.json](file:///c:/Users/NV_USER/Desktop/AI-Serv5/tests/fixtures/jobs_seed.json) and deleted `src/fixtures/`.

### 9. Skill Gap Analysis Requirement Completeness & Critical Gap Prevention (Audit Fix)
- Identified and resolved the blocker where an LLM chain might omit required skills from `skill_breakdown`, causing scoring and qualification verdict to be computed only over returned items and hiding critical skill gaps.
- Updated [src/services/matching_service.py](file:///c:/Users/NV_USER/Desktop/AI-Serv5/src/services/matching_service.py) in `apply_evaluation_rules` to:
  - Enforce 100% requirement coverage by cross-referencing all declared `required_skills` against returned items (including canonical taxonomy resolution).
  - Synthesize any omitted requirement as a missing gap with `match_score=0.0`, `is_matched=False`, and `candidate_proficiency="Missing"`.
  - Ensure all critical skills are tracked in `critical_total`, and any missing critical skill is explicitly placed in `missing_critical_skills` and `recommended_upskilling_path`.
  - Calculate `overall_match_score` and qualification verdict across all declared requirements.
- Added comprehensive unit tests in [tests/test_matching_service.py](file:///c:/Users/NV_USER/Desktop/AI-Serv5/tests/test_matching_service.py) asserting that omitted critical requirements correctly drop the match score, flag all critical gaps, and prevent false-positive `Qualified` verdicts.

### 10. Verification & Invariance Gates
- **Full Test Suite**: `pytest -q` &rarr; 235 passed, 4 skipped, 0 failures (100% pass rate).
- **Compilation**: `python -m compileall -q src` &rarr; 0 errors.
- **Git Diff**: `git diff --check` &rarr; clean, zero whitespace/line-ending issues.
- **OpenAPI / Health**: `GET /health` verified with `"active_model": "gemini-3.5-flash"` retained; `GET /openapi.json` verified with all 23 unique routes.
- **LLM Runtime**: Confirmed zero redesign; `get_llm()` remains the canonical zero-argument factory backed by LangChain `init_chat_model()`. No LiteLLM or provider routing was added.

### 11. Explainable Job Match — 5-Dimension Scoring & Response Contract Fix (Audit 3 Blocker)

Resolved the 🔴 Blocker for "Feature 3: Explainable Job Match". The previous implementation routed `POST /api/v1/matches/explain` through `analyze_skill_gap()`, which only scored core required skills. This violated the stated contract — role alignment, experience fit, preferences, and preferred skills were never evaluated, calculated, or returned.

#### Root Cause
- The `/explain` endpoint called `matching_service.analyze_skill_gap(payload)`, a method that only runs the LLM chain over required skill dimensions.
- Response fields (`role_alignment_score`, `experience_score`, `preference_fit_score`, `preferred_skills_breakdown`, `weak_skills`, `blockers`, `nice_to_have_gaps`, `score_breakdown`, `rationale`, `priority`) were present in the schema but never populated.

#### Fix Applied

**[src/schemas/match.py](file:///c:/Users/NV_USER/Desktop/AI-Serv5/src/schemas/match.py)**
- Added `target_roles`, `preferences`, and `total_years_experience` to `CandidateProfilePayload`.
- Added `preferred_skills`, `job_title`, `canonical_role`, `min_years_experience`, `work_mode`, `location`, `employment_type` to `SkillGapAnalysisRequest`.
- Added all explainability output fields to `SkillGapAnalysisResponse` (all optional, backward-compatible defaults).

**[src/services/matching_service.py](file:///c:/Users/NV_USER/Desktop/AI-Serv5/src/services/matching_service.py)**
- Extracted `_run_llm_evaluation()` — pure LLM chain call + `apply_evaluation_rules()` with no enrichment. This is called by both `analyze_skill_gap` and `explain_job_match`.
- `analyze_skill_gap()` now calls `_run_llm_evaluation()` only — pure skill-gap path, no enrichment. This preserves backward compatibility with all existing Skill Gap Analysis and Recommendation tests.
- Added `enrich_explainable_dimensions()` — deterministic 5-dimension enrichment layer:
  1. **Skills Match Score** — captured from `overall_match_score` after `apply_evaluation_rules`.
  2. **Role Alignment Score** — reuses `calculate_role_fit()` from `recommendation_scoring.py` with candidate `target_roles` vs `job_title`/`canonical_role`.
  3. **Experience Score** — tiered scoring: `>=100%` required → 100, `>=80%` → 80, `>=50%` → 50, else proportional. Adds blocker string if `< 50%` required.
  4. **Preference Fit Score** — reuses `calculate_preference_fit()` from `recommendation_scoring.py` with candidate `preferences` vs `work_mode`/`location`/`employment_type`.
  5. **Preferred Skills Score** — evaluates each `preferred_skills` entry against candidate skills. Unmatched skills go to `nice_to_have_gaps`.
  - **Composite score** (only when explainable context is present): `skills×0.50 + role×0.20 + exp×0.15 + pref×0.10 + preferred_skills×0.05`.
  - **Weak skills**: items in `skill_breakdown` with `0 < score < 70`.
  - **Blockers**: missing critical skills + experience deficit messages.
  - **Priority**: `"high"` (Qualified, no blockers), `"low"` (Not Qualified or ≥2 blockers), `"medium"` otherwise.
  - **Rationale**: synthesized natural-language summary.
- Added `explain_job_match()` — calls `_run_llm_evaluation()` then `enrich_explainable_dimensions()` exactly once.
- Fixed double-enrichment bug: initial version of `explain_job_match` called `analyze_skill_gap()` (which was enriching) and then enriched again, compounding the composite score. Fixed by giving `analyze_skill_gap` back to pure evaluation.
- Fixed `evaluate_match()` (used by recommendation pipeline) to NOT construct a `SkillGapAnalysisRequest` from a raw `Candidate` DB model (which caused `ValidationError`). This fast-path returns the plain `apply_evaluation_rules` result only.

**[src/api/v1/endpoints/matches.py](file:///c:/Users/NV_USER/Desktop/AI-Serv5/src/api/v1/endpoints/matches.py)**
- Changed `POST /api/v1/matches/explain` handler to call `matching_service.explain_job_match(payload)` instead of `matching_service.analyze_skill_gap(payload)`.

**[tests/test_matching_service.py](file:///c:/Users/NV_USER/Desktop/AI-Serv5/tests/test_matching_service.py)**
- Added `test_explainable_match_covers_all_dimensions`: asserts all 5 dimension scores, `preferred_skills_breakdown`, `nice_to_have_gaps`, composite `overall_match_score`, `priority="high"`, and rationale text.
- Added `test_explainable_match_experience_and_critical_blockers`: asserts experience deficit blocker, missing critical skill blocker, weak skills list, `priority="low"`, and `Not Qualified` verdict.

**[tests/test_matching_api.py](file:///c:/Users/NV_USER/Desktop/AI-Serv5/tests/test_matching_api.py)**
- Updated `test_matching_api_explain_endpoint` to patch `matching_service.explain_job_match` (was incorrectly patching `analyze_skill_gap`).

#### Verification
- `pytest tests/test_matching_service.py tests/test_matching_api.py -v` &rarr; **13/13 passed**.
- `pytest -q` (full suite) &rarr; **237 passed, 4 skipped, 0 failures**.
