from __future__ import annotations
from crewai import Task
from src.ai.crew.agents import mentor_agent, roadmap_agent, job_insights_agent


def build_mentor_task(user_message: str, context: dict) -> Task:
    return Task(
        description=(
            f"User message: {user_message}\n\n"
            f"Candidate context provided: {context}\n\n"
            "Apply the following 7 Core Capabilities & Principles where relevant:\n"
            "1. Goal Clarification: If the user states a broad goal (e.g. 'I want a backend internship'), help turn it into a target role, timeframe, and concrete milestones.\n"
            "2. Weekly Action Planning: Convert skill gaps into a manageable weekly plan (practice tasks, portfolio improvements, CV updates, targeted applications).\n"
            "3. Job-Specific Advice: If asking about a job, ground advice strictly in that job's requirements and the candidate's verified profile.\n"
            "4. Roadmap Adjustment: Reprioritize milestones if the user added skills, completed projects, or changed target roles.\n"
            "5. Application Debrief: If discussing rejections or interview stages, capture lessons and improvement steps without claiming insight into hidden employer decisions.\n"
            "6. Interview Readiness: Highlight concrete topics to practice before interviews based on role requirements and skill gaps.\n"
            "7. Truthfulness & Boundaries: Never invent qualifications, never promise guaranteed hiring probabilities, and ask for missing evidence when needed."
        ),
        expected_output="An evidence-based, actionable response adhering to the 7 core mentoring principles.",
        agent=mentor_agent,
    )


def build_roadmap_task(user_message: str, context: dict) -> Task:
    return Task(
        description=(
            f"User message: {user_message}\n\n"
            f"Candidate context provided: {context}\n\n"
            "Focus on Weekly Action Planning & Roadmap Adjustment:\n"
            "- Convert skill gaps and milestones into manageable weekly action plans (tasks, portfolio projects, CV updates).\n"
            "- Reprioritize the roadmap dynamically if new skills are added, projects finished, or target roles changed.\n"
            "- Uphold Truthfulness & Boundaries by setting realistic, achievable timelines without fabricating prerequisites."
        ),
        expected_output="A structured, reprioritized roadmap update or weekly action plan based on verified gaps.",
        agent=roadmap_agent,
    )


def build_job_insights_task(user_message: str, context: dict) -> Task:
    return Task(
        description=(
            f"User message: {user_message}\n\n"
            f"Candidate context provided: {context}\n\n"
            "Focus on Job-Specific Advice, Interview Readiness & Application Debrief:\n"
            "- Compare the candidate's verified CV against specific job requirements with transparent evidence.\n"
            "- Identify high-priority topics and practical exercises needed for interview readiness.\n"
            "- If debriefing an application/rejection, extract constructive takeaways without claiming knowledge of hidden employer processes.\n"
            "- Maintain strict Truthfulness & Boundaries (no guaranteed hiring probabilities, no invented qualifications)."
        ),
        expected_output="A transparent job compatibility report, interview readiness plan, or application debrief.",
        agent=job_insights_agent,
    )
