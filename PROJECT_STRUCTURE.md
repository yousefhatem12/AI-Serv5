# Project Structure & Architecture Patterns

```text
AI-Serv5/
├── .env                                       # Environment variables & secrets (local)
├── .env.example                               # Example environment variables template
├── .gitignore                                 # Git ignored files and directories
├── Agent.md                                   # Agent action history and decision log
├── README.md                                  # Project overview and developer documentation
├── pyproject.toml                             # Build system and package configuration
├── pytest.ini                                 # Pytest configuration
├── requirements.txt                           # Python project dependencies
├── skillmatch.db                              # SQLite local development database
├── docs/                                      # Documentation & API Specifications
│   ├── API_DOCUMENTATION.md                   # Full REST API endpoint reference
│   ├── api_documentation.json                # OpenAPI specification
│   └── ai-contract/                           # AI system design specifications
│       ├── AI_Contract.md                     # AI contract and constraints
│       ├── LLM_ARCHITECTURE.md                # LLM architecture and fallback design
│       └── skills_seed.json                   # Seed canonical skills dataset
├── scripts/                                   # Automation & Utility Scripts
│   ├── import_jooble_jobs.py                  # CLI script to import jobs from Jooble
│   └── test_jooble_api.py                     # Jooble API connectivity test script
├── src/                                       # Core Application Source Code
│   ├── main.py                                # Application entry point
│   ├── ai/                                    # AI / LLM Layer
│   │   ├── __init__.py
│   │   ├── adapters/                          # LLM provider adapter implementations
│   │   ├── chains/                            # LangChain execution chains
│   │   │   ├── __init__.py
│   │   │   ├── cv_extraction.py               # CV extraction chain
│   │   │   ├── interview_coach.py             # Mock interview coaching chain
│   │   │   ├── match_explanation.py           # Match reasoning and explanation chain
│   │   │   └── roadmap_chain.py               # Learning roadmap generation chain
│   │   ├── factories/                         # AI factory generators
│   │   │   └── roadmap_factory.py             # Factory for roadmap chains
│   │   ├── prompts/                           # Prompt templates
│   │   │   ├── __init__.py
│   │   │   ├── cv_extraction.py               # CV extraction prompt templates
│   │   │   └── match_reasoning.py             # Match scoring and reasoning prompts
│   │   └── tools/                             # AI tool definitions
│   │       ├── __init__.py
│   │       └── taxonomy_tool.py               # Skill taxonomy verification tool
│   ├── api/                                   # FastAPI Web Layer
│   │   ├── __init__.py
│   │   ├── dependencies.py                    # FastAPI dependency injection
│   │   ├── main.py                            # FastAPI app instance and router mount
│   │   ├── security.py                        # API key authentication & security
│   │   ├── routers/                           # Domain-specific routers
│   │   │   ├── __init__.py
│   │   │   ├── cv_router.py                   # CV upload and parsing router
│   │   │   └── job_router.py                  # Job parsing and extraction router
│   │   ├── schemas/                           # Router request/response schemas
│   │   │   ├── __init__.py
│   │   │   ├── cv_schemas.py                  # CV endpoint schemas
│   │   │   └── job_schemas.py                 # Job endpoint schemas
│   │   └── v1/                                # API Version 1
│   │       ├── __init__.py
│   │       ├── routers.py                     # v1 master router aggregator
│   │       └── endpoints/                     # v1 individual endpoint handlers
│   │           ├── __init__.py
│   │           ├── cv.py                      # Candidate CV endpoints
│   │           ├── matches.py                 # Candidate-job matching endpoints
│   │           ├── recommendations.py         # Recommendation feed endpoints
│   │           ├── review_queue.py            # Admin human-in-the-loop review endpoints
│   │           └── roadmap.py                 # Skill roadmap endpoints
│   ├── core/                                  # Application Configuration & Infrastructure
│   │   ├── __init__.py
│   │   ├── cache.py                           # Cache utilities
│   │   ├── cel_app.py                         # Celery app configuration
│   │   ├── config.py                          # Pydantic application settings
│   │   ├── llm.py                             # LLM client setup and provider switching
│   │   ├── logging.py                         # Logging setup
│   │   ├── redis.py                           # Redis client initialization
│   │   └── security.py                        # Security and password hashing utilities
│   ├── cv_extractor/                          # CV Parsing & Extraction Pipeline
│   │   ├── __init__.py
│   │   ├── confidence_scorer.py               # Extraction confidence scoring
│   │   ├── document_loader.py                 # PDF / DOCX / TXT text extraction
│   │   ├── evidence_linker.py                 # Links skills to exact text evidence
│   │   ├── link_associator.py                 # Associates candidate links (GitHub, etc.)
│   │   ├── llm_extractor.py                   # Structured LLM CV extractor
│   │   └── pipeline.py                        # End-to-end CV extraction orchestrator
│   ├── db/                                    # Database Layer (SQLAlchemy)
│   │   ├── __init__.py
│   │   ├── base.py                            # SQLAlchemy Base and metadata
│   │   ├── models/                            # ORM Database Models
│   │   │   ├── __init__.py
│   │   │   ├── interview.py                   # Interview session and question models
│   │   │   ├── job_requirement.py             # Job requirements model
│   │   │   ├── match.py                       # Match result models
│   │   │   ├── review_queue.py                # Human review queue item models
│   │   │   ├── roadmap.py                     # Learning roadmap models
│   │   │   └── skill_resource.py              # Curated skill resources model
│   │   └── repositories/                      # Database CRUD Repositories
│   │       ├── __init__.py
│   │       ├── base.py                        # Base repository class
│   │       ├── interview_repository.py        # Interview persistence repository
│   │       ├── job_repository.py              # Job persistence repository
│   │       ├── job_requirement_repository.py  # Job requirements repository
│   │       ├── match_repository.py            # Candidate-job match repository
│   │       ├── review_queue_repository.py     # Admin review queue repository
│   │       └── roadmap_repository.py          # Learning roadmap repository
│   ├── fixtures/                              # Static Fixtures & Seed Data
│   │   └── jobs_seed.json                     # Seed job descriptions dataset
│   ├── integrations/                          # Third-Party Integrations
│   │   ├── __init__.py
│   │   └── jooble/                            # Jooble Job Search Integration
│   │       ├── __init__.py
│   │       ├── client.py                      # Jooble REST client
│   │       ├── ingestion.py                   # Ingestion workflow for Jooble jobs
│   │       ├── models.py                      # Jooble API response models
│   │       └── normalizer.py                  # Normalizes Jooble jobs to internal schema
│   ├── job_extractor/                         # Job Description Extraction Pipeline
│   │   ├── __init__.py
│   │   ├── llm_extractor.py                   # LLM job requirement extractor
│   │   ├── models.py                          # Job extraction internal data structures
│   │   ├── pipeline.py                        # Job parsing pipeline coordinator
│   │   ├── prompt_builder.py                  # Prompt templates for job extraction
│   │   └── skill_normalizer.py                # Normalizes extracted job skills
│   ├── middleware/                            # Custom HTTP & Service Middlewares
│   │   ├── __init__.py
│   │   ├── llm_middleware.py                  # LLM telemetry and latency tracking
│   │   └── rate_limit_middleware.py           # Request rate limiting middleware
│   ├── models/                                # Core Domain Models
│   │   ├── __init__.py
│   │   ├── candidate.py                       # Candidate domain model
│   │   ├── common.py                          # Common domain models and enums
│   │   └── taxonomy.py                        # Skill taxonomy domain models
│   ├── repositories/                          # Additional Domain Repositories
│   │   ├── behavior_repository.py             # User behavioral logs repository
│   │   ├── candidate_repository.py            # Candidate profile repository
│   │   ├── job_repository.py                  # High-level job repository
│   │   └── mock_job_repository.py             # In-memory mock job repository
│   ├── schemas/                               # Pydantic Schemas & DTOs
│   │   ├── __init__.py
│   │   ├── candidate.py                       # Candidate schemas
│   │   ├── cv.py                              # CV extraction and profile schemas
│   │   ├── interview.py                       # Interview coaching schemas
│   │   ├── job.py                             # Job requirement schemas
│   │   ├── match.py                           # Matching score schemas
│   │   ├── mentor.py                          # Mentorship matching schemas
│   │   ├── recommendation.py                  # Recommendation schemas
│   │   ├── review_queue.py                    # Review queue DTOs
│   │   └── roadmap.py                         # Learning roadmap schemas
│   ├── services/                              # Business Logic Layer
│   │   ├── __init__.py
│   │   ├── cv_service.py                      # CV processing service
│   │   ├── interview_service.py               # Interview simulation service
│   │   ├── matching_service.py                # Candidate-job matching service
│   │   ├── recommendation_explanation.py      # Recommendation explanation service
│   │   ├── recommendation_scoring.py          # Multi-factor recommendation scoring
│   │   ├── recommendation_service.py          # Candidate/job recommendation service
│   │   ├── review_queue_service.py            # Admin review queue workflow service
│   │   └── roadmap_service.py                 # Skill roadmap generation service
│   ├── taxonomy/                              # Taxonomy Management
│   │   ├── __init__.py
│   │   └── taxonomy_manager.py                # Skill matching, aliases, and normalization
│   ├── utils/                                 # General Utilities
│   │   ├── __init__.py
│   │   └── text_cleaner.py                    # Text cleaning and preprocessing
│   └── workers/                               # Background Asynchronous Workers
│       ├── __init__.py
│       ├── dispatcher.py                      # Task dispatcher
│       ├── tasks.py                           # Background task functions
│       └── youtube_fetcher.py                 # YouTube skill resource fetcher worker
└── tests/                                     # Automated Test Suite
    ├── fixtures/                              # Test Fixtures & Samples
    │   └── job_descriptions/                  # Sample raw job description files
    │       ├── jd_arabic_mixed.txt
    │       ├── jd_data_analyst_vague.txt
    │       └── jd_senior_backend_engineer.txt
    ├── samples/                               # Sample CV files for testing
    │   ├── sample_ahmed_hassan_cv.txt
    │   └── yousef_hatem_cv.docx
    ├── test_job_extractor/                    # Job extractor test suite
    │   ├── __init__.py
    │   ├── test_db_repository.py
    │   ├── test_endpoint.py
    │   └── test_pipeline.py
    ├── test_api_cv.py                         # CV API tests
    ├── test_api_endpoints.py                  # General API endpoint tests
    ├── test_background_workers.py             # Background workers tests
    ├── test_config.py                         # Configuration tests
    ├── test_cv_pipeline.py                    # CV pipeline tests
    ├── test_database_job_repository.py        # Database job repository tests
    ├── test_docx_extraction.py                # DOCX parser tests
    ├── test_duckduckgo_fetcher.py             # Search fetcher tests
    ├── test_dynamic_sections.py               # Dynamic section parsing tests
    ├── test_evidence_and_confidence.py        # Evidence linker & confidence tests
    ├── test_experience_parser.py              # Experience parser tests
    ├── test_fallback_no_fabrication.py        # Anti-hallucination tests
    ├── test_five_feature_integration.py       # Full feature integration tests
    ├── test_interview.py                      # Interview service tests
    ├── test_jooble_integration.py             # Jooble integration tests
    ├── test_llm_adapters.py                   # LLM adapter tests
    ├── test_llm_factory.py                    # LLM factory tests
    ├── test_llm_middleware.py                 # LLM middleware & telemetry tests
    ├── test_logging_and_error_handling.py     # Logging & exception handler tests
    ├── test_match_schemas.py                  # Match schema validation tests
    ├── test_matching_api.py                   # Match API tests
    ├── test_matching_service.py               # Match scoring engine tests
    ├── test_personalized_recommendations_automation.py # Personalized recommendations tests
    ├── test_project_parser.py                 # Project extraction tests
    ├── test_rate_limiting.py                  # Rate limiting tests
    ├── test_recommendation_explanation.py     # Recommendation reasoning tests
    ├── test_recommendation_filtering.py       # Recommendation filtering tests
    ├── test_recommendation_scoring.py         # Recommendation scoring tests
    ├── test_recommendation_service.py         # Recommendation service tests
    ├── test_recommendation_validation.py      # Recommendation schema tests
    ├── test_redis.py                          # Redis caching tests
    ├── test_repositories.py                   # Database repository tests
    ├── test_review_queue.py                   # Review queue service tests
    ├── test_roadmap_endpoints.py              # Roadmap API endpoint tests
    ├── test_roadmap_service.py                # Roadmap generation tests
    ├── test_schema_validation.py              # Pydantic schema validation tests
    ├── test_taxonomy_manager.py               # Skill taxonomy manager tests
    └── test_text_cleaner.py                   # Text cleaning utility tests
```

---

## Architectural & Design Patterns in this Structure

The directory organization follows **Layered Clean Architecture** combined with battle-tested software design patterns:

### 1. Layered Architecture (Separation of Concerns)

```text
[ Client Request ]
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. Presentation Layer (`src/api/`, `src/middleware/`)        │  FastAPI routes, DTO validation, rate limiting
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Service Layer (`src/services/`)                          │  Domain orchestration & business logic
└──────────────┬───────────────────────────────┬──────────────┘
               │                               │
               ▼                               ▼
┌─────────────────────────────┐ ┌─────────────────────────────┐
│ 3. AI / Pipeline Layer       │ │ 4. Persistence Layer        │
│ (`src/ai/`, `cv_extractor/`,│ │ (`src/db/`, `repositories/`)│
│  `job_extractor/`)          │ │ SQLAlchemy models & repos   │
└─────────────────────────────┘ └─────────────────────────────┘
```

- **Presentation / API Layer (`src/api/`)**: Thin routers that parse HTTP requests, authenticate via `dependencies.py` and `security.py`, validate schemas, and delegate work to services.
- **Service Layer (`src/services/`)**: Orchestrates core business operations (matching, roadmap creation, recommendations) without coupling to transport or direct database ORM logic.
- **AI & Domain Pipelines (`src/ai/`, `src/cv_extractor/`, `src/job_extractor/`)**: Encapsulates LLM chains, prompts, tools, and multi-stage extraction pipelines.
- **Data Access Layer (`src/db/`, `src/repositories/`)**: Encapsulates all database operations, isolating ORM models from upper layers.
- **Domain Models & Schemas (`src/models/`, `src/schemas/`)**: Provides contracts and data transfer objects (DTOs) shared across layers.

---

### 2. Core Design Patterns Applied

| Pattern | Where It Is Used | How It Works |
| :--- | :--- | :--- |
| **Factory Pattern** | `src/core/llm.py`<br>`src/ai/factories/` | `get_llm()` acts as a central factory instantiating the right LLM provider (OpenAI, Gemini, Anthropic, local) based on environment configuration without leaking provider SDK specifics to business logic. |
| **Facade Pattern** | `src/cv_extractor/pipeline.py`<br>`src/job_extractor/pipeline.py` | Exposes a single, unified method (e.g. `process_cv()`, `extract_job()`) hiding complex multi-step pipelines (document loading, text cleaning, LLM extraction, evidence linking, and confidence scoring). |
| **Repository Pattern** | `src/db/repositories/`<br>`src/repositories/` | Mediates between the domain/service layers and data mapping layers (`SQLAlchemy`), enabling unit testability with mock repositories (e.g., `mock_job_repository.py`). |
| **Pipe-and-Filter / Pipeline Pattern** | `src/cv_extractor/`<br>`src/job_extractor/` | Sequences data processing through dedicated filter stages: `document_loader` → `text_cleaner` → `llm_extractor` → `evidence_linker` → `confidence_scorer` → `taxonomy_manager`. |
| **Strategy Pattern** | `src/ai/adapters/` | Allows switching between different AI models, prompt styles, or scoring algorithms dynamically at runtime. |
| **Chain of Responsibility / Escalation** | `src/services/review_queue_service.py`<br>`src/workers/youtube_fetcher.py` | If an automated extraction or external resource (e.g., YouTube tutorial) has low confidence or lacks verification, it escalates to the Human-in-the-loop Review Queue before database commit. |
| **Data Transfer Object (DTO) / Strict Schema** | `src/schemas/*` | Strict Pydantic models enforce type validation at API boundaries and enforce structured LLM output parsing (`.with_structured_output()`). |
| **Middleware / Interceptor Pattern** | `src/middleware/` | Intercepts HTTP and LLM traffic for cross-cutting concerns: `rate_limit_middleware.py` protects endpoints, while `llm_middleware.py` logs token counts and response latencies. |
| **Asynchronous Worker / Task Queue** | `src/workers/`<br>`src/core/cel_app.py` | Offloads heavy workloads (e.g. offline YouTube scraping, batch matching, large document parsing) to background Celery tasks. |
