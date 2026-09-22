# AI and Job Aggregation Audit Report

Date: 2026-09-17  
Repository: Team-2-Skill-Project/AI  
Reviewed commit: 699f780  
Scope: AI only. The job-data pipeline is included only where it supplies or affects AI inputs; Flutter, general backend, authentication, and admin features are outside this audit.  
Specification source: SkillMatch_Project_Features_and_Deliverables_EN (1).pdf, pages 9–15, 18, and 20.

## Executive Summary

The current repository is not ready to be accepted as an AI MVP.

The main problem is not only that several features are incomplete. The repository does not currently provide a unified, reproducible, working LLM runtime. It contains LLM abstractions and calls to init_chat_model, but:

- The current environment is invalid: LLM_PROVIDER=groq while LLM_MODEL_NAME is empty, so the runtime falls back to gemini-3.5-flash and constructs ChatGroq.
- The requested contract was three generic variables: LLM_BASE_URL, LLM_MODEL_NAME, and LLM_API_KEY. The implementation still depends on LLM_PROVIDER and provider-specific adapters.
- custom and vllm are accepted by configuration validation, but the installed LangChain runtime rejects custom as an actual provider.
- The runtime dependencies used by the source code are not fully declared in requirements.txt.
- The AI Mentor is not implemented: there is no usable schema, chain, route, history, or context builder.
- Matching can return an incorrect qualified result when the LLM omits a requirement. This was reproduced with a critical missing skill.
- The review queue exists as a partial structure, but it is not connected to all low-confidence extraction/enrichment paths or all match paths.
- Several data-facing outputs are hardcoded or synthetic when source evidence is absent: Candidate, Organization, remote/full_time, synthetic match evidence, generic recommendation text, Core Fundamentals, placeholder documentation URLs, and fake YouTube IDs.

Therefore, the green tests do not prove that production AI works. They mainly prove that some deterministic logic, schema logic, and mocked flows work.

## Tests Run

### Test suite

| Test | Result |
|---|---|
| pytest -q -rs | 233 passed, 4 skipped, 1 warning, in 44.51 seconds |
| Targeted API tests | 57 passed, in 78.81 seconds |
| ruff check src tests --statistics | 366 issues: 149 I001, 114 E402, 58 F401, 41 W293, 2 F841, 1 E741, 1 F541 |
| python -m compileall -q src | PASS |
| pip check | FAIL: the current environment contains multiple dependency conflicts; this is additional evidence that the declared install is not reproducible |

The targeted API suite covered CV, general API endpoints, matching, job extraction, roadmap, review queue, recommendations, and logging/error handling.

The four skipped tests are all Redis-dependent and were skipped because Redis was unavailable. No test in this run proves a real provider call. The current environment also reports package conflicts from installed tooling, including incompatible protobuf, pydantic/ruff, click, dotenv, tokenizers, and transformers requirements. The repository still has the more fundamental problem that the AI/runtime dependencies are missing from its own requirements.txt.

### Direct FastAPI API smoke test

TestClient was run against the actual FastAPI application without calling an external provider or consuming a real API key:

| Request | Result |
|---|---:|
| GET / | 200 |
| GET /openapi.json | 200 |
| GET /health | 200 |
| GET /api/v1/recommendations/feed with default candidate | 200, returns cand_001 with total_results=0 and an empty list |
| GET /api/v1/recommendations/feed?candidate_id=does_not_exist | 404 |
| POST /api/v1/jobs/analyze with missing data | 422 |
| POST /api/v1/matches/analyze with missing data | 422 |
| POST /api/v1/roadmap/generate with missing data | 422 |
| POST /api/v1/interview/generate with missing data | 422 |
| Number of OpenAPI paths | 23 |
| OpenAPI paths containing mentor | None |

This smoke test proves routing and validation only. It does not prove successful real-LLM execution because the current configuration is invalid and many existing tests mock the LLM layer.

## Evidence That There Is No Valid Working LLM Integration

### Actual environment state

The following environment state was observed at review time. The secret value itself was not exposed:

| Variable | State |
|---|---|
| LLM_PROVIDER | groq |
| LLM_API_KEY | Set |
| LLM_MODEL_NAME | Empty |
| LLM_BASE_URL | Empty |

The runtime resolves this to:

| Value | Result |
|---|---|
| Provider | groq |
| Model | gemini-3.5-flash |
| Client class | ChatGroq |
| Base URL | Not set |

This is not a valid setup: a Gemini model name is being sent through a Groq client. In addition, LLM_MODEL_NAME is described in src/core/config.py as deprecated in favor of LLM_MODEL, which contradicts the requested contract.

### Implementation problems

1. src/core/config.py reads and branches on provider, with provider-specific key fallbacks, instead of using a single generic three-variable contract.
2. src/core/llm.py passes the configured provider into init_chat_model. This means a model string such as groq/model-name cannot reliably select its provider when a global provider is already configured.
3. custom is accepted by validation, but the actual runtime raises:

~~~text
init_chat_model(model="any-model", model_provider="custom", ...)
ValueError: Unsupported provider='custom'.
~~~

4. requirements.txt does not declare important packages used by the source code, including langchain, langchain-core, langchain-openai, langchain-groq, pydantic-settings, sqlalchemy, redis, celery, and the other provider adapters.
5. Some of these packages happen to be installed in the current development environment outside the declared requirements. A fresh clone/install therefore is not reproducible.
6. DynamicLLMMiddleware is currently a request-header override middleware, not a generic environment-driven LLM middleware. When overrides are enabled, it reads x-llm-api-key and x-llm-api-token from requests. This must not be public production behavior.

### Required LLM contract

The requested configuration is:

~~~text
LLM_BASE_URL=
LLM_MODEL_NAME=
LLM_API_KEY=
~~~

These variables must be the source of truth. The realistic way to support any model from any vendor with these three variables is to support any endpoint that follows the OpenAI-compatible Chat Completions protocol. APIs with a different protocol require a dedicated adapter; three variables alone cannot infer an entirely different protocol.

The middleware/factory must:

- Use LLM_BASE_URL, LLM_MODEL_NAME, and LLM_API_KEY directly.
- Use one OpenAI-compatible client path and not require LLM_PROVIDER for normal operation.
- Treat LLM_PROVIDER as optional metadata or an internal adapter selector only, not as an override of the three variables.
- Fail fast with a clear configuration error at startup or through a health check when the configuration is incomplete.
- Prevent public client request headers from changing the model, base URL, or API key in production.
- Include a local fake OpenAI-compatible model smoke test without an external API key.

## How the Features Actually Work Without a Working LLM

| Feature | What actually runs | Assessment |
|---|---|---|
| CV extraction | Attempts the LLM, then uses a heuristic fallback in src/cv_extractor/llm_extractor.py. The fallback extracts text patterns but does not fulfill the complete contract. | Partially works and can look successful without an LLM |
| Job Description Understanding | Pipeline and endpoint exist, but the LLM extractor has no equivalent reliable fallback. Without a valid LLM this is not production-ready. | Partial and dependent on an invalid LLM setup |
| Explainable Match | Deterministic scoring runs, while explanation uses the LLM optionally. This is why some tests pass without an LLM. | Exists, but has contract and correctness problems |
| Skill Gap | Uses an LLM response followed by deterministic post-processing. A missing requirement can be silently omitted. | Broken in important cases |
| Recommendations | Deterministic ranking and explanations, with MockBehaviorRepository as the default in service paths. | Demo logic, not production personalization |
| AI Mentor | No implementation in src and no route in OpenAPI. | Not implemented |
| Roadmap | Attempts the LLM, then uses a deterministic fallback that creates ungrounded gaps/resources and placeholder links. | Partial and misleading on fallback |
| Interview coach | Chains and endpoints exist, but they are LLM-dependent and are not the Mentor. | Partial |
| Human review | Queue logic covers some match, interview, and resource cases only. It is not a complete quality gate. | Partial and not fully wired |

## AI-Facing Assessment of Job Aggregation & Scraping Features

This section is included only because job data is a direct input to job understanding, matching, recommendations, roadmap generation, and the Mentor. It is not a general backend/operations audit. The existing implementation is a small Jooble integration, not a complete AI-ready data-ingestion path.

| PDF requirement | Status | Evidence and problem |
|---|---|---|
| Approved Source Registry | ❌ Not implemented | There is JOOBLE_API_KEY and a Jooble module, but no admin-manageable source registry or source-control API. |
| Scheduled Collection | ❌ Not implemented | JoobleIngestionService.ingest() is only a callable service. There is no route or scheduled worker/Celery beat collection job. |
| Listing Discovery | 🟡 Partial | Jooble search fetches one page only (page=1) with a limit; there is no pagination/result navigation. |
| Job Detail Extraction | 🟡 Partial | The Jooble payload is normalized, but there is no detail-page fetch/parser. Deadline, application URL, experience, and other fields may be missing. |
| Normalization | 🟡 Partial | RawJoobleJob and normalize_jooble_job exist with source URL and external ID, but there is no complete multi-source normalization or sufficient preservation of original values. |
| Skill and Requirement Enrichment | 🟡 Partial | JoobleIngestionService accepts an optional extraction pipeline, but it is not connected to a real operational execution path. |
| Duplicate Detection | 🟡 Partial | Deduplication is only within a batch by external ID or URL; there is no company/title similarity or full content fingerprint. |
| Update Detection | 🟡 Partial | Upsert exists for the same source, but there is no version history or diff for description, deadline, application URL, or state changes. |
| Freshness and Expiration | ❌ Not implemented | ingested_at exists, but the Jooble normalizer sets posted_at=None and there is no last_seen or stale/expired workflow. |
| Source Health Monitoring | ❌ Not implemented | No persisted collection runs, success/failure rate, dashboard, or retry monitor exists. |
| Retry and Failure Isolation | 🟡 Partial | The Jooble client is explicitly non-retrying. Extraction failures are caught per job, but source-run retries are not implemented. |
| Responsible Collection Rules | 🟡 Unverified | Using an API is better than bypass scraping, but there is no documented layer for rate limits, terms, robots, or source policies. |
| Manual/File Import Fallback | ❌ Not implemented | There is no operational path for manual job entry or structured file import. |
| End-to-end ingestion delivery | ❌ Incomplete | No OpenAPI endpoint exposes Jooble ingestion, and there is no scheduler or admin visibility. |

Conclusion: an adapter, normalizer, and repository tests exist, but there is no complete operational pipeline from collection through refresh and source monitoring. AI data quality is therefore not guaranteed.

## Assessment of AI Features – Useful, Actionable and Explainable

| PDF feature | Status | Assessment |
|---|---|---|
| 1. CV Profile Extraction | 🟡 Partial | A structured Candidate, heuristic fallback, and skill evidence/confidence exist. There is no confidence/evidence for every important field, no clear profile version, and no user correction workflow before the profile affects downstream features. |
| 2. Job Description Understanding | 🟡 Partial | POST /api/v1/jobs/analyze and a normalization/classification pipeline exist. There is no reliable LLM fallback, no complete downstream representation for preferred skills/constraints/evidence, and the endpoint is synchronous despite the project background-work requirement. |
| 3. Explainable Job Match | 🔴 Blocker | Score, explanation, and routes exist, but scoring does not cover the full role alignment, experience, preferences, and preferred-skill requirements. The response contract is incomplete and has the correctness bug documented below. |
| 4. Skill Gap Analysis | 🔴 Blocker | Chain and post-processing exist, but the response may not contain every requirement while scoring/verdict are calculated from only the returned items. Critical gaps can be hidden. |
| 5. Personalized Job Recommendations | 🟡 Partial | Ranking, deduplication, and deterministic recommendation reasons exist. The default behavior repository is mock/in-memory, freshness is unreliable, behavior scoring is simplistic, and the cache module is not used by the service. |
| 6. AI Mentor Chatbot | ❌ Not implemented | src/schemas/mentor.py is a placeholder. There is no Mentor chain, /mentor/message, history, suggested prompts, SSE, context assembler, tools, or guardrails. |
| 7. Dynamic Career Roadmap | 🔴 Partially broken | Generate/refresh, phases, milestones, and tasks exist, but grounding validation is weak, fallback adds an ungrounded gap and placeholder links, and refresh may lose completed tasks. |
| 8. CV Improvement Assistant | ❌ Not implemented | No clear chain or endpoint exists for evidence-based CV recommendations and truthful rewriting. |
| 9. Interview Preparation Coach | 🟡 Partial | Generate/evaluate chains and API exist, but the feature is LLM-dependent, is not connected to the Mentor, and answer evaluation does not pass through the full review policy. |
| 10. Application Strategy Guidance | ❌ Not implemented | There is no clear apply-now / improve-first / alternative-roles flow with reasoning. |
| 11. Roadmap Progress Review | 🟡 Partial | Task completion and refresh exist, but there is no periodic comparison of CV evidence, applications, and new skills to determine the next highest-value action. |
| 12. AI Data Quality Assistant | 🟡 Partial and not fully wired | Review queue logic covers some match and resource cases, but CV/JD low-confidence results are not comprehensively enqueued and direct match routes can bypass the queue. There is no complete confidence audit. |

## Assessment of How the AI Mentor Should Actually Work

The PDF requires a Mentor grounded in real user context, not a generic chatbot. The current state is:

| Required behavior | Status |
|---|---|
| Candidate profile and verified CV | ❌ No Mentor context builder or verified-context contract |
| Target role and preferences | ❌ |
| Selected, saved, and applied jobs | ❌ |
| Match reports and prioritized skill gaps | ❌ |
| Current roadmap, completed milestones, and notes | ❌ |
| Application statuses | ❌ |
| Goal clarification | ❌ |
| Weekly action planning | ❌ |
| Job-specific advice | ❌ |
| Roadmap adjustment after profile/target/progress changes | 🟡 A separate refresh exists, not Mentor behavior, and it may lose completed tasks |
| Application debrief | ❌ |
| Interview readiness based on role and gaps | 🟡 A separate Interview Coach exists, not the Mentor |
| Truthfulness and no invented qualifications | 🟡 Some prompts contain guardrails, but there is no Mentor output policy or auditable evidence links |
| Conversation history | ❌ |
| Suggested prompts | ❌ |
| Contextual answers and job/roadmap links | ❌ |
| Fallback and safety behavior | ❌ As a Mentor feature |

The API smoke test confirms that no OpenAPI path contains mentor.

## Assessment of Expected AI Deliverables

| Expected deliverable in PDF | Status |
|---|---|
| Structured CV output | 🟡 Partially present; confidence/evidence are not consistent across all fields |
| Structured job requirement output | 🟡 Partially present; not a complete stable contract for all downstream consumers |
| Match result contract | 🔴 Incomplete and unsafe; does not guarantee requirement completeness |
| Skill-gap result | 🔴 Exists but can hide gaps and has weak linkage to roadmap actions |
| Recommendation result | 🟡 Deterministic result exists, but it depends on mock behavior and weak freshness data |
| Mentor context and conversation behavior | ❌ Not present |
| Roadmap model | 🟡 Present, but grounding, refresh, and progress are incomplete |
| CV improvement output | ❌ Not present |
| Interview preparation output | 🟡 Partially present |
| Confidence and human-review rules | 🟡 Partially present, but low-confidence extraction/enrichment is not comprehensively reviewable |

The PDF acceptance principle is Result + Reason + Evidence + Confidence + Recommended Action. This format is not applied consistently across the AI outputs.

## Required Implementation Flow for Every AI Feature

This is the implementation flow the team should follow. A feature is not complete merely because a chain, schema, or endpoint exists; the whole path from verified input to persisted, explainable output must work.

### Shared AI execution pipeline

Every AI feature must use the same sequence:

~~~text
Authenticated request and real entity IDs
        ↓
Load canonical, versioned profile/job/application context
        ↓
Validate input completeness, ownership, freshness, and source status
        ↓
Call the shared LLM middleware using LLM_BASE_URL, LLM_MODEL_NAME, LLM_API_KEY
        ↓
Parse strict structured output into the feature's Pydantic contract
        ↓
Run deterministic validation, grounding, completeness, and score rules
        ↓
Attach field-level evidence, confidence, provenance, model/prompt fingerprints
        ↓
Route low-confidence, contradictory, or risky results to human review
        ↓
Persist the approved/versioned result and its audit trail
        ↓
Return result + reason + evidence + confidence + recommended action
~~~

Non-negotiable rules:

- The normal runtime source of truth is only `LLM_BASE_URL`, `LLM_MODEL_NAME`, and `LLM_API_KEY`. `LLM_PROVIDER` may be optional adapter metadata, but it must not override the generic contract.
- A provider-compatible client must be selected by the configured endpoint/model contract. Provider SDK calls must not be scattered through individual features.
- The LLM may extract, classify, explain, or suggest. It must not silently determine final match scores, bypass required fields, or invent evidence.
- Missing data must remain `null`/`unknown` with a confidence and reason. It must never become a plausible-looking name, employer, role, skill, URL, score, or qualification.
- A fallback must be explicitly marked as degraded or `needs_review`; it must not look identical to successful LLM output.
- Every persisted result must reference the input versions it used, the model name, prompt/schema version, timestamp, extraction method, evidence, and review status.

### AI-facing job aggregation and enrichment flow

This is the upstream flow required before job-based AI features are allowed to consume a posting:

1. Register an approved source with its terms, rate limits, parser, and health policy.
2. Run a scheduled or manually triggered collection job with a durable collection-run ID.
3. Store the raw source response and attribution before transformation.
4. Normalize title, company, description, location, work mode, employment type, experience, dates, application URL, and source identifiers without inventing missing fields.
5. Deduplicate using source URL/external ID plus company/title similarity and content fingerprints.
6. Detect updates, persist versions/diffs, update `last_seen`, and mark stale/expired records.
7. Send a complete description to JD Understanding for role, seniority, required/preferred skills, responsibilities, constraints, taxonomy IDs, evidence, and confidence.
8. Quarantine incomplete or low-confidence jobs and send them to the review queue before matching/recommendations.
9. Publish only an approved enriched version to downstream AI consumers, with source URL and freshness visible.
10. Isolate one source/job failure, retry safely, and expose run health and failure reasons to administrators.

### Feature 1 — CV Profile Extraction

~~~text
Upload CV → validate filename/content signature/size/security
        → extract digital text or OCR scanned pages
        → call structured CV extraction
        → normalize skills/roles/degrees using versioned taxonomy
        → link every field to source text/page/span
        → calculate field-level confidence and extraction method
        → queue low-confidence/contradictory fields for review
        → show candidate a review/edit/confirm screen
        → persist confirmed profile version and source document
        → publish the version to matching, recommendations, roadmap, and Mentor
~~~

Required output: name, contact-safe profile data, role history, companies, dates, skills, experience, education, projects, certifications, target roles, evidence, confidence, and source metadata. If a field is not present, return unknown; do not return `Candidate`, `Organization`, inferred credentials, or fabricated evidence. Async extraction must use a durable job record and must survive restarts.

### Feature 2 — Job Description Understanding

~~~text
Approved/raw job version → verify description completeness and provenance
        → extract role family/title/seniority/experience/constraints
        → extract required and preferred skills/responsibilities
        → normalize each skill to taxonomy or preserve as unresolved
        → attach evidence spans and confidence to every extracted claim
        → validate/deduplicate requirements and criticality
        → human review when confidence is low or fields conflict
        → persist enriched job-requirement version
        → make only approved complete versions matchable/recommendable
~~~

Required output must preserve required versus preferred skills, minimum experience, responsibilities, work constraints, evidence, confidence, source version, and enrichment status. Missing work mode, employment type, criticality, or proficiency must remain unknown rather than defaulting to `remote`, `full_time`, `Intermediate`, or optional.

### Feature 3 — Explainable Job Match

~~~text
Verified candidate profile version + approved enriched job version
        → load target role/preferences and applicable constraints
        → build a complete canonical requirement set
        → normalize and deduplicate requirements
        → deterministically evaluate every required/preferred item
        → calculate role alignment, experience, preference, blocker, and skill scores
        → optionally ask LLM for explanations/actions only
        → validate every explanation against candidate/job evidence
        → prevent Qualified when requirements are missing or input is incomplete
        → attach strengths, gaps, blockers, reasons, evidence, confidence
        → review borderline/high-risk results
        → persist result against both input versions
~~~

The LLM response must not be the source of truth for completeness or the final score. If the LLM omits a requirement, the system must add it as unknown/missing. The result must contain a stable match ID, matched/missing/weak requirements, preferred-skill coverage, role/experience/constraint reasoning, evidence references, confidence, and recommended next action.

### Feature 4 — Skill Gap Analysis

~~~text
Approved match result → collect all missing/weak/unknown requirements
        → classify each gap as missing/weak/blocked/uncertain
        → assign importance, required level, candidate level, and confidence
        → link source evidence and the reason for the gap
        → create stable gap IDs
        → generate evidence-backed actions/resources
        → send uncertain gaps to review
        → persist a versioned gap artifact
        → expose the same gap IDs to roadmap and Mentor
~~~

The gap artifact must not be only a list of strings. It must preserve the canonical skill ID/name, required and current level, importance, evidence, confidence, blocker status, recommended action, resource provenance, and links to roadmap milestones and Mentor context.

### Feature 5 — Personalized Job Recommendations

~~~text
Authenticated candidate + confirmed profile + current behavior events
        → load approved active/fresh jobs and enriched requirements
        → exclude applied/dismissed/ineligible/duplicate/expired jobs
        → compute match, role, experience, preference, freshness, and behavior signals
        → apply a versioned scoring policy and calibration checks
        → generate reasons only from actual signals/evidence
        → expose uncertainty when job data or behavior is missing
        → persist/cache with input and policy versions
        → record impression/click/save/apply/dismiss feedback
        → refresh ranking from real events, not mock state
~~~

The feed must use a database-backed candidate and interaction store, real application state, source freshness, and approved job versions. A missing candidate must be a clear error; it must not silently become `cand_001`. A recommendation must never be returned as applied=false when the persisted event says it was applied.

### Feature 6 — AI Mentor Chatbot

~~~text
Authenticated conversation + candidate goal/message
        → load verified profile/CV and target role/preferences
        → load selected/saved/applied jobs and application statuses
        → load match reports, prioritized gaps, roadmap/progress, and notes
        → identify missing context and clarify the user's goal
        → call the shared LLM with bounded context and approved tools
        → return structured answer, evidence links, actions, and referenced entities
        → validate claims against stored facts and block invented qualifications
        → persist user/assistant messages, context snapshot, and result metadata
        → provide safe fallback when context/LLM is unavailable
~~~

Mentor actions must be linked to real jobs, gaps, roadmap tasks, or applications. The Mentor must support weekly planning, job-specific advice, roadmap adjustment, application debrief, interview readiness, and suggested prompts. It must say when it lacks evidence instead of filling the gap with generic career claims.

### Feature 7 — Dynamic Career Roadmap

~~~text
Verified target role + approved profile baseline + approved skill-gap IDs
        → prioritize gaps by role importance, blockers, current level, and user constraints
        → generate phases, milestones, measurable weekly tasks, and completion criteria
        → validate every cited gap against the input gap IDs
        → verify resources and retain source/title/URL provenance
        → review low-confidence plan/resources before publication
        → persist roadmap, task versions, and progress events transactionally
        → accept completion only with evidence/user confirmation where required
        → refresh by merging new gaps while preserving completed history
        → expose current roadmap/progress to Mentor and progress review
~~~

No-gap or missing-context cases must ask for a target role or verified gaps; they must not invent `Core Technical Fundamentals`, `Advanced Career Progression`, or `Software Engineer`. Refresh must append/reprioritize while retaining completed tasks, evidence, notes, and audit history.

### Feature 8 — CV Improvement Assistant

~~~text
Confirmed CV version + target job/version + match/gap evidence
        → identify concrete evidence-backed weaknesses
        → propose section-level changes and truthful rewrites
        → attach each suggestion to source CV evidence and target requirement
        → mark missing evidence instead of inventing achievements/metrics
        → validate length, format, and claim consistency
        → let the user accept/edit/reject each change
        → persist a new CV version with before/after and audit trail
~~~

The assistant may improve wording and ordering, but it must never add an employer, qualification, project, technology, metric, certification, or responsibility that is not supported by the confirmed profile or user-provided evidence.

### Feature 9 — Interview Preparation Coach

~~~text
Real candidate + real job + target role + match/gap context
        → create a durable interview session
        → generate 3–5 role-specific questions with type/skill/rubric
        → persist questions and session context
        → accept an answer bound to the session/candidate/question
        → evaluate quality and security with bounded 1–10 scores
        → return strengths, improvements, ideal outline, risks, mitigations, confidence
        → enqueue low-confidence/security-risk evaluations for review
        → persist answer/evaluation and feed trends to Mentor/roadmap
~~~

The coach must load actual job requirements rather than use a generic summary. Question count, question type, answer ownership, score ranges, and security fields must be validated before persistence.

### Feature 10 — Application Strategy Guidance

~~~text
Candidate + approved job + match/gap/evidence + preferences + application history
        → evaluate readiness, blockers, freshness, constraints, and alternatives
        → classify action: apply now, improve first, or consider alternative role
        → explain the classification with concrete evidence and confidence
        → provide a bounded action plan and no-guarantee language
        → persist the decision with input versions and timestamp
        → update strategy after application outcome or profile/roadmap change
        → expose the decision and next action to Mentor
~~~

The feature must not promise interviews/jobs or infer readiness from a percentage alone. It must distinguish hard blockers from learnable gaps and must preserve the candidate's final decision.

### Feature 11 — Roadmap Progress Review

~~~text
Current roadmap/progress events + updated CV evidence + new skills + applications/outcomes
        → compare baseline and current verified evidence
        → identify completed, stale, unproven, or newly relevant gaps
        → calculate milestone/task progress from stored evidence and confirmations
        → recommend the single highest-value next action plus alternatives
        → update roadmap priorities without deleting history
        → persist a review snapshot and expose it to Mentor
~~~

Task status alone is not enough. The review must connect progress to evidence, applications, target role changes, and newly approved skills, and must explain why the next action changed.

### Feature 12 — AI Data Quality Assistant and Human Review

~~~text
Every extraction/enrichment/match/interview/resource result
        → run confidence, completeness, contradiction, duplicate, and safety rules
        → create a review item with type, target ID, input/result versions, evidence,
          confidence, reasons, priority, and suggested correction
        → enforce pending → claimed → approved/rejected state transitions
        → require authorized reviewer ownership and immutable audit events
        → apply approved corrections to the source entity and invalidate dependents
        → block downstream publication while required review is pending
~~~

Review is part of the data pipeline, not a separate list that has no effect. Resolving a CV/JD/match/resource item must update the consumed record, result versions, caches, and downstream roadmap/recommendation/Mentor context.

### Cross-feature dependency graph

~~~text
CV document ──→ confirmed candidate profile version ───────────────┐
                                                                    │
Job source ──→ normalized job ──→ approved JD requirement version ──┼─→ deterministic match
                                                                    │          │
                                                                    │          ├─→ structured skill gaps
                                                                    │          │       ├─→ dynamic roadmap/progress review
                                                                    │          │       └─→ Mentor context
                                                                    │          ├─→ explainable recommendations ──→ behavior feedback
                                                                    │          └─→ interview/application strategy
                                                                    │
All branches ──→ evidence + confidence + review gate + versioned persistence
~~~

The team should implement and test this graph as one connected happy path. Isolated endpoints with mocked repositories or caller-supplied strings do not satisfy the PDF deliverables.

## Target AI Architecture and Implementation Blueprint

The following is the minimum architecture required to turn the current skeleton into a reliable AI subsystem. It is intentionally provider-neutral and keeps deterministic business rules outside the model.

~~~text
API / authentication / request validation
                    ↓
Feature application service and context builder
                    ↓
Canonical versioned domain entities
                    ↓
Shared LLM Gateway (OpenAI-compatible protocol)
                    ↓
Strict structured-output parser
                    ↓
Grounding + completeness + deterministic policy validators
                    ↓
Confidence/evidence/provenance assembler
                    ↓
Review gate and approval state machine
                    ↓
Transactional persistence + cache invalidation + audit event
                    ↓
API response / async job result / Mentor context
~~~

### Layer responsibilities

| Layer | Must do | Must not do |
|---|---|---|
| API routers | Authenticate, authorize, validate DTOs, create an execution/job, return normalized status/errors | Build prompts, read mock data, calculate scores, or silently swallow persistence failures |
| Feature services | Orchestrate context loading, LLM calls, deterministic rules, review, and persistence | Invent missing data or contain provider-specific branches |
| Context builders | Load the exact confirmed profile/job/match/gap/roadmap/application versions required by a feature | Accept arbitrary caller text as a substitute for canonical records in production |
| LLM Gateway | Apply the three env variables, timeouts, structured output, safe retries, redaction, and normalized provider errors | Expose API keys/model overrides to public callers or decide business verdicts |
| Deterministic validators | Enforce completeness, score invariants, grounding, taxonomy, dates, ownership, and policy thresholds | Replace missing evidence with generated prose |
| Review workflow | Hold uncertain/risky results, manage authorized claim/resolve/reject transitions, and apply corrections | Be a passive list that does not affect downstream records |
| Repositories | Persist versioned inputs/results/events transactionally and support idempotency | Use in-memory mocks or silently return success after a failed write |
| Workers | Run long AI/scraping work with durable status, retries, isolation, and correlation IDs | Return a fake completed result when the job was not actually executed |
| Observability | Record execution IDs, latency, token usage, model/config fingerprint, failures, and review rates without PII leakage | Log raw CVs, API keys, full prompts, or sensitive answers |

### Required LLM Gateway contract

The implementation should have one internal gateway, for example `LLMGateway.complete_structured(request, response_model)`. All CV, JD, matching explanations, roadmap, interview, and Mentor calls must use it.

Gateway requirements:

1. Read only `LLM_BASE_URL`, `LLM_MODEL_NAME`, and `LLM_API_KEY` for normal operation.
2. Treat an endpoint implementing the OpenAI-compatible Chat Completions protocol as the portability boundary. Three variables cannot magically translate a non-compatible vendor protocol; a separate adapter is required for such a vendor.
3. Fail readiness when the base URL/model/key combination is incomplete or impossible to initialize. Do not report `healthy` merely because FastAPI started.
4. Validate the base URL scheme and allowlist production hosts where appropriate. Never let public request headers select a model, endpoint, or secret.
5. Set explicit connect/read timeouts, bounded retries for transient failures only, and no retry for malformed requests or invalid credentials.
6. Request a JSON schema/structured response and validate the returned object with the feature's Pydantic model. Invalid JSON, missing required fields, and extra unsafe claims must be rejected or marked `needs_review`.
7. Normalize failures to provider-independent error codes such as `LLM_NOT_CONFIGURED`, `LLM_UNAVAILABLE`, `LLM_TIMEOUT`, `LLM_AUTH_FAILED`, `LLM_RATE_LIMITED`, `LLM_INVALID_OUTPUT`, and `LLM_CONTEXT_TOO_LARGE`.
8. Record model name, endpoint identity (without secrets), prompt/schema version, request ID, latency, token usage when available, and failure code.
9. Redact CV PII and secrets from logs. Keep raw prompts/results only according to an explicit retention policy.
10. Make the local fake OpenAI-compatible server the required integration-test dependency so no real vendor key is needed in CI.

`LLM_PROVIDER` may remain as optional internal metadata for a deliberate adapter registry, but it must not be required to make the generic three-variable path work and must not override `LLM_BASE_URL` or `LLM_MODEL_NAME`.

### Canonical versioned data model

The current feature chain needs explicit entities instead of unrelated JSON blobs and in-memory objects. The following records are the minimum shared vocabulary:

| Entity | Minimum required fields | Downstream consumers |
|---|---|---|
| `SourceDocument` | owner, storage reference, MIME/signature, checksum, extracted text/OCR status, created_at, retention status | CV extraction, review, audit |
| `CandidateProfileVersion` | candidate_id, version, confirmed status, fields, field evidence, field confidence, extraction method, source_document_id | matching, recommendations, roadmap, Mentor |
| `JobPostingVersion` | job/source IDs, raw reference, normalized fields, source URL, posted/expires/last_seen, fingerprint, active/stale status, version | JD extraction, freshness, recommendations |
| `JobRequirementVersion` | job_version_id, role/seniority, required/preferred skills, responsibilities, experience, constraints, taxonomy IDs, evidence, confidence, review status | matching, gaps, recommendations, Mentor |
| `MatchResult` | stable ID, candidate/profile version, job/requirement version, complete breakdown, scores, verdict, blockers, reasons, evidence, confidence, policy/model fingerprints | gaps, recommendations, review, Mentor |
| `SkillGap` | stable ID, match ID, canonical skill, required/current level, importance, gap type, evidence, confidence, action, roadmap links | roadmap, Mentor, progress review |
| `RecommendationEvent` | candidate, job/version, event type, timestamp, request/consent context | recommendation ranking, Mentor, analytics |
| `RecommendationResult` | candidate/profile version, job version, score breakdown, reasons/evidence, policy version, generated_at, expiry | feed, audit, feedback |
| `RoadmapVersion` | candidate, target role/version, source gap IDs, phases/milestones/tasks, resource provenance, status, created/updated | progress review, Mentor |
| `RoadmapProgressEvent` | roadmap/task version, actor, old/new status, evidence, note, timestamp | roadmap refresh, Mentor, audit |
| `InterviewSession` / `InterviewEvaluation` | candidate/job versions, questions, answers, bounded scores, rubric/evidence, review status | Mentor, roadmap, review |
| `MentorConversation` / `MentorMessage` | owner, goal, context snapshot/version IDs, role, message, citations/actions, safety status, timestamps | Mentor history, audit |
| `AIExecution` | execution ID, feature, input IDs/versions, model/prompt/schema fingerprints, status, duration, error, output reference | observability, retries, reproducibility |
| `ReviewItem` | item type/target, input/result versions, confidence, evidence, reasons, priority, assignee, state transitions, decision audit | all uncertain AI results |

No downstream feature should consume a bare candidate dictionary, a caller-supplied string, a mock repository, or an unversioned result when a canonical entity is required.

### Canonical AI result envelope

Every user-facing AI result should be wrapped in a consistent envelope, even when the feature has additional fields:

~~~text
{
  "result": { "feature-specific structured fields": "..." },
  "reason": "why this result was produced",
  "evidence": [
    {"source_type": "cv|job|event|user_input", "source_id": "...", "locator": "...", "quote": "..."}
  ],
  "confidence": {"overall": 0.0, "fields": {"field_name": 0.0}},
  "recommended_action": {"type": "review|confirm|learn|apply|none", "details": "..."},
  "provenance": {
    "input_versions": ["..."], "model": "...", "prompt_version": "...",
    "schema_version": "...", "extraction_method": "llm|heuristic|rule"
  },
  "review": {"status": "not_required|pending|approved|rejected", "item_id": "..."}
}
~~~

The exact JSON names can be agreed with the frontend, but the semantics must remain. A free-form summary without evidence and confidence is not an acceptable substitute.

## Bug and Problem Register

### P0 – Blocks AI MVP acceptance

#### AI-001 – No valid working LLM runtime

Location: src/core/config.py, src/core/llm.py, src/middleware/llm_middleware.py.

Problem:

- The current environment mixes Groq with a Gemini model.
- The requested environment contract is not implemented.
- custom does not work with init_chat_model.
- No fake/local provider smoke test proves that a fresh setup works.

Impact: Any LLM-dependent feature can fail at runtime or use an incompatible provider/model combination, while the tests remain green.

Acceptance criteria:

- The application starts from a fresh install using only the three requested variables.
- Changing LLM_BASE_URL to any OpenAI-compatible endpoint and changing LLM_MODEL_NAME requires no source-code change.
- A local test proves chat, structured output, and provider-error handling.
- Normal runtime does not require LLM_PROVIDER.

#### AI-002 – Mentor is missing

Location: src/schemas/mentor.py is a placeholder, and there is no Mentor router or chain.

Impact: A core MVP feature is 0% implemented; issue #7 is not complete.

Acceptance criteria:

- POST /api/v1/mentor/message or the agreed endpoint.
- GET /api/v1/mentor/history.
- Suggested prompts.
- Conversation persistence/history.
- Context builder linking candidate, job, match, gaps, roadmap, and applications.
- Structured actions linked to UI entities.
- Fallback for missing context or LLM failure, with unsupported claims prevented.

#### AI-003 – Match accepts incomplete LLM output and returns a falsely qualified result

Location: src/services/matching_service.py:61-152.

Reproduction:

- Critical requirements: Python and SQL.
- LLM response contains only Python with score 100.
- Result: verdict=Qualified, score=100.0, missing=[], and one breakdown item.

Impact: A critical skill can disappear when the LLM omits it.

Acceptance criteria:

- Build the breakdown from canonical requirements first.
- Any requirement missing from the LLM response becomes unknown or missing; it must not be deleted.
- Qualified is impossible until completeness validation passes.
- The final score is deterministic from canonical data; the LLM only explains it.

#### AI-004 – Human review is not a quality gate

Location: src/services/review_queue_service.py, src/workers/tasks.py, and direct match endpoints.

Problems:

- The CV confidence scorer calculates a score, but there is no comprehensive caller that sends low-confidence CV results to the queue.
- JD confidence/enrichment is not automatically sent to the queue.
- Some direct match routes do not call enqueue_match_if_needed.
- The review queue has no dedicated confidence field and no complete audit history.
- Claim/resolve do not strongly enforce state/ownership.

Impact: Uncertain AI data can flow into recommendations and roadmaps without review.

Acceptance criteria: Every extraction/enrichment carries confidence, reason, and evidence. Low-confidence results enter the queue before affecting downstream features, with audit logging and admin authorization.

#### AI-005 – Package/runtime drift

Location: requirements.txt.

Problem: Dependencies imported by the application are not declared in requirements.txt. Their presence on the current development machine does not make the project reproducible.

Impact: A fresh setup may fail before the API or LLM starts.

Acceptance criteria: Update requirements/lock files, install in a clean environment, and run API smoke plus the local provider test.

### P1 – Major functional problems

#### AI-006 – AI contracts do not match the AI Contract document

Location: src/schemas/match.py, src/schemas/job.py, src/models/candidate.py.

Problems:

- The match response does not adequately include match_id, matched/missing/weak skills, constraints, strengths, reasons, and confidence.
- SkillMatchItem.is_matched can contradict the score because the validator does not enforce the relationship.
- Candidate does not carry profile version/metadata as expected.
- JobPosting does not expose a complete preferred-skills, constraints, and evidence contract.
- There is no consistent Result/Reason/Evidence/Confidence/Recommended Action standard.

#### AI-007 – CV extraction fallback is silent and limited

Location: src/cv_extractor/llm_extractor.py, src/cv_extractor/confidence_scorer.py, src/cv_extractor/evidence_linker.py.

Problem: When the LLM fails, the system silently falls back to heuristics without escalating the failure or low confidence for review. Evidence is primarily linked to skills, not all important fields.

Impact: A profile can look complete while being unreliable, then affect matching, recommendations, and roadmaps.

#### AI-008 – Job Description Understanding is not a production path

Location: src/job_extractor/llm_extractor.py, src/job_extractor/pipeline.py, src/api/routers/job_router.py.

Problem: The endpoint exists, but the extractor depends on a valid LLM and has no equivalent CV-style fallback. The pipeline is synchronous, its confidence score is structural rather than model/evidence confidence, and there is no automatic review.

#### AI-009 – Roadmap fallback is not grounded

Location: src/ai/chains/roadmap_chain.py, src/schemas/roadmap.py.

Problems:

- When no gaps exist, the fallback inserts Core Technical Fundamentals without a source in the candidate or job data.
- The fallback creates links such as https://docs.example.com/....
- validate_grounding checks only that cited_gap is non-empty; it does not verify that the gap exists in the input.
- Progress does not fully model evidence or user confirmation.

Impact: The system can show a plan that appears intelligent but is based on invented information.

#### AI-010 – Roadmap refresh can lose progress

Location: src/services/roadmap_service.py:198-253.

Problem: Refresh collects completed gaps and generates a new roadmap for remaining gaps, but does not reliably preserve every completed milestone and task.

Impact: A user can lose progress history after refresh, contrary to the PDF requirement.

#### AI-011 – Recommendations are not production personalization

Location: src/services/recommendation_service.py, src/repositories/behavior_repository.py, src/services/recommendation_scoring.py.

Problems:

- MockBehaviorRepository is the default in the service path.
- Behavior scoring is very simplified and does not sufficiently use views, applications, or similar-job behavior.
- A cache module exists but is not used by recommendation service.
- Freshness relies on incomplete fields, and the Jooble normalizer leaves posted date empty.

#### AI-012 – Async architecture is inconsistent

Location: src/api/routers/cv_router.py, src/workers/tasks.py, README.md.

Problem: The README requires background jobs for all non-trivial AI calls. CV uses an in-memory BackgroundTasks store, job extraction and roadmap generation are synchronous, and Celery covers only match/interview. There is no unified durable job-status model.

#### AI-013 – PDF AI features have no endpoints

Missing or incomplete paths include:

- Mentor message/history/suggested prompts.
- CV improvement.
- Application strategy.
- Roadmap progress review as an actual service.
- Job ingestion/collection trigger and collection monitor.

#### AI-014 – Error handling is provider-specific

Location: src/api/main.py.

Problem: Exception handlers are mainly specialized for Groq, while other provider errors fall through to a generic handler. A multi-provider architecture needs normalized provider-independent errors.

### P2 – Quality and maintenance

#### AI-015 – Code quality

ruff check src tests found 366 issues, including 239 auto-fixable issues. This makes review harder and can hide integration defects.

#### AI-016 – Aggregation is not operationally runnable

Location: src/integrations/jooble/*.

Problem: A Jooble client, normalizer, and ingestion service exist, but there is no route, scheduler, source registry, run persistence, health monitor, or manual fallback. The client does not retry and ingest processes only one page.

#### AI-017 – Freshness/update state is incomplete

Location: src/schemas/job.py, src/db/models/job_requirement.py, and the Jooble normalizer.

Problem: source_url and ingested_at exist, but last_seen, expiration/stale state, and version/diff are incomplete. This damages recommendation freshness and Mentor context.

#### AI-018 – No real evaluation set

Problem: There is no fixed CV/JD/match/Mentor scenario set with expected outputs and measurements for completeness, grounding, and truthfulness. Most AI tests are schema/unit tests or mocks.

## Additional Exhaustive Code-Level Findings

The following findings came from a second pass over every AI-related Python module, schema, repository, worker, route, prompt, and test. Job-ingestion findings are included only where they affect AI inputs, freshness, enrichment, or recommendations. Literal validation messages and UI labels are not counted as fabricated AI data; the findings below are values that can be presented as user facts, evidence, recommendations, or system readiness without being sourced.

### P0 - Data correctness and acceptance blockers

#### AI-019 - Data-facing hardcoded and synthetic values can masquerade as AI output

Locations: src/cv_extractor/llm_extractor.py:160, 192, 247; src/models/candidate.py:34, 87; src/schemas/job.py:22, 43-44; src/services/matching_service.py:188-222; src/services/roadmap_service.py:211-212, 241; src/ai/chains/roadmap_chain.py:64-65, 117-128; src/services/interview_service.py:21-29; src/workers/youtube_fetcher.py:148-157.

Confirmed examples:

- An empty or unusable CV can return name=Candidate.
- An experience record with no detected employer becomes company=Organization.
- A JobPosting created without these facts becomes work_mode=remote and employment_type=full_time.
- A malformed requirement dictionary becomes skill_name=Unknown and proficiency=Intermediate.
- A candidate skill with no evidence receives the fabricated string Extracted Python with intermediate proficiency.
- A roadmap with no gaps can insert Core Technical Fundamentals; refresh can insert Advanced Career Progression; a missing existing roadmap can default to Software Engineer and Core Fundamentals.
- Roadmap fallback documentation uses https://docs.example.com/... rather than a verified source.
- When network searches fail, the resource fetcher manufactures a ddg_<hash> video ID, title, thumbnail, and YouTube URL that do not identify a real video.
- Interview generation without a job summary receives a generic synthetic summary about core competencies, architecture, security, and practical problem solving instead of actual job requirements.

Impact: The user cannot distinguish source facts, deterministic policy, model output, fallback text, and fabricated placeholders. This violates the PDF zero-fabrication, evidence, confidence, and truthfulness requirements.

Required fix: return null/unknown plus explicit source and fallback metadata when evidence is missing; never create fake URLs or fake IDs; block downstream matching, recommendations, and roadmaps until required source data is present or human-approved.

#### AI-020 - Demo candidate and behavior data are in the production recommendation path

Locations: src/repositories/candidate_repository.py:33-86; src/repositories/behavior_repository.py:30-54; src/api/v1/endpoints/recommendations.py:33, 42; src/services/recommendation_service.py:47-49, 172-184.

Problem:

- candidate_repository is an in-memory MockCandidateRepository seeded with cand_001 and a fixed backend profile.
- MockBehaviorRepository is the default behavior store and contains fixed saved/applied/dismissed/viewed job IDs.
- A separate MockJobRepository reads the static src/fixtures/jobs_seed.json fixture; this must be test/demo-only and must never be confused with live aggregated jobs.
- The public feed defaults to cand_001.
- The live database currently has no usable job rows, so the default feed returned 200 with total_results=0 and no recommendations.

Impact: Recommendation output can be driven by demo facts, disappears after process restart, and is not a real user-personalized feature.

Required fix: use a database-backed candidate/profile and interaction repository, remove demo seed data from production startup, require an authenticated candidate identity, and make empty data explicit rather than silently falling back to a demo candidate.

#### AI-021 - Preferred skills, constraints, experience, and evidence are dropped before matching

Locations: src/job_extractor/models.py:66-92; src/schemas/job.py:33-57; src/db/repositories/job_requirement_repository.py:59-66; src/db/repositories/job_repository.py:63-89, 190-200; src/services/matching_service.py:23-43, 230-280.

Problem:

- Job extraction produces preferred_skills and constraints, but JobPosting exposes only required_skills.
- Persistence stores the full profile in structured_profile but downstream DatabaseJobRepository reads required_skills and does not reconstruct preferred_skills, constraints, responsibilities, or extraction evidence.
- Matching evaluates only the required skill list. It does not score preferred coverage, role alignment, years of experience, constraints, work authorization, or candidate preferences.

Impact: The output is not the PDF match contract and recommendations can be ranked from an incomplete job representation.

Required fix: define one canonical JobRequirement model with required/preferred skills, responsibilities, experience, constraints, source evidence, confidence, and version; make every downstream consumer use that model.

#### AI-022 - Human review is storage, not an enforced quality gate

Locations: src/services/review_queue_service.py:23-98; src/workers/tasks.py:74-85, 127-136; src/api/v1/endpoints/matches.py:30-72; src/api/v1/endpoints/review_queue.py; src/db/repositories/review_queue_repository.py:55-86.

Problems:

- Direct /matches/analyze, /matches/skill-gap, and /matches/explain do not enqueue uncertain results.
- CV confidence and JD extraction confidence are calculated or available but are not comprehensively routed to the queue.
- Interview workers persist evaluations but never call should_flag_interview.
- ReviewQueueModel has no dedicated confidence, source version, or immutable decision history.
- claim_item and resolve_item allow state changes without enforcing current state, reviewer ownership, or admin authorization.
- A resolution only stores resolution_json; it does not update the candidate profile, job requirements, match result, or roadmap that consumed the AI output.

Impact: An item can be reviewed while the unreviewed or rejected result remains the result used by downstream features.

Required fix: route every low-confidence result before downstream consumption, add confidence/evidence/version fields, enforce a state machine and reviewer permissions, write an audit event, and propagate approved/rejected corrections to the source entity and caches.

### P1 - Major AI functionality and contract defects

#### AI-023 - LLM output is parsed inconsistently and is not fully grounded

Locations: src/cv_extractor/llm_extractor.py:84-130; src/job_extractor/llm_extractor.py:44-89; src/core/llm.py:27-60; README.md:92-96.

Problem:

- CV and JD extraction use free-form invoke() followed by parse_json_response(), not the strict structured-output path promised by the README.
- JD validation is lenient and silently drops non-dictionary skill entries and unknown fields.
- The match chain returns an LLM-owned full_candidate_summary and recommended_upskilling_path without a post-generation evidence validator.
- The roadmap validator checks only that cited_gap is non-empty; it does not verify that the cited gap exists in the request or candidate/job data.

Impact: A syntactically valid response can still be semantically incomplete, hallucinated, or ungrounded.

Required fix: use strict Pydantic structured output at each chain boundary, reject unknown/invalid fields where appropriate, validate every claim against canonical input evidence, and keep deterministic facts separate from natural-language explanation.

#### AI-024 - Match correctness has additional failure modes beyond the missing-requirement bug

Locations: src/services/matching_service.py:61-152, 170-296; src/schemas/match.py:27-42.

Problems:

- The known omission bug counts only LLM-returned items. An omitted critical requirement is excluded from the denominator and can produce Qualified.
- If canonical required_skills is empty but the LLM returns a high-scoring item, the rules can classify the result as Qualified even though there is no canonical requirement.
- Duplicate requirement names can be counted multiple times.
- The final rule pass reconstructs SkillMatchItem objects and drops resources returned for gaps.
- SkillMatchItem.sync_is_matched accepts an already supplied boolean and does not enforce the documented score relationship at schema level.
- Full score/verdict logic is skill-only, despite the PDF requiring role alignment, experience, preferences, blockers, and reasons.

Required fix: normalize and deduplicate canonical requirements first; reject empty or contradictory input; build a complete deterministic breakdown from canonical requirements; make the LLM explanation-only; preserve validated resources; enforce score/boolean invariants with model validators.

#### AI-025 - Skill gaps are not a structured, prioritized, roadmap-linked artifact

Locations: src/schemas/match.py:44-70; src/services/matching_service.py:298-320; src/schemas/roadmap.py:71-88; src/services/roadmap_service.py:28-70.

Problem: Skill gaps are represented as missing_critical_skills and a free-form list of recommended_upskilling_path strings. There are no gap IDs, priority/importance, weakness level, source evidence, confidence, or direct links to roadmap milestones. The roadmap API must be called separately with caller-supplied strings.

Impact: The PDF flow CV -> JD -> match -> gaps -> roadmap/Mentor is not an actual connected pipeline.

Required fix: persist a versioned SkillGap entity containing canonical skill ID, required level, candidate level, importance, evidence, confidence, blockers, recommended action, and roadmap linkage.

#### AI-026 - Roadmap generation is not actually dynamic or profile-grounded

Locations: src/schemas/roadmap.py:24-68; src/ai/chains/roadmap_chain.py:17-24, 54-95; src/services/roadmap_service.py:28-70, 198-253; src/ai/factories/roadmap_factory.py:12-38.

Problems:

- The request contains only candidate_id, target_role, role_family, and strings in skill_gaps; no verified baseline, CV evidence, job ID, experience level, or progress evidence is supplied.
- The LLM prompt therefore cannot ground tasks in the actual profile or job.
- The role-family factory changes labels only; it uses the same prompt, structure, and deterministic fallback for all roles.
- LLM output may contain zero phases/tasks because the schema does not require a non-empty roadmap.
- Task/phase cited_gap values are not checked for membership in the input gaps.
- Progress updates accept arbitrary backward transitions and store no evidence, note, completion proof, or user confirmation.

Required fix: build roadmap inputs from persisted verified profile/job/gap entities, validate citations against input IDs, implement role-specific constraints, require measurable tasks, and persist evidence-backed progress events.

#### AI-027 - Roadmap fallback resources are false, auto-approved, and not persisted with the roadmap

Locations: src/ai/chains/roadmap_chain.py:117-128; src/services/roadmap_service.py:75-149; src/workers/youtube_fetcher.py:148-157, 225-233.

Problems:

- The deterministic fallback emits docs.example.com links.
- The network fallback fabricates a YouTube record if every search fails.
- Roadmap enrichment writes externally discovered items directly with status=approved, bypassing the review queue.
- Enrichment runs after repo.save_roadmap, so attached resource links are not stored in the roadmap payload; GET requests can repeat external searches.
- fetch_youtube_resources calls ReviewQueueRepository.create() with a dict, while BaseRepository.create() expects an ORM model and calls Session.add(); this batch path will fail at runtime.
- Resource identity uses Python hash(), which is not stable across processes.

Impact: Users can receive broken learning links, and the resource quality workflow is not trustworthy or reproducible.

Required fix: only return verified HTTPS resources with source metadata, queue them as pending_review, never auto-approve network fallbacks, use stable hashes, persist the enriched roadmap transactionally, and test the batch worker with a real repository.

#### AI-028 - Interview Coach is a disconnected, weakly validated feature

Locations: src/api/v1/routers.py:18-25; src/services/interview_service.py:18-52; src/schemas/interview.py:5-65; src/workers/tasks.py:95-142; src/db/repositories/interview_repository.py:14-45.

Problems:

- Direct API calls invoke the LLM synchronously and do not persist sessions or answers; persistence exists only in Celery task code, which the router does not dispatch.
- QuestionSetResponse has no session ID/history and does not enforce the promised 3-5 questions.
- AnswerSubmission has no candidate/session/job binding, no minimum answer length, and no enum validation for question type.
- The generated prompt can use a synthetic generic job summary instead of loading the actual job.
- AnswerEvaluationResponse.score and SecurityAssessment.security_score have no 1-10 bounds; score=99 and security_score=99 were accepted by the schema test.
- ReviewQueueService.should_flag_interview exists but is not invoked by the worker.

Required fix: resolve the real job and candidate context, return a durable session ID, route all calls through one async job contract, validate the output range and question count, persist and link answers, and enqueue risky/low-confidence evaluations.

#### AI-029 - CV extraction is a best-effort parser with misleading success semantics

Locations: src/cv_extractor/llm_extractor.py:84-130, 160-247; src/cv_extractor/pipeline.py:139-223; src/api/routers/cv_router.py:77-337; src/cv_extractor/document_loader.py:52-159.

Problems:

- Any LLM exception or schema failure silently switches to a heuristic parser and the API still returns a normal Candidate response.
- The fallback only knows a fixed role and technology vocabulary and extracts skill confidence mainly for skills, not every profile field.
- Scanned image PDFs are explicitly unsupported because there is no OCR path.
- Uploaded files are checked by extension and size, not content signature/antivirus policy.
- Candidate profiles are saved only to an in-memory repository; there is no profile version, source document record, user correction/confirm endpoint, or field-level diff.
- Async CV extraction uses FastAPI BackgroundTasks and an in-memory job dictionary; process restart, multiple workers, expiry, ownership, and durable status are not handled.

Impact: CV output can look successful while it is a low-confidence heuristic approximation, and downstream AI cannot know which profile version it used.

Required fix: expose extraction method/status/confidence, route fallback/low confidence to review, add OCR and secure file validation, persist versions/evidence, and use a durable queue/job table.

#### AI-030 - Job Description Understanding is not connected to the job lifecycle

Locations: src/api/routers/job_router.py:33-90; src/integrations/jooble/ingestion.py:29-86; src/db/repositories/job_requirement_repository.py:37-82.

Problems:

- /jobs/analyze can only update an existing job row. It does not create a job when job_id is new, and returns persisted=false rather than a durable error.
- Jooble ingestion accepts an optional extraction pipeline but has no API route, scheduler, collection-run record, retry policy, or admin status.
- The normalized Jooble row has partial snippet text and no posted/expiry/last-seen/fingerprint/version state.
- There is no guaranteed trigger from job normalization to JD enrichment and no downstream notification when enrichment fails.

Impact: A job can enter the catalog without AI requirements, yet still be eligible for downstream consumers; current live recommendation output is empty because the catalog is not operationally populated.

Required fix: persist raw/normalized/enriched job versions, expose a controlled ingestion/enrichment job, fail or quarantine incomplete jobs, and provide source health and retry isolation.

#### AI-031 - AI persistence is incomplete and silently non-durable

Locations: src/repositories/candidate_repository.py:69-86; src/db/models/match.py:9-20; src/db/models/roadmap.py:9-21; src/db/models/interview.py:9-41; src/api/v1/endpoints/matches.py:64-72; src/services/roadmap_service.py:41-55.

Problems:

- Candidate profiles and behavior are in memory, while job requirements, matches, roadmaps, and interview records use different storage strategies.
- Match records have no profile/job version, model/config fingerprint, confidence, provenance, or unique key; repeated /explain calls append duplicates.
- Roadmaps are a mutable JSON blob with no normalized task/progress/evidence history.
- The explain endpoint swallows persistence errors and still returns 200.
- Roadmap generation catches persistence errors and still returns a successful roadmap without indicating it was not saved.

Impact: Results cannot be reproduced, invalidated when source data changes, or reliably used as Mentor context.

Required fix: use one versioned AI-result persistence model, transactional writes, explicit cache invalidation, unique evaluation keys, and honest response status when persistence fails.

#### AI-032 - API and documentation contracts diverge

Locations: src/api/v1/routers.py; src/api/v1/endpoints/*.py; README.md:121-361; docs/API_DOCUMENTATION.md:388 onward; src/ai/chains/cv_extraction.py; src/ai/prompts/cv_extraction.py; src/ai/tools/taxonomy_tool.py; src/api/v1/endpoints/cv.py.

Problems:

- The OpenAPI document has 23 paths and no mentor path.
- There are no routes for Mentor, CV improvement, application strategy, or progress review.
- README documents /cv/upload, /cv/{id}/profile, /cv/{id}/confirm, /jobs/{id}/match, /mentor/message, /mentor/history, and other paths that are absent.
- docs/API_DOCUMENTATION.md mentions /matches/evaluate-gap, but the implementation exposes /matches/skill-gap instead.
- Several AI architecture modules are empty placeholders: the CV chain, CV prompt, taxonomy tool, and v1 CV endpoint module.

Impact: consumers cannot implement the promised AI workflow from the published contract.

Required fix: choose one canonical route/schema contract, implement or remove every documented feature, regenerate OpenAPI, and add contract tests that compare documentation with registered routes.

#### AI-033 - Validation permits empty, invalid, or contradictory AI output

Locations: src/schemas/interview.py:5-65; src/schemas/roadmap.py:24-88; src/schemas/job.py:6-31; src/schemas/match.py:27-42.

Examples:

- Interview scores are unbounded.
- Question lists and key-point lists have no required minimum.
- Roadmap phases, milestones, and tasks can be empty; cited gaps are not cross-validated.
- SkillRequirement.skill_name accepts an empty string and malformed dicts become Unknown.
- Match boolean/score consistency is not enforced at the schema boundary.
- Candidate IDs, job IDs, target roles, and user text do not have meaningful normalization/ownership validation.

Impact: bad input can reach the LLM, and bad model output can pass as a successful structured response.

Required fix: add non-empty/length/enumeration/range validators, canonical ID validation, cross-field validators, and reject contradictory structures before persistence or display.

#### AI-034 - Taxonomy and heuristic extraction are hardcoded and silently degrade

Locations: src/taxonomy/taxonomy_manager.py:229-247; src/cv_extractor/llm_extractor.py:347-365, 717-733; src/services/recommendation_scoring.py:20-44, 61-75.

Problems:

- A missing taxonomy file silently loads an eight-skill fallback seed.
- CV extraction uses fixed lists of roles, technologies, locations, and date/degree patterns.
- strict CV matching drops any skill not in the seed taxonomy.
- non-strict taxonomy normalization can manufacture skill IDs and classify arbitrary short text as Tools.
- recommendation role synonyms and adjacency rules are fixed code, not a versioned taxonomy/policy.

Impact: real skills may disappear, unsupported skills may be misclassified, and results change based on whether a seed file was present.

Required fix: fail fast on missing taxonomy in production, version/manage taxonomy entries, preserve unresolved raw terms for review, and make role/skill mappings auditable.

#### AI-035 - AI input security, privacy, and external-link controls are missing

Locations: src/cv_extractor/llm_extractor.py:84-103; src/ai/chains/*.py; src/services/roadmap_service.py:116-149; src/middleware/llm_middleware.py:35-98; src/core/security.py:135-166; src/api/main.py:124-167.

Problems:

- Raw CV text and potentially sensitive personal data are sent to the configured provider with no redaction, consent, retention, or provider data-policy control.
- CV/JD/user text is inserted into prompts without a documented prompt-injection/data-boundary defense.
- LLM-produced roadmap URLs are not validated against an allowlist or checked for malicious or invalid destinations.
- If request overrides are enabled, clients can submit model/token headers; the localhost check uses substring matching and is not a robust endpoint policy.
- Error handling is primarily Groq-specific, while generic/raw exception detail is exposed by roadmap routes; public health reports Redis URL details.
- API-key authentication is disabled by default, including for AI routes, and reviewer operations have no role authorization.

Required fix: add PII and prompt-injection controls, URL validation, secret-safe normalized errors, secure internal-only model configuration, real user/admin authorization, and production readiness checks.

#### AI-036 - The test suite proves mocks and deterministic helpers, not a working AI system

Locations: tests/test_job_extractor/test_pipeline.py:1-5; tests/test_llm_adapters.py; tests/test_llm_factory.py; tests/test_api_endpoints.py; tests/test_recommendation_validation.py.

Evidence:

- Job extraction tests explicitly state that all LLM calls are mocked.
- LLM factory/adapter tests patch init_chat_model.
- API tests patch service methods and do not exercise a real provider-compatible endpoint.
- Redis integration tests are skipped when Redis is absent.
- There is no local fake OpenAI-compatible server test for chat, structured output, timeout, rate-limit, invalid JSON, model-not-found, or provider failure.
- There is no fixed evaluation dataset measuring extraction recall, requirement completeness, grounding, hallucination, recommendation quality, or Mentor truthfulness.

Required fix: add a local OpenAI-compatible fake server, end-to-end tests across CV -> JD -> match -> gap -> recommendation/roadmap -> Mentor, negative/failure tests, and a versioned evaluation set with acceptance thresholds.

## Hardcoded and Fabricated Output Inventory

This inventory is intentionally explicit. It distinguishes data-facing hardcoding, which must be removed or clearly labeled, from fixed policy constants, which may be acceptable only when documented, versioned, tested, and never presented as evidence from the CV/JD.

### Data-facing values that must not be returned as user facts

| ID | Location | Current value/behavior | Required behavior |
|---|---|---|---|
| HC-01 | src/cv_extractor/llm_extractor.py:160; src/models/candidate.py:87 | Missing CV name becomes Candidate | null/unknown + low confidence/review |
| HC-02 | src/cv_extractor/llm_extractor.py:649; src/models/candidate.py:34 | Missing employer becomes Organization | null/unknown; never claim an employer |
| HC-03 | src/schemas/job.py:43-44; src/repositories/mock_job_repository.py:83-84 | Missing work mode/type defaults to remote/full_time | preserve unknown unless source states it |
| HC-04 | src/schemas/job.py:21-31 | Malformed requirement becomes Unknown/Intermediate | reject invalid input; do not create a requirement |
| HC-05 | src/services/matching_service.py:188-222 | Missing candidate evidence becomes Extracted <skill> with <level> proficiency | empty evidence + low confidence; never synthesize proof |
| HC-06 | src/api/v1/endpoints/recommendations.py:33; src/services/recommendation_service.py:47-49, 172-184 | Missing candidate identity uses cand_001 and demo profile/behavior | authenticated real candidate or explicit 404 |
| HC-07 | src/services/recommendation_explanation.py:148-156 | No signal becomes Recommended based on candidate profile | list actual signals or say insufficient data |
| HC-08 | src/ai/chains/roadmap_chain.py:64-65; src/services/roadmap_service.py:211-212, 241 | Missing gaps become Core Technical Fundamentals, Advanced Career Progression, or Core Fundamentals | refuse/ask for verified gaps; never invent the gap |
| HC-09 | src/services/roadmap_service.py:211-212 | Missing target role becomes Software Engineer and role family Engineering | require target role or mark unknown |
| HC-10 | src/ai/chains/roadmap_chain.py:117-128 | Fallback returns docs.example.com links and generated documentation titles | only verified resource records or no link |
| HC-11 | src/workers/youtube_fetcher.py:148-157; src/services/roadmap_service.py:116-149 | Network failure returns fake ddg_<hash> YouTube IDs and auto-approves them | no result or pending verified resource |
| HC-12 | src/services/interview_service.py:21-29 | Missing job summary becomes generic competencies/security text | load the real job or report missing context |
| HC-13 | src/api/main.py:197-214 | Health always says healthy and feature flags say active without dependency checks | readiness must reflect LLM, DB, queue, and feature availability |
| HC-14 | src/taxonomy/taxonomy_manager.py:229-247 | Missing taxonomy silently changes output to an eight-skill hardcoded vocabulary | fail fast or surface degraded mode and review |
| HC-15 | src/services/recommendation_service.py:288-290 | Every returned recommendation is_applied value is hardcoded to false, even when the behavior store contains applied job IDs | derive application state from a persisted interaction record |
| HC-16 | src/services/matching_service.py:155-156, 287-292; src/schemas/recommendation.py:56-58 | Deterministic match responses can use default IDs (job_default/cand_default) and a fixed summary; recommendation items also default qualification_status to Qualified when callers omit authoritative values | require real IDs and an explicit computed verdict; never default to Qualified |
| HC-17 | src/schemas/match.py:8-9; src/services/matching_service.py:183-222 | Candidate skills without an explicit level are treated as Intermediate, and missing evidence can receive a generated proficiency sentence | preserve unknown level/evidence and lower confidence |
| HC-18 | src/ai/chains/roadmap_chain.py:97-164; src/schemas/roadmap.py:14-52 | Fallback roadmaps use fixed task titles/descriptions, 3.0/5.0 estimated hours, two weeks per gap, and default roadmap metadata | generate from verified gaps/profile context or label the plan as a non-production template |
| HC-19 | src/repositories/mock_job_repository.py:53-88; src/fixtures/jobs_seed.json | Static seed jobs and defaults such as Untitled Job, remote, full_time, and is_active=true can be served by the mock catalog | isolate fixtures from production and preserve unknown source values |

The taxonomy fallback seed is exactly: Python, SQL (with PostgreSQL/MySQL aliases), Machine Learning, Large Language Models (with LLM/LLMs aliases), React, FastAPI, Docker, and Git (with GitHub alias). Any profile or job processed without the real taxonomy file is therefore constrained by this hardcoded list.

### Fixed AI policy/constants that currently affect user decisions

| Location | Hardcoded policy | Risk/required action |
|---|---|---|
| src/services/matching_service.py:98-145 | score threshold 70; Qualified threshold 80% critical and average 75; partial threshold 50 | version the policy, test it against labeled cases, and keep it separate from model output |
| src/services/recommendation_service.py:8; src/services/recommendation_scoring.py:334-365 | weights 0.60/0.15/0.10/0.10/0.05 | document/version/configure and evaluate calibration |
| src/services/recommendation_scoring.py:20-44, 155-176 | fixed role synonym and adjacency map | taxonomy-backed, auditable role matching |
| src/services/recommendation_scoring.py:260-301 | freshness decay 0.05 and missing-date neutral score 50 | use source freshness/last_seen and expose uncertainty |
| src/services/recommendation_scoring.py:304-331 | behavior score is 100 only for saved current job and 50 otherwise | persist event history, recency, negative signals, and cold-start state |
| src/cv_extractor/llm_extractor.py:347-365, 717-733 | fixed English roles, locations, technologies, degrees, and regex heuristics | use taxonomy/NLP/OCR and preserve unresolved text |
| src/middleware/llm_middleware.py:104-128; AI chains | fixed four-characters-per-token estimate and hardcoded input limits | use provider context metadata, safe truncation, and explicit truncation flags |
| src/core/config.py:42-65, 77-105; src/core/llm.py:113-156 | default gemini provider/model and provider-specific constructor branches | replace with the requested three-variable OpenAI-compatible contract and fail fast |

### Reproduced hardcoded and synthetic outputs

The following values were reproduced locally without calling an external LLM:

    CV_EMPTY = name: Candidate, location: null, target_roles: [], skills: []
    JOB_DEFAULTS = work_mode: remote, employment_type: full_time
    REQ_MALFORMED = skill_name: Unknown, proficiency: Intermediate
    MATCH_SYNTHETIC_EVIDENCE = Extracted Python with intermediate proficiency.
    ROADMAP_FALLBACK = https://docs.example.com/redis
    INTERVIEW_GENERIC_SUMMARY = Candidate preparation for Data Scientist. Evaluation of core competencies, architecture, security, and practical problem solving.
    INTERVIEW_RANGE = score 99 and security_score 99 accepted by Pydantic

These are not acceptable as evidence-backed production AI outputs.

## GitHub Issue Status

All nine issues were Open at review time, with no Closed issues:

| Issue | Assessment | Link |
|---|---|---|
| #6 AI Data Quality & Human Review | 🟡 Partial and not fully wired | https://github.com/Team-2-Skill-Project/AI/issues/6 |
| #7 AI Mentor Chatbot | ❌ Not implemented | https://github.com/Team-2-Skill-Project/AI/issues/7 |
| #8 Dynamic Career Roadmap | 🟡 Exists but has blockers | https://github.com/Team-2-Skill-Project/AI/issues/8 |
| #9 Personalized Job Recommendations | 🟡 Partial demo/deterministic implementation | https://github.com/Team-2-Skill-Project/AI/issues/9 |
| #10 Skill Gap Analysis | 🔴 Correctness bug | https://github.com/Team-2-Skill-Project/AI/issues/10 |
| #11 Explainable Job Match | 🔴 Correctness and contract gaps | https://github.com/Team-2-Skill-Project/AI/issues/11 |
| #12 Job Description Understanding | 🟡 Endpoint exists but is LLM-dependent | https://github.com/Team-2-Skill-Project/AI/issues/12 |
| #13 Shared AI Architecture & Foundation | 🔴 Incomplete, especially LLM/env/contracts/review | https://github.com/Team-2-Skill-Project/AI/issues/13 |
| #14 CV Profile Extraction | 🟡 Exists with fallback and confidence/review gaps | https://github.com/Team-2-Skill-Project/AI/issues/14 |

## Required API Contract and Feature Matrix

The API should expose a coherent workflow rather than unrelated endpoints. The following matrix separates what is currently registered from what is required for an acceptable AI delivery.

| Capability | Current route/state | Required production contract |
|---|---|---|
| CV upload/extraction | `POST /api/v1/cv/extract-file` and `POST /api/v1/cv/extract-file-async` exist; async state is in memory | Return a durable execution ID, extraction status/method/confidence, source document ID, and profile version; never hide heuristic fallback |
| CV text extraction | `POST /api/v1/cv/extract-text` exists | Same versioned/evidence-backed contract as file extraction; no second behavior path |
| CV review/confirmation | No confirmed profile route | Add profile read, field correction, confirm/reject, version diff, and audit endpoints |
| CV improvement | Missing | Add a route that accepts a confirmed CV version and target job version and returns evidence-backed suggestions requiring user approval |
| Job collection | Jooble adapter/service exists but no operational route/scheduler/run status | Add source registry, collection trigger, durable run status, pagination, retries, failure isolation, and admin health |
| Job enrichment | `POST /api/v1/jobs/analyze` exists and is synchronous | Accept a persisted raw/normalized job version, create a durable enrichment execution, return required/preferred/constraints/evidence/confidence, and gate publication |
| Explainable match | `POST /api/v1/matches/analyze`, `/skill-gap`, `/explain` exist | One canonical match endpoint should load confirmed/approved versions, evaluate every requirement, persist a stable result, and return complete reasons/evidence/confidence |
| Skill gaps | Embedded lists in match response | Persist stable gap records linked to the match, requirement, evidence, roadmap, and Mentor |
| Recommendations | `GET /api/v1/recommendations/feed` exists; default candidate and mock behavior are present | Require authenticated candidate identity, approved fresh jobs, persisted events, real application state, policy/model version, reasons, and cache invalidation |
| Recommendation events | No durable save/apply/dismiss/view API | Add idempotent event endpoints and an event history used by ranking and Mentor context |
| Roadmap generation | `POST /api/v1/roadmap/generate` exists; caller supplies strings | Load verified candidate/job/gap context, return a versioned roadmap, validate citations/resources, and persist atomically |
| Roadmap progress | Task completion route exists | Bind task to candidate/roadmap version, enforce valid transitions, record evidence/notes/actor, and retain history |
| Progress review | No real review workflow | Add a route that compares current evidence, completed tasks, new skills, and applications and produces a traceable next action |
| Mentor message/history | No Mentor OpenAPI path | Add authenticated message, history, suggested prompts, context snapshot, structured actions/citations, and safe fallback |
| Interview preparation | `POST /api/v1/interview/generate` and `/evaluate` exist | Create durable sessions, bind questions/answers to candidate/job, validate 3–5 questions and 1–10 scores, persist results, and feed review/Mentor |
| Application strategy | Missing | Add apply-now/improve-first/alternative decision with evidence, blockers, confidence, no-guarantee language, and history |
| Human review | Queue list/claim/resolve routes exist | Enqueue every uncertain result before publication, enforce authorization/state ownership, record decisions, and propagate corrections |
| Health/readiness | `/health` returns healthy while LLM/Redis can be unavailable | Separate liveness from readiness and report provider, DB, queue, taxonomy, and migration state without leaking secrets/URLs |

### Recommended response semantics

The team should agree on these meanings and use them consistently:

| Situation | HTTP/status behavior |
|---|---|
| Request is syntactically invalid | `422` with field-level validation errors |
| Required source entity does not exist or belongs to another user | `404` without revealing other users' data |
| Source exists but is incomplete or unapproved | `409` or a clear `needs_review` response; do not run downstream AI as if complete |
| LLM is not configured or unavailable | `503`/durable failed execution with normalized error code; do not return a fabricated successful result |
| LLM output is malformed or ungrounded | `422`/`needs_review`, retain raw failure metadata safely, and do not publish |
| Long-running AI/scraping job accepted | `202` with durable execution ID and poll/callback contract |
| Result was generated but persistence failed | non-success status or explicit `persistence_status=failed`; never silently return a durable-looking success |
| Result requires a human decision | `200` only when the contract clearly says `review_status=pending` and downstream use is blocked, otherwise `202` |

## File-by-File Remediation Map

This map identifies the code areas that must change together. Fixing only one file in a group will leave the same broken integration elsewhere.

| Code area | Files | Required change |
|---|---|---|
| LLM configuration | `src/core/config.py`, `.env.example` | Remove the normal dependency on provider-specific configuration; validate the three-variable contract, distinguish liveness/readiness, and fail clearly on incomplete config |
| LLM gateway | `src/core/llm.py`, `src/middleware/llm_middleware.py` | Implement one OpenAI-compatible gateway, structured output, normalized errors, timeouts, safe retries, redaction, and internal-only configuration; remove public model/token overrides |
| AI architecture placeholders | `src/ai/chains/cv_extraction.py`, `src/ai/prompts/cv_extraction.py`, `src/ai/tools/taxonomy_tool.py`, `src/api/v1/endpoints/cv.py`, `src/schemas/mentor.py` | Implement them or delete misleading duplicate placeholders; keep one canonical chain/route/schema per feature |
| CV extraction | `src/cv_extractor/llm_extractor.py`, `pipeline.py`, `document_loader.py`, `confidence_scorer.py`, `evidence_linker.py`, `src/api/routers/cv_router.py` | Add OCR, secure file inspection, explicit extraction method/status, field-level evidence/confidence, review/confirmation, profile versions, and durable async jobs; remove silent fallback and fake defaults |
| Candidate persistence | `src/models/candidate.py`, `src/schemas/candidate.py`, `src/repositories/candidate_repository.py` | Replace the mock default with versioned database-backed profiles, source metadata, field provenance, ownership, and correction history |
| JD extraction | `src/job_extractor/llm_extractor.py`, `pipeline.py`, `models.py`, `prompt_builder.py`, `skill_normalizer.py`, `src/api/routers/job_router.py` | Use strict structured output, preserve preferred/required/constraints/responsibilities, retain unresolved terms, add evidence/confidence/review, and use a durable async flow |
| Job aggregation | `src/integrations/jooble/client.py`, `normalizer.py`, `ingestion.py`, `src/repositories/mock_job_repository.py`, `src/fixtures/jobs_seed.json` | Add source registry, pagination, details, dedup/update versions, freshness/expiry, retries, source health, manual import, and an explicit test-only boundary for fixtures |
| Taxonomy | `src/taxonomy/taxonomy_manager.py`, `docs/ai-contract/skills_seed.json` | Version and validate taxonomy, fail or clearly degrade when absent, preserve unresolved skills, and expose taxonomy version in every result |
| Match and gaps | `src/services/matching_service.py`, `src/ai/chains/match_explanation.py`, `src/schemas/match.py`, `src/api/v1/endpoints/matches.py` | Build complete canonical breakdowns deterministically, prevent omitted requirements/empty-input false qualifications, add full contract fields, validate evidence, persist gaps, and enqueue review |
| Recommendations | `src/services/recommendation_service.py`, `recommendation_scoring.py`, `recommendation_explanation.py`, `src/repositories/behavior_repository.py`, `src/api/v1/endpoints/recommendations.py` | Replace mock candidate/behavior, derive applied state, add event APIs, use approved fresh jobs, version scoring policy, make explanations signal-backed, and use/invalidate cache correctly |
| Roadmap | `src/ai/chains/roadmap_chain.py`, `src/ai/factories/roadmap_factory.py`, `src/services/roadmap_service.py`, `src/schemas/roadmap.py` | Generate from verified gap IDs and profile/job context, validate citations, preserve progress on refresh, persist enrichment, and block fake/unverified resources |
| Learning resources | `src/workers/youtube_fetcher.py`, `src/db/models/skill_resource.py`, review repositories | Remove fake IDs/URLs, verify resource identity, queue new resources as pending review, use stable fingerprints, and fix ORM-vs-dict repository calls |
| Interview Coach | `src/ai/chains/interview_coach.py`, `src/services/interview_service.py`, `src/schemas/interview.py`, `src/api/v1/routers.py`, `src/workers/tasks.py`, `src/db/repositories/interview_repository.py` | Resolve real job/profile context, create durable sessions, validate question/score bounds, persist answers/evaluations, and invoke review/security policy |
| Review workflow | `src/services/review_queue_service.py`, `src/db/repositories/review_queue_repository.py`, `src/db/models/review_queue.py`, `src/schemas/review_queue.py`, review routes | Add confidence/version/evidence, state/ownership/admin checks, immutable transitions, and correction propagation to source/dependent results |
| Persistence/operations | `src/db/base.py`, `src/db/models/*`, repositories, `src/workers/dispatcher.py`, `src/workers/tasks.py`, `src/core/cache.py` | Add migrations, durable executions, idempotency, transactional writes, explicit persistence failures, cache invalidation, and consistent Celery/local behavior |
| API/docs/tests/dependencies | `README.md`, `docs/API_DOCUMENTATION.md`, `docs/ai-contract/*`, `requirements.txt`, `pyproject.toml`, `tests/*` | Publish one route/schema contract, declare/lock imports, add fake-provider/e2e/negative/hardcoded regression tests, and make CI run all gates |

## Repair Backlog and Acceptance Gates

The following order minimizes rework. Each item should be implemented as a complete vertical slice and must meet its gate before the related GitHub issue is closed.

### P0 — Make the foundation truthful and runnable

| ID | Work package | Acceptance gate |
|---|---|---|
| FIX-01 | Replace the current provider factory with the generic LLM gateway | A clean environment using only the three requested variables can call a local OpenAI-compatible fake server for plain chat, structured output, timeout, invalid JSON, auth failure, and rate limit |
| FIX-02 | Declare and lock the actual runtime dependencies | Fresh install from repository metadata imports the app, starts the API, runs migrations, and passes the provider-independent smoke suite |
| FIX-03 | Establish versioned source/result/provenance entities | CV/JD/match/gap/roadmap/interview/Mentor records reference input versions, evidence, confidence, model/prompt/schema fingerprints, and review status |
| FIX-04 | Remove data-facing fabrication | Regression tests prove that missing CV/JD/profile/resource data never produces `Candidate`, `Organization`, `remote`, `full_time`, `Unknown`, synthetic evidence, fake URLs/IDs, demo identity, or default Qualified |
| FIX-05 | Fix match completeness and gap linkage | Every canonical requirement appears exactly once; omitted LLM items become unknown/missing; empty/invalid inputs cannot be Qualified; stable gap records link to roadmap/Mentor |
| FIX-06 | Make human review a real gate | Low-confidence extraction/enrichment, contradictory matches, security-risk interviews, and unverified resources are blocked or explicitly pending until an authorized decision |
| FIX-07 | Implement the Mentor vertical slice | Message/history/context/action routes use real persisted candidate/job/gap/roadmap/application data, return citations and safe fallback, and persist conversations |

### P1 — Complete user-visible AI behavior

| ID | Work package | Acceptance gate |
|---|---|---|
| FIX-08 | Complete CV confirmation and JD enrichment | Users can inspect/correct/confirm fields; downstream consumers use only confirmed/approved versions with evidence and confidence |
| FIX-09 | Make roadmap dynamic and durable | Roadmap tasks are tied to gap IDs, resources are verified/pending-review, progress evidence is stored, and refresh preserves completed history |
| FIX-10 | Make recommendations real | Feed requires a real candidate, uses persisted behavior/application events and fresh approved jobs, derives `is_applied`, and returns only signal-backed reasons |
| FIX-11 | Complete Interview Coach | Durable session/questions/answers/evaluations are linked to real job/profile context; 3–5 questions and 1–10 scores are enforced; risks reach review |
| FIX-12 | Implement CV Improvement, Application Strategy, and Progress Review | Each has a documented route, structured output, evidence, confidence, user confirmation/history, and Mentor integration |
| FIX-13 | Make job aggregation operational | At least one source completes collection → normalization → dedup/version → JD enrichment → review/publication, with source URL/freshness/admin visibility |

### P2 — Quality, security, and measurable acceptance

| ID | Work package | Acceptance gate |
|---|---|---|
| FIX-14 | Add privacy, safety, and authorization controls | PII redaction/retention/consent, prompt-boundary rules, URL validation, user/admin ownership, secure error responses, and no public LLM overrides are tested |
| FIX-15 | Add observability and operations | Correlation IDs, provider latency/error metrics, queue health, collection-run history, retry isolation, readiness checks, and safe structured logs are visible |
| FIX-16 | Build an AI evaluation set | Versioned CV/JD/match/roadmap/interview/Mentor cases measure required-field recall, unsupported-claim rate, completeness, score correctness, recommendation quality, and fallback behavior |

## Test and Evaluation Plan Required Before Acceptance

The current unit suite is not enough. The following tests must be added and must run without a real vendor key.

### LLM gateway and configuration tests

- Only the three generic env variables configured against a local OpenAI-compatible fake server.
- `LLM_PROVIDER` absent, present as metadata, blank, or conflicting with the model/base URL.
- Missing model, missing base URL, missing key for a remote endpoint, malformed URL, and unsupported non-compatible protocol.
- Plain text response, valid structured JSON, invalid JSON, schema mismatch, extra claims, truncated output, timeout, 429, 401, 5xx, and context-too-large errors.
- Verify that no feature imports a provider SDK or calls `os.getenv` to select its own model.
- Verify that public headers cannot change endpoint, model, or token in production mode.

### Per-feature functional tests

| Feature | Minimum test cases |
|---|---|
| CV | Digital PDF/DOCX/TXT, scanned PDF/OCR, empty CV, malformed CV, missing name/employer, conflicting dates, unknown skill, low confidence, user correction, restart during async job |
| JD | Complete description, missing description, required vs preferred distinction, constraints, unknown skill, duplicate requirements, partial source snippet, source update/version, enrichment failure/retry |
| Match/gaps | All requirements returned, one critical requirement omitted, empty requirements, duplicate requirements, preferred skills, experience/role/constraints, evidence missing, score/boolean invariants, stable gap IDs |
| Recommendations | Unknown candidate, no jobs, stale/expired jobs, applied/dismissed exclusion, applied-state response, cold start, event idempotency, behavior update, duplicate jobs, cache invalidation |
| Mentor | Missing context clarification, job-specific question, roadmap action, application debrief, interview readiness, history, suggested prompts, unsupported claim, prompt injection, LLM outage fallback |
| Roadmap | Verified gaps, no gaps, invalid cited gap, empty phases/tasks, resource verification, resource failure, task evidence, valid/invalid status transition, refresh preserving completed work |
| CV improvement | Unsupported achievement/metric, target-job evidence, user accept/reject, version diff, contradictory rewrite |
| Interview | Real job context, 3–5 questions, session ownership, answer binding, score 1/10 bounds, score 0/11 rejection, security risk review, persistence failure |
| Application strategy | hard blocker, learnable gap, apply-now, improve-first, alternative role, no guarantee, decision history |
| Progress review | completed evidence, new skill, changed target role, application outcome, stale task, next-action explanation |
| Data quality review | confidence threshold, contradiction, duplicate candidate/job, claim/resolve state machine, unauthorized reviewer, correction propagation |

### Cross-feature end-to-end test

Use one deterministic fixture and execute this exact sequence:

1. Ingest a job through the source adapter and persist raw, normalized, and enriched versions.
2. Upload a CV, extract/OCR it, create a profile version, and require user confirmation for uncertain fields.
3. Build the JD requirement version with required/preferred skills, experience, constraints, evidence, and confidence.
4. Run match using only the two approved versions; assert every requirement appears and the verdict is deterministic.
5. Create stable skill gaps and verify that each one can be traced back to a requirement and evidence.
6. Generate recommendations from the confirmed profile, approved jobs, and persisted behavior events; assert applied/dismissed jobs are handled correctly.
7. Generate a roadmap from gap IDs, verify resources/review, complete a task with evidence, and refresh without losing completion.
8. Open a Mentor conversation and assert that its context snapshot references the same profile/job/match/gap/roadmap versions.
9. Generate an interview session and application strategy from the same context; verify their outputs are persisted and reviewable.
10. Change the CV or JD version and assert dependent match/gap/recommendation/roadmap/Mentor results are invalidated or regenerated rather than silently reused.

### Hardcoded-output regression suite

Add explicit assertions that the following strings/values cannot appear as a successful source-backed result unless the user actually supplied them: `Candidate`, `Organization`, `remote`, `full_time`, `Unknown`, `Core Technical Fundamentals`, `Core Fundamentals`, `Advanced Career Progression`, `Software Engineer` as an inferred role, `docs.example.com`, `ddg_...` video IDs, `Extracted <skill> with <level> proficiency.`, `Recommended based on candidate profile`, `cand_001`, `job_default`, `cand_default`, and `is_applied=false` when the event store says applied.

### Suggested evaluation measures

The team should agree on thresholds before closing issues. At minimum, the evaluation report must show:

- 100% canonical requirement coverage in match outputs for the labeled test set; omission is a failure, not a lower score.
- 0 unsupported employers, degrees, skills, achievements, URLs, or application guarantees in the truthfulness set.
- 100% traceability for user-facing factual claims to a CV/job/event source locator or an explicit user input.
- 100% rejection or review routing for invalid score ranges, malformed structured output, missing required context, and unverified resources.
- 100% preservation of completed roadmap task history across refresh scenarios.
- Separate measurements for LLM success, deterministic fallback, review-pending, and hard failure; these states must not be merged.

## Definition of a Correct Demo / Release Handoff

Before the team presents the AI as complete, the demo should show:

1. A clean install and startup using the repository-declared dependencies.
2. A local OpenAI-compatible fake model configured with only the three requested variables.
3. A real CV uploaded and confirmed with evidence/confidence visible.
4. A real or fixture job ingested, normalized, enriched, and approved with source/freshness metadata.
5. A match showing every required/preferred item, deterministic scores, reasons, evidence, confidence, and gaps.
6. A recommendation feed generated from a real candidate and event history, with correct applied/dismissed state.
7. A roadmap linked to gap IDs, verified resources, and preserved progress.
8. An interview session and application strategy linked to the same job/profile context.
9. A Mentor conversation that cites the stored context and refuses unsupported claims.
10. A forced LLM failure and a low-confidence result routed to an honest fallback/review state.
11. The review queue resolving an item and visibly updating the source/dependent records.
12. Logs/health showing the execution ID and dependency state without exposing PII, secrets, or raw prompts.

If any step is replaced by a mock repository, caller-supplied substitute context, hardcoded response, swallowed persistence error, or unverified external link, the AI release is not complete.

## Recommended Fix Order

### Sprint 1 – P0

1. Fix the LLM middleware/factory around the three-variable contract and add a local fake OpenAI-compatible provider test.
2. Declare and lock all runtime dependencies, then run a clean install.
3. Fix the match completeness bug and prevent Qualified when requirements are missing.
4. Finalize CV/JD/match/gap/confidence/evidence contracts.
5. Implement the Mentor end-to-end with context, history, fallback, and the required routes.
6. Connect the low-confidence queue before recommendations/roadmaps, with audit logging and admin permissions.

### Sprint 2 – P1

1. Fix roadmap grounding and refresh while preserving completed tasks.
2. Add CV review/correction and profile versioning.
3. Complete JD enrichment, preferred skills, constraints, evidence, and review.
4. Replace the mock behavior repository with persisted user events, and add freshness/cache behavior.
5. Unify background jobs and durable status for CV/JD enrichment/roadmap.
6. Add Application Strategy, CV Improvement, and Mentor-linked Interview Readiness.

### Sprint 3 – Job data and quality

1. Add a source registry and expose the Jooble adapter through an operational route.
2. Add scheduling and collection-run history.
3. Add pagination, detail extraction, deduplication, and update versioning.
4. Add last_seen, stale/expiration, source health, and retry isolation.
5. Add an admin monitor and manual import fallback.
6. Add an evaluation dataset and realistic provider-independent integration tests.

## Proposed Definition of Done for AI

An AI issue must not be marked Done unless:

- It works from a fresh install using dependencies declared in the repository.
- It works with only LLM_BASE_URL, LLM_MODEL_NAME, and LLM_API_KEY against an OpenAI-compatible endpoint.
- It has a real local/fake-provider test, not only patches around every LLM call.
- Every output is structured and matches the agreed contract.
- Each result includes reason, evidence, confidence, and action where applicable.
- The LLM cannot calculate the final score or silently drop a requirement.
- Failure or low confidence produces a clear fallback or human-review item, not a result that looks successful.
- The Mentor uses real user data, keeps history, and never invents qualifications.
- Roadmap refresh never loses completed progress.
- Recommendations do not use a mock repository in the production path.
- Each feature has a documented API route plus happy-path, validation, and provider-failure tests.

## Final Verdict

The repository contains a reasonable skeleton for some schemas, deterministic services, and tests, but it is not a complete implementation of the AI scope in the PDF. The most accurate summary is:

**The AI foundation is not production-runnable, the Mentor is missing, matching/skill-gap analysis has correctness risks, and the green tests do not represent a real LLM integration.**

The AI issues should not be closed as Done until the P0 items are fixed and a complete happy path is demonstrated from CV → job requirements → match/gaps → recommendations/roadmap → Mentor using a real local fake LLM and persisted data.
