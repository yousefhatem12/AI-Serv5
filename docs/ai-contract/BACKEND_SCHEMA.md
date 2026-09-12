# 📄 Backend DB Schema vs. AI Engine Contract — Alignment & Modifications
# 📄 Backend DB Schema vs. AI Engine Contract — Alignment & Specifications

> **Objective:** Outline the discrepancies, missing tables, and required column additions in the Backend Database Schema to ensure 100% compatibility with the AI Engine services (**CV Extraction, Skill Matching & Recommendation, and Coaching Track**).

---

## 📌 Executive Summary

1. **إضافة 4 جداول جديدة أساسية (New Tables):**
   * `cv_files`: لتخزين وتتبع ملفات الـ CV المرفوعة وحالة معالجتها.
   * `job_matches`: لتخزين نتائج المطابقة والـ Score والـ Reasons وتوصيات الوظائف للمرشح.
   * `roadmaps` & `roadmap_steps`: لتخزين خطط التطوير المهني (Engineer 2 / Coaching Track).
   * `data_quality_issues`: لتخزين بلاغات الـ Admin مراجعة جودة البيانات والوظائف المكررة.
1. **4 New Required Tables:**
   * `cv_files`: To track uploaded CV files, storage paths, and processing lifecycle status.
   * `job_matches`: To persist calculated match scores, breakdown of missing/matched skills, and AI-generated explainability reasons.
   * `roadmaps` & `roadmap_steps`: To support candidate learning paths and skill gap remediation (Engineer 2 / Coaching Track).
   * `data_quality_issues`: To queue low-confidence AI extractions or duplicate job postings for Admin review.

2. **تعديل 5 جداول حالية بإضافة حقول حيوية (Missing Fields in Existing Tables):**
   * `candidate_skills`: إضافة `confidence` و `evidence`.
   * `job_skills`: إضافة `required_level` (مستوى المهارة المطلوب).
   * `jobs`: إضافة `min_years_experience` و `max_years_experience` و `responsibilities`.
   * `career_preferences`: تحويل `target_role` إلى `target_roles` (Array/JSON) وإضافة `preferred_industries`.
   * `experiences`: إضافة `technologies` (JSON Array).
2. **5 Existing Tables Requiring Field Additions:**
   * `candidate_skills`: Add `confidence` score and extracted text `evidence`.
   * `job_skills`: Add `required_level` (minimum proficiency required by the job).
   * `jobs`: Add numerical experience bounds (`min_years_experience`, `max_years_experience`), `responsibilities`, and `canonical_role`.
   * `career_preferences`: Convert `target_role` to multi-valued `target_roles` (JSONB) and add `preferred_industries`.
   * `experiences`: Add `technologies` (JSONB array).

---

## 🏛️ Detailed Technical Specifications & DDL Migrations

### 1️⃣ الجداول الجديدة المطلوبة (New Tables)
### 1️⃣ Proposed New Tables

#### A. جدول ملفات الـ CV المرفوعة (`cv_files`)
> **السبب:** الذكاء الاصطناعي يحتاج معرفة مكان الملف المرفوع، تتبع حالة الـ Parsing (`queued`, `processing`, `completed`, `failed`)، وربطه بالمرشح.
#### A. CV Uploads & Parsing Lifecycle (`cv_files`)
> **Rationale:** The AI engine requires a deterministic reference to uploaded CV documents, file storage URIs, and background extraction job statuses (`queued`, `processing`, `completed`, `failed`).

```sql
CREATE TABLE cv_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_profile_id UUID NOT NULL REFERENCES candidate_profiles(id) ON DELETE CASCADE,
    file_url VARCHAR(500) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_size_bytes INT,
    mime_type VARCHAR(100),
    status VARCHAR(50) DEFAULT 'queued', -- queued | processing | completed | failed
    status VARCHAR(50) DEFAULT 'queued', -- 'queued' | 'processing' | 'completed' | 'failed'
    error_message TEXT NULL,
    parsed_at TIMESTAMP WITH TIME ZONE NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

---

#### B. Candidate Job Match Results (`job_matches`)
> **Rationale:** The AI Engine computes a deterministic match score alongside structured explainability metrics (`matched_skills`, `missing_skills`, `weak_skills`, `reasons`). Persisting these results enables fast UI rendering and historical recommendation tracking.

```sql
CREATE TABLE job_matches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_profile_id UUID NOT NULL REFERENCES candidate_profiles(id) ON DELETE CASCADE,
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    score DECIMAL(5, 2) NOT NULL, -- Score 0.00 to 100.00
    matched_skills JSONB DEFAULT '[]', -- [{skill_id, candidate_level, required_level, evidence_strength}]
    missing_skills JSONB DEFAULT '[]', -- [{skill_id, importance}]
    weak_skills JSONB DEFAULT '[]', -- [{skill_id, reason}]
    reasons JSONB DEFAULT '[]', -- [{type: "strength"|"gap", text: "..."}]
    score DECIMAL(5, 2) NOT NULL, -- Score from 0.00 to 100.00
    matched_skills JSONB DEFAULT '[]', -- Array of [{skill_id, candidate_level, required_level, evidence_strength}]
    missing_skills JSONB DEFAULT '[]', -- Array of [{skill_id, importance}]
    weak_skills JSONB DEFAULT '[]', -- Array of [{skill_id, reason}]
    reasons JSONB DEFAULT '[]', -- Array of [{type: "strength"|"gap", text: "..."}]
    confidence DECIMAL(3, 2) DEFAULT 0.85,
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(candidate_profile_id, job_id)
);
```

---

#### C. Career Roadmap & Coaching Track (`roadmaps` & `roadmap_steps`)
> **Rationale:** Supports Engineer 2 features for generating personalized career roadmaps and step-by-step guidance based on detected skill gaps.

```sql
CREATE TABLE roadmaps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_profile_id UUID NOT NULL REFERENCES candidate_profiles(id) ON DELETE CASCADE,
    target_job_id UUID NULL REFERENCES jobs(id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    overall_progress DECIMAL(5, 2) DEFAULT 0.00,
    status VARCHAR(50) DEFAULT 'active', -- active | completed | archived
    status VARCHAR(50) DEFAULT 'active', -- 'active' | 'completed' | 'archived'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE roadmap_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    roadmap_id UUID NOT NULL REFERENCES roadmaps(id) ON DELETE CASCADE,
    step_order INT NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    target_skill_id UUID NULL REFERENCES skills(id),
    status VARCHAR(50) DEFAULT 'pending', -- pending | in_progress | completed
    resources JSONB DEFAULT '[]', -- [{title, url, type}]
    status VARCHAR(50) DEFAULT 'pending', -- 'pending' | 'in_progress' | 'completed'
    resources JSONB DEFAULT '[]', -- Array of [{title, url, type}]
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

---
#### D. Admin Data Quality Review Queue (`data_quality_issues`)
> **Rationale:** Stores low-confidence extractions (`confidence < 0.50`), duplicate job listings, or taxonomy anomalies for administrative moderation.

```sql
CREATE TABLE data_quality_issues (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type VARCHAR(50) NOT NULL, -- job | candidate_skill | company
    entity_type VARCHAR(50) NOT NULL, -- 'job' | 'candidate_skill' | 'company'
    entity_id UUID NOT NULL,
    issue_type VARCHAR(100) NOT NULL, -- possible_duplicate | low_confidence | anomalous_data
    issue_type VARCHAR(100) NOT NULL, -- 'possible_duplicate' | 'low_confidence' | 'anomalous_data'
    confidence DECIMAL(3, 2) NOT NULL,
    evidence JSONB DEFAULT '[]',
    recommended_action VARCHAR(100) DEFAULT 'REVIEW', -- REVIEW | IGNORE | MERGE
    status VARCHAR(50) DEFAULT 'pending', -- pending | resolved | dismissed
    recommended_action VARCHAR(100) DEFAULT 'REVIEW', -- 'REVIEW' | 'IGNORE' | 'MERGE'
    status VARCHAR(50) DEFAULT 'pending', -- 'pending' | 'resolved' | 'dismissed'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

---
### 2️⃣ Alterations to Existing Tables

#### 🔹 1. جدول `candidate_skills`
* **الحقول المطلوبة إضافتها:**
  * `confidence`: `DECIMAL(3, 2)` — درجة ثقة استخراج المهارة من الـ CV (من `0.00` إلى `1.00`).
  * `evidence`: `JSONB` — الاقتباسات والأدلة المأخوذة من الـ CV التي تثبت المهارة `[{type, text, section, source}]`.
#### 🔹 1. `candidate_skills` Table
* **Required Additions:**
  * `confidence`: `DECIMAL(3, 2)` — AI extraction confidence score (`0.00` to `1.00`).
  * `evidence`: `JSONB` — Quotes/snippets from the CV validating the skill `[{type, text, section, source}]`.

```sql
ALTER TABLE candidate_skills 
ADD COLUMN confidence DECIMAL(3, 2) DEFAULT 0.85,
ADD COLUMN evidence JSONB DEFAULT '[]';
```

---

#### 🔹 2. جدول `job_skills`
* **الحقول المطلوبة إضافتها والتأكد منها:**
  * `required_level`: `VARCHAR(50)` — المستوى المطلوب للمهارة في هذه الوظيفة (`beginner`, `intermediate`, `advanced`, `expert`).
  * `importance`: التأكد أن القيم المسندة إليه تنتمي للـ Enum: (`critical`, `important`, `nice_to_have`).
#### 🔹 2. `job_skills` Table
* **Required Additions & Validation:**
  * `required_level`: `VARCHAR(50)` — Minimum proficiency level expected for the job (`beginner`, `intermediate`, `advanced`, `expert`).
  * `importance`: Ensure values strictly follow the enum: (`critical`, `important`, `nice_to_have`).

```sql
ALTER TABLE job_skills 
ADD COLUMN required_level VARCHAR(50) DEFAULT 'intermediate';
```

---

#### 🔹 3. جدول `jobs`
* **الحقول المطلوبة إضافتها:**
  * `min_years_experience`: `INT` — الحد الأدنى لسنوات الخبرة (مثال: 0).
  * `max_years_experience`: `INT` — الحد الأقصى لسنوات الخبرة (مثال: 2).
  * `responsibilities`: `JSONB` — قائمة المسؤوليات المستخرجة والمهيكلة من الـ Description.
  * `canonical_role`: `VARCHAR(150)` — المسمى الوظيفي النمطي المنظم المعتمد لدى الـ AI taxonomy (مثل: "Data Scientist").
#### 🔹 3. `jobs` Table
* **Required Additions:**
  * `min_years_experience`: `INT` — Lower bound of required experience in years (e.g., `0`).
  * `max_years_experience`: `INT` — Upper bound of required experience in years (e.g., `2`).
  * `responsibilities`: `JSONB` — Structured bullet points extracted from the job description.
  * `canonical_role`: `VARCHAR(150)` — Normalized role title mapped to taxonomy (e.g., `"Data Scientist"`).

```sql
ALTER TABLE jobs 
ADD COLUMN min_years_experience INT DEFAULT 0,
ADD COLUMN max_years_experience INT NULL,
ADD COLUMN responsibilities JSONB DEFAULT '[]',
ADD COLUMN canonical_role VARCHAR(150) NULL;
```

---

#### 🔹 4. جدول `career_preferences`
* **التعديلات الحيوية:**
  * تغيير `target_role` لتصبح `target_roles` من نوع `JSONB` أو `TEXT[]` لتمكين المرشح من إدخال أكثر من مسمى وظيفي مستهدف.
  * إضافة `preferred_industries`: `JSONB` — المجالات المفضلة (مثل: `["FinTech", "Technology"]`).
  * تحويل `work_mode` و `job_type` لتكون قابلة لتخزين مصفوفة `JSONB` لتمكين اختيار أكثر من نمط عمل (مثل: `["remote", "hybrid"]`).
#### 🔹 4. `career_preferences` Table
* **Required Modifications:**
  * Change `target_role` to `target_roles` (`JSONB` or `TEXT[]`) allowing candidates to target multiple career tracks.
  * Add `preferred_industries`: `JSONB` — Target industries (e.g., `["FinTech", "Technology"]`).
  * Ensure `work_mode` and `job_type` accommodate JSON arrays for multi-selection (e.g., `["remote", "hybrid"]`).

```sql
ALTER TABLE career_preferences 
ADD COLUMN target_roles JSONB DEFAULT '[]',
ADD COLUMN preferred_industries JSONB DEFAULT '[]';
```

---

#### 🔹 5. جدول `experiences`
* **الحقل المطلوب إضافته:**
  * `technologies`: `JSONB` — قائمة الأدوات والتقنيات والمكتبات المستخدمة في هذه الخبرة السابقة.
#### 🔹 5. `experiences` Table
* **Required Additions:**
  * `technologies`: `JSONB` — Array of tools, libraries, and frameworks used in the work experience item.

```sql
ALTER TABLE experiences 
ADD COLUMN technologies JSONB DEFAULT '[]';
```

---

## 🔄 ملخص الفروقات الأساسية بين الـ DB والـ AI Schemas
## 🔄 Summary Matrix: Current Schema vs. AI Engine Contract

| الكيان / الجدول | الموجود حالياً لدى الباك إند | المطلوب للتوافق مع الـ AI Engine | السبب والهدف الفني |
| Entity / Table | Current Backend Schema | Required AI Contract Target | Rationale & Impact |
| :--- | :--- | :--- | :--- |
| **`cv_files`** | ❌ غير موجود | ✅ جدول مستقل بحالة الـ Parsing والـ File URL | لتتبع رفع الـ CV ومعالجته بالـ AI |
| **`job_matches`** | ❌ غير موجود | ✅ جدول ناتج المطابقة والـ Score والـ Reasons | لحفظ وتصفح التوصيات والـ Match Results |
| **`candidate_skills`** | `proficiency_level`, `source` | ➕ إضافة `confidence` و `evidence` | لإظهار أسباب ودرجة ثقة استخراج المهارة |
| **`job_skills`** | `is_required`, `importance` | ➕ إضافة `required_level` | لمقارنة مستويات المهارة المطلوبة بدقة |
| **`jobs`** | `experience_level` (String) | ➕ إضافة `min_years_experience` و `max_years_experience` | لحساب سكور الخبرة بشكل حتمي (Deterministic) |
| **`career_preferences`**| `target_role` (Single String) | 🔄 `target_roles` (JSON Array) + `preferred_industries` | للسماح باستهداف أكثر من تخصص ومجال |
| **`cv_files`** | ❌ Missing | ✅ Dedicated table with status & file URL | Enables CV upload tracking & parsing pipeline execution |
| **`job_matches`** | ❌ Missing | ✅ Dedicated match score & explainability table | Persists match results, recommendations, and evidence |
| **`candidate_skills`** | `proficiency_level`, `source` | ➕ Add `confidence` & `evidence` | Supports explainable AI extraction auditing |
| **`job_skills`** | `is_required`, `importance` | ➕ Add `required_level` | Required for multi-level skill match scoring |
| **`jobs`** | `experience_level` (String) | ➕ Add `min_years_experience` & `max_years_experience` | Enables deterministic experience score calculation |
| **`career_preferences`**| `target_role` (Single String) | 🔄 `target_roles` (JSON) + `preferred_industries` | Allows candidate targeting across multiple roles/industries |
| **`experiences`** | `description` only | ➕ Add `technologies` (JSON) | Captures technology stack used per employment role |

---