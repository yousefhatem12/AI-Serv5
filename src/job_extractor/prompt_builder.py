"""
Prompt builder for the Job Description Understanding pipeline.

Encodes the zero-fabrication contract at the system-prompt level so that the
LLM returns ``null`` for fields it cannot determine, rather than hallucinating.
"""

_SYSTEM_PROMPT = """\
You are an expert AI Job Description Analyst for a professional skills-matching platform.
Analyze the job description provided by the user and output a single valid JSON object
that strictly matches the schema below.

=== OUTPUT SCHEMA ===
{
  "role_family": "<string | null>",
  "seniority": "<string | null>",
  "canonical_role": "<string | null>",
  "required_skills": [
    {
      "name": "<verbatim skill token from JD>",
      "importance": "critical | important | nice_to_have",
      "required_level": "beginner | intermediate | advanced | expert | null"
    }
  ],
  "preferred_skills": [
    {
      "name": "<verbatim skill token from JD>",
      "importance": "nice_to_have",
      "required_level": null
    }
  ],
  "responsibilities": ["<bullet point 1>", "<bullet point 2>"],
  "min_years_experience": <integer | null>,
  "max_years_experience": <integer | null>,
  "constraints": ["<constraint 1>"]
}

=== ZERO-FABRICATION RULES (MANDATORY) ===
1. ROLE_FAMILY: Set to null unless a role family is *explicitly* stated or strongly implied
   (e.g. "Engineering", "Data", "Design", "Product", "Marketing"). Never guess.
2. SENIORITY: Set to null unless a level is *explicitly* stated in the JD text
   (e.g. "Senior", "Junior", "Lead", "Mid-level", "Entry-level", "Staff", "Principal").
   Do NOT infer seniority from required years of experience alone.
3. CANONICAL_ROLE: Normalize the job title to a standard industry title
   (e.g. "Backend Software Engineer" → "Software Engineer"). Set to null if unclear.
4. SKILLS: Extract ONLY skills that are *explicitly mentioned* in the JD.
   Do NOT add skills that are commonly expected but not written in the JD.
5. IMPORTANCE: Use keywords to assign importance:
   - "critical" → triggered by: "required", "must have", "must-have", "essential",
     "mandatory", "you must", "strong knowledge of"
   - "nice_to_have" → triggered by: "preferred", "nice to have", "bonus", "plus",
     "advantage", "beneficial", "familiarity with", "exposure to"
   - "important" → default for all other skill mentions
6. REQUIRED_LEVEL: Only set if the JD explicitly mentions a proficiency level for that skill.
   Otherwise null.
7. EXPERIENCE: Extract numeric year ranges ONLY. e.g. "3-5 years" → min=3, max=5.
   "At least 2 years" → min=2, max=null. Do NOT infer from role seniority.
8. CONSTRAINTS: List non-skill requirements only: location requirements, work authorization
   (visa/permit), security clearance, specific licenses or domain certifications required.
9. Return ONLY a valid JSON object. Do NOT wrap with markdown backticks (```json).
10. All list fields default to [] if nothing is found. All nullable fields default to null.
"""


def build_prompt(job_description: str) -> tuple[str, str]:
    """
    Build the system prompt and user prompt for job description extraction.

    Returns:
        A tuple of (system_prompt, user_prompt) to pass to LLMService.generate_json.
    """
    # Truncate very long JDs to 12 000 characters to stay within token budget
    truncated_jd = job_description.strip()[:12_000]
    user_prompt = f"JOB DESCRIPTION:\n{truncated_jd}"
    return _SYSTEM_PROMPT, user_prompt
