You are performing a careful structural cleanup and architecture consolidation of an
existing Python/FastAPI project called AI-Serv5 / SkillMatch AI Services.

The goal is to make the codebase simpler, de-duplicated, easier to understand, and aligned
with the backend database contract — WITHOUT redesigning the already-clean LLM runtime and
WITHOUT changing product/business behavior.

======================================================================
CURRENT AI FEATURES — SCOPE OF THIS SERVICE
======================================================================

The current SkillMatch AI service supports these features:

- CV Profile Extraction
- Job Description Understanding
- Explainable Job Match
- Skill Gap Analysis
- Personalized Job Recommendations
- AI Mentor Chatbot
- Dynamic Career Roadmap
- CV Improvement Assistant
- Interview Preparation Coach

These features define the persistence scope of the AI service.

IMPORTANT DATABASE SCOPE RULE:

Only implement, map, migrate, or maintain database entities that are required by these AI
features.

If a database table belongs to the wider backend but is not required by the AI service,
do NOT duplicate or reimplement it in this FastAPI service.

For every backend database entity classify it as:

A. REQUIRED BY AI SERVICE
B. REFERENCED BUT OWNED BY BACKEND
C. OPTIONAL / FUTURE AI CONTEXT
D. OUT OF AI SERVICE SCOPE

Rules:

- A → implement/map if required.
- B → the AI service may reference identifiers/relationships but should not own the full domain.
- C → document and retain only if current code genuinely uses it.
- D → skip implementation and do not create ORM models/repositories/migrations for it.

Do not mirror the entire Laravel backend database just for completeness.

The AI service must remain an AI-focused service, not become a duplicate backend.

======================================================================
CRITICAL WORKING RULES
======================================================================

1. Work incrementally.
2. Do not delete code before proving its replacement is working.
3. Do not create new abstraction layers unless there is a proven distinct responsibility.
4. Prefer deletion/consolidation over wrappers, adapters, managers, facades, or compatibility
   bridges.
5. Do not modify `.env`.
6. Do not commit.
7. Do not push.
8. Do not delete untracked files unless explicitly requested.
9. Do not modify generated/local databases automatically.
10. Do not make unrelated formatting changes.
11. Do not silently change public API behavior.
12. Do not silently change database semantics.
13. Do not silently change AI business logic.
14. Do not continue past a phase if unexplained failures appear.

======================================================================
EXECUTION GATE — VERY IMPORTANT
======================================================================

PHASE 0 MUST BE READ-ONLY.

Before modifying any file:

- inspect the repository
- map duplicates
- map callers
- map database models
- map schema mismatches
- map startup behavior
- map security/rate-limit behavior
- map dependencies
- map DB entities to current AI features

Produce a detailed implementation plan first.

Do NOT implement Phases 1+ until the Phase 0 audit is complete.

If a material database mismatch, destructive migration, ambiguous ownership issue,
or unverified backend dependency is found, STOP and report it before changing code.

======================================================================
TARGET ARCHITECTURE PRINCIPLES
======================================================================

The project should move toward:

src/
├── api/
│   └── v1/
│       ├── routers / router aggregator
│       └── endpoints/
│
├── schemas/
│
├── services/
│
├── db/
│   ├── models/
│   ├── repositories/
│   └── migrations/
│
├── core/
│   ├── config.py
│   ├── llm.py
│   ├── security.py
│   ├── logging.py
│   ├── cache.py
│   └── redis.py
│
├── ai/
├── cv_extractor/
├── job_extractor/
├── taxonomy/
├── integrations/
└── workers/

Do not create layers merely to match this diagram.

The real codebase and responsibilities determine whether a file remains separate.

======================================================================
LLM RUNTIME — STRICTLY OUT OF SCOPE
======================================================================

The current LLM runtime has already been cleaned and must NOT be redesigned.

The approved runtime is:

.env
→ LLMSettings / Settings.llm
→ get_llm()
→ LangChain init_chat_model()
→ all LLM-based features

The current `get_llm()` is intentionally a zero-argument canonical factory.

Do NOT:

- migrate to LiteLLM
- add LiteLLM
- add an LLM gateway package
- add provider adapters
- add LLM services
- add LLM managers
- add model routers
- add provider fallback routing
- add provider load balancing
- add request-scoped model selection
- add request-scoped API keys
- add request-scoped provider selection
- add LLM telemetry middleware
- reintroduce DynamicLLMMiddleware
- reintroduce LLMContext
- reintroduce X-LLM-* headers
- reintroduce LLM_ALLOW_REQUEST_OVERRIDES
- change LLM_PROVIDER
- change LLM_MODEL
- change LLM_API_KEY
- reintroduce operational LLM_MODEL_NAME
- infer provider from model-name substrings
- add default Gemini fallback
- add default model fallback
- change `get_llm()` signature
- change feature LLM call paths
- allow feature code to override provider/model/API key/base URL
- change current LLM prompts
- change current LLM output contracts

Current production feature calls must remain conceptually:

get_llm()

with zero arguments.

Only minimal import-path corrections are allowed if structural file moves require them.

======================================================================
1. FIX PROVIDER-SPECIFIC API ERROR HANDLING
======================================================================

Audit:

`src/api/main.py`

Current code may still contain provider-specific API-layer knowledge such as:

- `import groq`
- `groq.AuthenticationError`
- `groq.RateLimitError`
- `groq.GroqError`
- messages referencing `GROQ_API_KEY`
- messages referencing request-level LLM tokens

This is stale because the runtime is provider-neutral.

Requirements:

1. Remove direct provider-specific knowledge from the FastAPI application layer.
2. `src/api/main.py` should not directly import Groq purely for LLM exception translation.
3. Do not replace Groq-specific handlers with OpenAI-, Gemini-, or provider-specific handlers.
4. Keep public API errors provider-neutral.
5. Keep useful detailed exception information in server logs where appropriate.
6. Do not expose secrets or raw sensitive provider errors in public responses.
7. Do not build a new exception framework merely for this cleanup unless an existing
   reusable error boundary already requires one.

Target principle:

API layer:
"LLM provider/runtime failure"

NOT:
"Groq failed"

Remove stale text referring to:
- GROQ_API_KEY
- request-level LLM token

======================================================================
2. ROUTER DEDUPLICATION
======================================================================

Audit all routing locations, especially:

- `src/api/routers/`
- `src/api/v1/endpoints/`
- `src/api/v1/routers.py`
- any router aggregator elsewhere

Current application wiring may be using both old routers and v1 routers.

Goal:

Have one canonical API v1 routing structure.

Preferred target:

`src/api/v1/endpoints/`

plus one clear v1 router aggregator.

Process:

1. Compare old and new routers file by file.
2. Do not assume same-named routers are equivalent.
3. For every endpoint map:
   - route path
   - HTTP method
   - tags
   - request schema
   - response schema
   - status codes
   - dependencies
   - auth requirements
   - rate limiting
   - service calls
   - error behavior
4. Identify:
   - duplicate logic
   - unique old logic
   - unique new logic
5. Migrate missing behavior into the canonical v1 endpoint.
6. Preserve existing API contracts.
7. Update all imports.
8. Verify all expected routes remain in OpenAPI.
9. Delete `src/api/routers/` only after:
   - zero production imports remain
   - all required routes exist
   - tests pass

Do not create another routing layer.

======================================================================
3. PYDANTIC SCHEMA DEDUPLICATION
======================================================================

Audit:

- `src/api/schemas/`
- `src/schemas/`

Goal:

Keep one canonical API/domain DTO location:

`src/schemas/`

Important:

Database schemas and Pydantic schemas are NOT the same concept.

Process:

1. Compare duplicated Pydantic models field by field.
2. Check:
   - field names
   - aliases
   - defaults
   - Optional vs required
   - validators
   - serialization behavior
   - response model behavior
3. Preserve current public API contracts.
4. Move missing definitions into `src/schemas/`.
5. Update imports project-wide.
6. Delete old `src/api/schemas/` only after zero production callers remain.

Do not create one Pydantic schema per database table merely because a DB table exists.

======================================================================
4. REPOSITORY DEDUPLICATION
======================================================================

Audit:

- `src/db/repositories/`
- `src/repositories/`

Goal:

Use:

`src/db/repositories/`

as the canonical persistence repository location.

Process:

1. Compare same-named repositories carefully.
2. Pay special attention to:
   - job_repository
   - candidate repositories
   - behavior repositories
   - match repositories
   - review queue repositories
3. List every public method before merging.
4. Determine real production callers.
5. Preserve all production persistence behavior.
6. Merge only genuinely missing methods.
7. Update services/dependencies.
8. Delete `src/repositories/` only after:
   - zero production callers remain
   - no functionality is lost
   - tests pass

Do not create repository adapters or wrappers.

======================================================================
5. SECURITY ARCHITECTURE AUDIT
======================================================================

Audit:

- `src/api/security.py`
- `src/core/security.py`
- rate limit middleware
- API dependencies related to authentication/rate limiting

Do NOT merge files only because they have the same name.

First document the responsibility of each function.

Specifically audit:

- verify_api_key
- check_rate_limit
- get_client_ip
- password hashing helpers
- Redis rate limiter
- in-memory rate limiter
- RateLimitMiddleware
- API authentication helpers

Classify responsibilities:

A. Authentication
B. Password/security utilities
C. Rate limiting
D. Request identity/client resolution
E. Other

If responsibilities belong together cleanly, consolidate.

If they are distinct, keep separate files with clear ownership.

Do not reduce file count at the cost of mixing unrelated responsibilities.

======================================================================
6. RATE LIMITING CONSOLIDATION
======================================================================

Current code may contain both:

- global `RateLimitMiddleware`
- dependency-based `check_rate_limit`
- special handling for CV routes

Audit the full rate-limit flow.

Report:

1. Routes using middleware
2. Routes using dependencies
3. Routes using both
4. Exempt routes
5. Why CV is treated differently
6. Whether the limits/policies differ
7. Whether both mechanisms operate on the same underlying limiter

Preferred outcome:

One canonical rate-limit mechanism for normal production routes.

A route-specific exception may remain ONLY if it has a real documented contract reason.

Do not change:
- rate-limit counts
- windows
- response semantics

unless existing duplication proves a bug.

======================================================================
7. SETTINGS / CONFIGURATION CONSOLIDATION
======================================================================

Audit:

- `AppSettings`
- `Settings`
- `LLMSettings`
- `settings`
- `get_app_settings()`
- `get_llm_settings()`

Current known duplication may include:

- environment
- CORS
- rate limiting

Goal:

Move toward one canonical application settings object while keeping `LLMSettings`
as the logical nested LLM configuration.

Do this AFTER router/security callers are understood.

Process:

1. Search all production callers of:
   - AppSettings
   - get_app_settings
2. Map every field they use.
3. Compare those fields against canonical `Settings`.
4. Migrate missing required fields safely.
5. Update callers to use canonical settings.
6. Delete AppSettings only after zero real callers remain.
7. Delete get_app_settings only after zero callers remain.
8. Update `src/core/__init__.py`.

Do not create a third settings class.

Do not modify the already-approved LLM contract.

======================================================================
8. DATABASE SCHEMA CONTRACT — CRITICAL
======================================================================

The attached:

`SkillMatch_Database_Schema.pdf`

is the TARGET backend database contract for this AI service.

Use it as the canonical target domain reference for this refactor.

IMPORTANT:

The document states that it is a proposed logical schema and NOT a verified export
of production Laravel/MySQL migrations.

Therefore:

1. Do NOT assume the current AI-service SQLite/SQLAlchemy schema is authoritative.
2. Do NOT assume the PDF exactly matches production Laravel migrations.
3. Do NOT invent a third schema.
4. If actual Laravel migrations or verified MySQL schema are available, compare them
   against the PDF.
5. If there is a material conflict:
   STOP and report it.
6. Do not perform destructive schema changes silently.
7. Do not preserve duplicate AI-service tables merely because they already exist.
8. Do not implement tables that are unrelated to the current AI service features.

Classify every mismatch as:

A. naming-only mismatch
B. structural mismatch
C. AI-service-only extension
D. missing target backend entity
E. obsolete/duplicate local model
F. unclear — backend confirmation required

======================================================================
9. AI SERVICE DATABASE SCOPE
======================================================================

The AI service does NOT own the entire backend database.

Only database entities required by these AI features should be implemented or maintained:

- CV Profile Extraction
- Job Description Understanding
- Explainable Job Match
- Skill Gap Analysis
- Personalized Job Recommendations
- AI Mentor Chatbot
- Dynamic Career Roadmap
- CV Improvement Assistant
- Interview Preparation Coach

For every target backend table classify it as:

A. REQUIRED BY AI SERVICE
B. REFERENCED BUT BACKEND-OWNED
C. OPTIONAL / FUTURE CONTEXT
D. OUT OF AI SERVICE SCOPE

Likely REQUIRED BY AI SERVICE:

- candidate_profiles
- educations
- experiences
- projects
- certificates
- languages
- skills
- candidate_skills
- career_preferences
- companies
- company_aliases
- job_posts
- job_skills
- cv_documents
- cv_extractions

Potentially OPTIONAL / FUTURE CONTEXT:

- saved_jobs
- applications

Likely BACKEND-OWNED / OUT OF AI PERSISTENCE SCOPE:

- users
- email_verification_otps

Important:

The AI service may reference:

user_id
candidate_profile_id
company_id
job_post_id

without owning the full parent domain.

Do not create local duplicates of backend-owned authentication/account tables just
to satisfy foreign-key completeness in the AI service.

If SQLAlchemy requires a relationship target that belongs to the backend, use the
simplest valid representation compatible with the real integration contract rather
than duplicating the entire backend domain.

======================================================================
10. TARGET BACKEND TABLES
======================================================================

The broader backend domain includes:

Authentication:
- users
- email_verification_otps

Candidate profile:
- candidate_profiles
- educations
- experiences
- projects
- certificates
- languages

Skills:
- skills
- candidate_skills

Career preferences:
- career_preferences

Companies & jobs:
- companies
- company_aliases
- job_posts
- job_skills

CV / AI processing:
- cv_documents
- cv_extractions

Candidate activity:
- saved_jobs
- applications

These do NOT all automatically belong inside the AI service.

Use the AI-service scope classification before implementing any table.

======================================================================
11. TARGET RELATIONSHIPS
======================================================================

For relevant AI-domain entities, preserve the intended backend relationships:

users
1 → 0..1 candidate_profiles

users
1 → N companies

candidate_profiles
1 → N educations

candidate_profiles
1 → N experiences

candidate_profiles
1 → N projects

candidate_profiles
1 → N certificates

candidate_profiles
1 → N languages

candidate_profiles
1 → 0..1 career_preferences

candidate_profiles
N ↔ N skills
via candidate_skills

companies
1 → N company_aliases

companies
1 → N job_posts

job_posts
N ↔ N skills
via job_skills

candidate_profiles
1 → N cv_documents

cv_documents
1 → N cv_extractions

candidate_profiles
1 → N saved_jobs

candidate_profiles
1 → N applications

job_posts
1 → N saved_jobs

job_posts
1 → N applications

cv_documents
1 → N applications
(optional CV attachment)

If a parent table is backend-owned and outside AI persistence scope, do not duplicate
the entire parent model solely to represent the relationship.

======================================================================
12. FEATURE → DATABASE MAPPING
======================================================================

During Phase 0, explicitly map each AI feature to the data it needs.

Expected examples:

CV Profile Extraction:
- cv_documents
- cv_extractions
- candidate_profiles
- educations
- experiences
- projects
- certificates
- languages
- candidate_skills / skills

Job Description Understanding:
- job_posts
- companies
- company_aliases
- job_skills / skills

Explainable Job Match:
- candidate_profiles
- candidate_skills
- job_posts
- job_skills
- career_preferences when relevant

Skill Gap Analysis:
- candidate_skills
- job_skills
- skills

Personalized Job Recommendations:
- candidate_profiles
- candidate_skills
- career_preferences
- job_posts
- job_skills
- optionally saved_jobs/applications only if current recommendation behavior uses them

AI Mentor Chatbot:
- candidate profile context
- skills
- career preferences
- roadmap context
- possibly conversation persistence only if current implementation requires it

Dynamic Career Roadmap:
- candidate skills
- job/target role requirements
- career preferences
- roadmap persistence only if current implementation uses it

CV Improvement Assistant:
- cv_documents
- cv_extractions
- candidate profile structured data
- target job/job skills when job-specific

Interview Preparation Coach:
- candidate profile
- candidate skills
- target job
- job skills
- interview persistence only if already required by current implementation

Do not create persistence solely because a feature conceptually could use it in the future.

Map CURRENT feature behavior, not speculative future architecture.

======================================================================
13. CV / AI DATA OWNERSHIP
======================================================================

Expected CV processing flow:

Candidate uploads CV
→ cv_documents
→ AI extraction
→ cv_extractions
→ structured candidate data
→ candidate profile

Use the backend entities appropriately:

`cv_documents`
represents uploaded CV/document metadata.

Expected responsibilities include:
- original filename
- storage path
- mime type
- file size
- upload timestamp
- candidate profile ownership

`cv_extractions`
represents an AI processing run/result.

Expected responsibilities include:
- source CV
- processing status
- extracted raw text
- structured extracted JSON
- model name
- error message
- processed timestamp

Do not create a second persistence model for the same CV extraction responsibility.

AI in-memory/Pydantic output objects may still exist, but persistence must map cleanly
to the backend contract.

======================================================================
14. SKILLS DATA CONTRACT
======================================================================

Persistent skills are normalized.

Use:

skills
candidate_skills
job_skills

for persistent skill relationships where persistence is required.

Do not store persistent candidate/job skills only as JSON blobs if normalized skill
relationships already represent the domain.

AI response schemas may still contain structured skill objects in memory/API payloads.

Audit how:

taxonomy canonical skill IDs

map to:

skills.id / skills.name

Do not generate duplicate skills silently.

======================================================================
15. JOB DATA CONTRACT
======================================================================

The canonical persistent job business entity should align with:

job_posts

and relationships:

companies
job_skills

Audit current Jooble/local job persistence carefully.

Determine whether any existing alternate job model is:

A. ingestion/staging representation
or
B. duplicate permanent job-domain persistence

If it is staging:
document why it exists and how it maps to job_posts.

If it represents the same permanent entity:
do not keep duplicate permanent tables.

Do not delete Jooble ingestion behavior in this structural task.

======================================================================
16. ORM → BACKEND SCHEMA AUDIT
======================================================================

Before modifying DB models or generating migrations:

List every current SQLAlchemy ORM model.

Create this matrix:

Current ORM Model
Current Table Name
Target Backend Table
AI Feature(s) Using It
Ownership Classification:
- REQUIRED BY AI
- BACKEND-OWNED REFERENCE
- OPTIONAL
- OUT OF SCOPE

Schema Status:
- MATCH
- PARTIAL
- MISSING TARGET
- EXTRA AI EXTENSION
- DUPLICATE
- UNKNOWN

Then include:

- column mismatches
- relationship mismatches
- key type mismatches
- nullable differences
- duplicate business entities
- missing target entities
- AI-only entities
- temporary/mock entities

Do NOT change DB models before reporting this mapping.

======================================================================
17. DATABASE MIGRATIONS
======================================================================

Audit the current migration system first.

If Alembic is already configured:
use/consolidate it.

If not:
add one canonical Alembic migration system only if the AI service actually owns
persistent database entities that require migrations.

Preferred location:

`src/db/migrations/`

CRITICAL:

Do NOT generate an initial migration directly from obsolete/current models before the
ORM → backend contract audit is complete.

Correct order:

1. Inspect current ORM models
2. Map them to current AI features
3. Classify ownership
4. Compare to target backend schema
5. Resolve/flag discrepancies
6. Confirm canonical AI-owned models
7. Generate migrations ONLY for AI-owned persistence

Do NOT generate migrations for backend-owned tables that this service merely references.

Requirements:

- use canonical SQLAlchemy metadata
- do not modify production data automatically
- do not silently drop columns/tables
- do not assume SQLite is the final backend truth
- preserve compatibility with intended Laravel/MySQL relational design
- document:
  - create migration
  - apply migration
  - rollback migration

If material model changes require backend-team confirmation:
STOP and report them.

======================================================================
18. DATABASE INITIALIZATION CLEANUP
======================================================================

Search all calls to:

`init_db()`

Current application wiring may initialize DB:

- inside FastAPI lifespan
- at module import time

Audit why both exist.

Preferred architecture:

One canonical startup initialization path.

If module-level initialization only exists because tests incorrectly bypass lifespan,
prefer fixing tests/TestClient lifecycle when safe.

Do NOT delete the second call blindly.

Final report must explain:
- why both existed
- whether one was removed
- how startup behavior remains protected

======================================================================
19. FIXTURE / SEED DATA PLACEMENT
======================================================================

Audit:

`src/fixtures/jobs_seed.json`

Determine whether it is:

A. test-only fixture
B. development/demo seed
C. production/runtime dependency
D. documentation/example data
E. script dependency

If test-only:
move to:

`tests/fixtures/`

If runtime/development seed:
do NOT move into tests.

Choose or propose a justified location such as:

data/
seed/
docs/ai-contract/

Do not move the file until usage is proven.

======================================================================
20. TEST STRUCTURE CLEANUP
======================================================================

Preferred organization:

tests/
├── unit/
│   ├── core/
│   ├── services/
│   ├── ai/
│   ├── db/
│   ├── api/
│   └── integrations/
│
├── integration/
└── fixtures/

Do not reorganize tests blindly.

First classify each test by what it actually verifies.

Move tests only when:
- imports remain correct
- pytest discovery remains stable
- no coverage is lost

Cross-feature/end-to-end tests belong in:

`tests/integration/`

Do NOT create a new LLM test architecture.
Do NOT rewrite the LLM runtime tests unless structural path changes require import updates.

======================================================================
21. DEPENDENCY CLEANUP
======================================================================

Audit:

- requirements.txt
- pyproject.toml

Goals:

1. Every production import must have a declared dependency.
2. Remove dependencies only after repository-wide proof they are unused.
3. Do NOT add LiteLLM.
4. Do NOT change the current LLM provider dependency stack as part of this task.
5. Remove provider-specific packages only if the LLM runtime separately proves they are
   unused — not as part of this cleanup.
6. Run:
   - pip check
   - import smoke tests
   - clean virtualenv install if practical

======================================================================
22. KEEP HEALTH ACTIVE MODEL
======================================================================

Keep:

"active_model": settings.llm.model_name

inside `/health`.

This is intentionally retained for debugging/monitoring.

Do not remove it in this task.

======================================================================
23. BUSINESS LOGIC — DO NOT CHANGE
======================================================================

Do NOT change:

- CV extraction behavior
- Job Description Understanding
- taxonomy normalization
- matching score logic
- qualification rules
- skill gap logic
- recommendation ranking
- recommendation filters
- recommendation eligibility gates
- AI Mentor logic
- roadmap generation behavior
- CV Improvement logic
- interview coach behavior
- review queue behavior
- Jooble ingestion business behavior
- prompts
- output schemas unless only import relocation is needed
- DB business semantics without approved schema alignment
- public API semantics

This task is structural consolidation.

======================================================================
24. NO USELESS LAYERS
======================================================================

Do not create:

- managers
- wrappers
- adapters
- gateways
- provider facades
- bridge modules
- compatibility services
- duplicate repositories
- duplicate router aggregators
- duplicate settings objects
- artificial "architecture" directories with no distinct responsibility

Before creating any new Python file answer:

1. What unique responsibility does this file own?
2. Why can no existing file own it cleanly?
3. Which production code calls it?
4. What duplication does it remove?

If those answers are weak:
do not create the file.

======================================================================
25. UNUSED / STALE CODE CLEANUP
======================================================================

After consolidation:

Remove unused imports and obsolete references such as:

- direct Groq imports in API layer
- old router imports
- old schema imports
- old security imports
- obsolete settings imports
- unused BaseSettings / SettingsConfigDict imports if genuinely unused
- stale compatibility comments
- references to deleted middleware
- references to request-level LLM overrides

Do not make unrelated formatting-only changes.

======================================================================
26. PHASED IMPLEMENTATION ORDER
======================================================================

PHASE 0 — READ-ONLY AUDIT

Report:

A. Current AI feature → data mapping
B. Router duplicates
C. Schema duplicates
D. Repository duplicates
E. Security responsibilities
F. Rate-limit paths
G. Settings callers
H. All SQLAlchemy models
I. ORM → backend schema mapping
J. AI ownership classification for every DB model/table
K. Fixture usage
L. Alembic/migration status
M. init_db callers
N. Current test structure
O. Dependency inconsistencies
P. Groq/provider-specific API artifacts

STOP after Phase 0 and present the implementation plan.

Do not implement further phases until the audit has completed and the scope is clear.

PHASE 1
Provider-neutral API exception cleanup

PHASE 2
Router consolidation

PHASE 3
Pydantic schema consolidation

PHASE 4
Repository consolidation

PHASE 5
Security and rate-limit consolidation

PHASE 6
Application settings consolidation

PHASE 7
AI-owned ORM/backend-contract alignment
ONLY for approved/non-ambiguous differences

PHASE 8
Database initialization cleanup

PHASE 9
Alembic migration setup/alignment
ONLY for AI-owned persistence

PHASE 10
Fixture/data placement

PHASE 11
Test organization

PHASE 12
Dependency verification and stale-import cleanup

======================================================================
27. TESTING AFTER EACH PHASE
======================================================================

After every relevant phase:

run focused tests first.

Then when risk is non-trivial run:

pytest -q

Also run:

python -m compileall -q src

git diff --check

Do not continue if failures are unexplained.

======================================================================
28. FINAL VERIFICATION
======================================================================

At completion verify:

FastAPI:
- app imports cleanly
- `/health` returns successfully
- `/docs` / OpenAPI generation succeeds
- expected v1 routes exist
- no duplicate routes exist

Authentication:
- behavior unchanged

Rate limiting:
- behavior unchanged unless an explicitly approved duplicate bug was removed

LLM:
- existing runtime unchanged
- get_llm remains zero-argument
- no request-level override mechanism exists

Database:
- only AI-relevant persistence is owned by this service
- backend-only tables were not duplicated unnecessarily
- ORM mappings documented
- no duplicate permanent business entities remain unintentionally
- migration state documented
- no destructive changes happened silently

Imports:
- no deleted module path remains referenced

======================================================================
29. REQUIRED REPOSITORY SEARCHES
======================================================================

Report remaining production occurrences for:

- `import groq`
- `groq.`
- `src.api.routers`
- `src.api.schemas`
- `src.api.security`
- `src.repositories`
- `AppSettings`
- `get_app_settings`
- `check_rate_limit`
- `RateLimitMiddleware`
- `init_db(`
- `get_llm(`

For every remaining occurrence explain why it still exists.

For every production `get_llm(` call confirm it remains:

get_llm()

with zero arguments.

======================================================================
30. DATABASE REPORT
======================================================================

Include:

1. Current AI features
2. Feature → DB entity mapping
3. Target backend tables
4. AI ownership classification for each target table
5. Current ORM tables
6. ORM → target mapping matrix
7. Missing AI-required entities
8. Extra AI-service entities
9. Duplicate business representations
10. Column mismatches
11. Relationship mismatches
12. Backend-owned tables intentionally skipped
13. Optional/future tables intentionally skipped
14. AI-only tables intentionally retained and why
15. Models modified
16. Models intentionally not modified
17. Migration files created
18. Items requiring Laravel/backend confirmation

======================================================================
31. FINAL STRUCTURAL REPORT
======================================================================

At completion report:

1. Files created
2. Files moved
3. Files modified
4. Files deleted
5. Router structure before/after
6. Schema structure before/after
7. Repository structure before/after
8. Security structure before/after
9. Rate-limit architecture before/after
10. Settings architecture before/after
11. AI feature → persistence mapping
12. ORM/backend schema mapping
13. DB initialization before/after
14. Migration setup status
15. Backend-owned tables intentionally not implemented
16. Fixture/data decision
17. Test structure before/after
18. Dependency changes
19. Provider-specific API code removed
20. Remaining intentional legacy code and why
21. Full pytest result
22. compileall result
23. pip check result
24. git diff --check result
25. OpenAPI verification result
26. Confirmation that LLM runtime/provider/model code was not redesigned
27. Confirmation that `/health` still exposes:
    `"active_model": settings.llm.model_name`
28. Confirmation that no unnecessary abstraction layer was introduced
29. Any item requiring backend-team confirmation

Do not commit.
Do not push.