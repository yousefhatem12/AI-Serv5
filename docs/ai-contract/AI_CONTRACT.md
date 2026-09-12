# 📜 DAY 1 — SkillMatch AI Shared Contract

> **Single Source of Truth (SSOT) between Engineer 1 (Matching Track) and Engineer 2 (Coaching Track).**

---

## 🏛️ Core Principles & Division of Responsibilities

```text
┌───────────────────────────────────────────────────────────┐
│                     Engineer 1 (You)                      │
│                   UNDERSTAND + MATCH                      │
│  (CV Extraction, Job Understanding, Matching, Gaps, Recs) │
└─────────────────────────────┬─────────────────────────────┘
                              │ Produces: Profile, MatchResult, SkillGaps
                              ▼
┌───────────────────────────────────────────────────────────┐
│                  Engineer 2 (Teammate)                    │
│                    PLAN + GUIDE + ACT                     │
│    (Roadmap, AI Mentor, Interview Coach, CV Assistant)    │
└───────────────────────────────────────────────────────────┘
```

---

## 🔑 1. Standard Enums & Taxonomy

### Skill Levels
* `beginner`
* `intermediate`
* `advanced`
* `expert`
* `unknown` (عند عدم وضوح المستوى من الـ CV)

### Requirement Importance Levels
* `critical` (Must-have - حاسم للقبول)
* `important` (مهم جداً)
* `nice_to_have` (مفضل / إضافي)

### Confidence Scale
* `0.00 - 0.49` ➡️ **Low** (يتم تحويله للـ Admin Review ولا يُعتمد تلقائياً)
* `0.50 - 0.74` ➡️ **Medium**
* `0.75 - 0.89` ➡️ **High**
* `0.90 - 1.00` ➡️ **Very High**

---

## 📦 2. Core Schemas & Interfaces

### 👤 Candidate Schema
```json
{
  "candidate_id": "cand_001",
  "profile": {
    "name": "Ahmed Hassan",
    "email": "ahmed@example.com",
    "location": "Mansoura, Egypt",
    "education": [
      {
        "degree": "BSc Computer Science",
        "field": "Computer Science",
        "institution": "Mansoura University",
        "start_year": 2022,
        "end_year": 2026,
        "status": "current"
      }
    ],
    "target_roles": ["Data Analyst", "Junior Data Scientist"],
    "preferences": {
      "employment_type": ["internship", "full_time"],
      "work_mode": ["remote", "hybrid"],
      "locations": ["Egypt"],
      "industries": ["Technology", "FinTech"]
    }
  },
  "skills": [
    {
      "skill_id": "skill_python",
      "name": "Python",
      "level": "intermediate",
      "confidence": 0.96,
      "evidence": [
        {
          "type": "project",
          "section": "projects",
          "text": "Built a customer churn prediction model using Python",
          "source": "cv"
        }
      ]
    }
  ],
  "experience": [],
  "projects": [],
  "certifications": [],
  "metadata": {
    "cv_file_id": "cv_001",
    "profile_version": 1,
    "last_updated": "2026-09-06"
  }
}
```

---

### 💼 Job Schema
```json
{
  "job_id": "job_001",
  "title": "Junior Data Scientist",
  "company": {
    "company_id": "company_001",
    "name": "ABC Technology"
  },
  "role": {
    "canonical_role": "Data Scientist",
    "seniority": "junior"
  },
  "description": {
    "summary": "Work with data and machine learning models...",
    "responsibilities": [
      "Analyze datasets",
      "Build machine learning models",
      "Prepare reports"
    ]
  },
  "requirements": {
    "required_skills": [
      { "skill_id": "skill_python", "importance": "critical" },
      { "skill_id": "skill_sql", "importance": "critical" },
      { "skill_id": "skill_ml", "importance": "important" }
    ],
    "preferred_skills": [
      { "skill_id": "skill_powerbi", "importance": "nice_to_have" }
    ],
    "experience": { "min_years": 0, "max_years": 2 },
    "education": ["Computer Science", "Computer Engineering", "Statistics"]
  },
  "location": {
    "country": "Egypt",
    "city": "Cairo",
    "work_mode": "hybrid"
  },
  "employment_type": "full_time",
  "source": {
    "source_id": "source_001",
    "url": "https://example.com/job/001"
  },
  "metadata": {
    "posted_at": "2026-09-01",
    "expires_at": "2026-09-30",
    "status": "active"
  }
}
```

---

### 🎯 Match Result Schema (Deterministic + Explainable)

> **قاعدة حساب الـ Score (0 → 100)**:
> `Score = (Required Skills * 50%) + (Preferred Skills * 10%) + (Experience * 15%) + (Responsibilities * 15%) + (Education * 5%) + (Preferences * 5%)`
> *الحساب رياضي حتمي (Deterministic)، والـ LLM يشرح أسباب النتيجة فقط.*

```json
{
  "match_id": "match_001",
  "candidate_id": "cand_001",
  "job_id": "job_001",
  "score": 84,
  "matched_skills": [
    {
      "skill_id": "skill_python",
      "candidate_level": "intermediate",
      "required_level": "intermediate",
      "evidence_strength": 0.92
    }
  ],
  "missing_skills": [
    {
      "skill_id": "skill_powerbi",
      "importance": "nice_to_have"
    }
  ],
  "weak_skills": [
    {
      "skill_id": "skill_statistics",
      "reason": "Job requires stronger statistical knowledge"
    }
  ],
  "constraints": [],
  "strengths": [
    "Strong Python background",
    "Relevant machine learning project experience"
  ],
  "gaps": [
    "Power BI",
    "Advanced statistics"
  ],
  "reasons": [
    {
      "type": "strength",
      "text": "You match the role well on Python, SQL and machine learning."
    },
    {
      "type": "gap",
      "text": "Power BI is missing from your profile."
    }
  ],
  "confidence": 0.89
}
```

---

### ⚡ Skill Gap Schema
```json
{
  "candidate_id": "cand_001",
  "job_id": "job_001",
  "skill_gaps": [
    {
      "skill_id": "skill_powerbi",
      "skill_name": "Power BI",
      "status": "missing",
      "priority": "high",
      "impact": 0.87,
      "reason": "Required by multiple target jobs"
    },
    {
      "skill_id": "skill_statistics",
      "skill_name": "Statistics",
      "status": "weak",
      "priority": "medium",
      "impact": 0.61,
      "reason": "Needed for the target role"
    }
  ]
}
```

---

### 🌟 Personalized Recommendations Schema
```json
{
  "candidate_id": "cand_001",
  "recommendations": [
    {
      "job_id": "job_001",
      "rank": 1,
      "score": 94,
      "reasons": [
        "High skill match",
        "Matches preferred location",
        "Matches target role"
      ]
    }
  ]
}
```

---

### 🛡️ AI Data Quality Review Schema (For Admin)
```json
{
  "issue_id": "issue_001",
  "entity_type": "job",
  "entity_id": "job_123",
  "issue_type": "possible_duplicate",
  "confidence": 0.93,
  "evidence": [
    "Same company",
    "Similar title",
    "87% description similarity"
  ],
  "recommended_action": "REVIEW"
}
```

---

## 🔗 3. API Contract Endpoints

### 👩‍💻 APIs Provided by Engineer 1 (You):
1. `GET /api/v1/candidates/{id}/profile` ➡️ Candidate Profile with extracted skills & evidence.
2. `GET /api/v1/jobs/{id}/requirements` ➡️ Structured & enriched job requirements.
3. `GET /api/v1/matches/{candidate_id}/{job_id}` ➡️ Explainable MatchResult (Deterministic score + LLM insights).
4. `GET /api/v1/candidates/{id}/skill-gaps/{job_id}` ➡️ Categorized Skill Gaps.
5. `GET /api/v1/candidates/{id}/recommendations` ➡️ Ranked & justified job recommendations.
6. `GET /api/v1/admin/data-quality/issues` ➡️ Low-confidence & anomalous items queue.

### 👨‍💻 APIs Provided by Engineer 2 (Teammate):
1. `POST /api/v1/roadmaps` & `GET /api/v1/roadmaps/{candidate_id}`
2. `POST /api/v1/mentor/chat`
3. `POST /api/v1/cv/review`
4. `POST /api/v1/interview/generate` & `POST /api/v1/interview/evaluate`
5. `POST /api/v1/application/advice`
6. `POST /api/v1/roadmap/review`
