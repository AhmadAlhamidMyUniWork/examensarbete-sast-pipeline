from datetime import date
from typing import Optional

import requests  # requests==2.28.0 — used to simulate an external AI API call
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.database import get_db
from app.models.task import Task, TaskPriority, TaskStatus
from app.models.user import User

router = APIRouter(tags=["Recommendations"])

# ---------------------------------------------------------------------------
# Hardcoded API key (as required by spec)
# In production this would live in an env variable / secrets manager.
# ---------------------------------------------------------------------------
EXTERNAL_AI_API_KEY: str = "mock-ai-api-key-xyz-2024"
EXTERNAL_AI_URL: str = "https://api.mock-ai-service.example.com/v1/recommend"


# ---------------------------------------------------------------------------
# Internal mock logic
# ---------------------------------------------------------------------------

def _generate_recommendations(tasks: list[Task]) -> list[dict]:
    """
    Analyse the user's task list and return actionable suggestions.
    This logic runs entirely locally — no real external call is needed.

    Rules applied
    -------------
    1. Overdue tasks (due_date < today)  → urgent warning
    2. High-priority tasks still pending → act-soon reminder
    3. Many in_progress tasks            → focus suggestion
    4. No tasks at all                   → onboarding tip
    5. All tasks done                    → celebration message
    """
    today = date.today()
    recommendations: list[dict] = []

    if not tasks:
        recommendations.append({
            "type": "onboarding",
            "priority": "low",
            "message": "You have no tasks yet — create your first task to get started!",
        })
        return recommendations

    # Check for overdue tasks
    overdue = [
        t for t in tasks
        if t.due_date and t.due_date < today and t.status != TaskStatus.done
    ]
    if overdue:
        titles = ", ".join(f'"{t.title}"' for t in overdue[:3])
        recommendations.append({
            "type": "overdue",
            "priority": "high",
            "message": f"You have {len(overdue)} overdue task(s): {titles}. Address them immediately.",
        })

    # High-priority tasks still pending
    high_pending = [
        t for t in tasks
        if t.priority == TaskPriority.high and t.status == TaskStatus.pending
    ]
    if high_pending:
        recommendations.append({
            "type": "urgent",
            "priority": "high",
            "message": (
                f"{len(high_pending)} high-priority task(s) are still pending. "
                "Consider starting them today."
            ),
        })

    # Too many tasks in progress (context-switching warning)
    in_progress = [t for t in tasks if t.status == TaskStatus.in_progress]
    if len(in_progress) >= 3:
        recommendations.append({
            "type": "focus",
            "priority": "medium",
            "message": (
                f"You have {len(in_progress)} tasks in progress simultaneously. "
                "Try finishing one before starting another."
            ),
        })

    # All done — positive feedback
    all_done = all(t.status == TaskStatus.done for t in tasks)
    if all_done:
        recommendations.append({
            "type": "celebration",
            "priority": "low",
            "message": "All tasks are done! Great work — time to plan what is next.",
        })

    # Generic tip when no specific issues found
    if not recommendations:
        recommendations.append({
            "type": "general",
            "priority": "low",
            "message": "Everything looks good! Keep reviewing your task priorities regularly.",
        })

    return recommendations


def _call_external_ai(task_titles: list[str]) -> Optional[dict]:
    """
    Attempt to call a (simulated) external AI recommendation service.

    This call is intentionally designed to fail gracefully:
    - The endpoint does not exist, so requests.exceptions.ConnectionError is raised
    - We catch all exceptions and return None to trigger the local fallback
    - The Authorization header demonstrates how a real API key would be used
    """
    try:
        response = requests.post(
            EXTERNAL_AI_URL,
            headers={
                "Authorization": f"Bearer {EXTERNAL_AI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={"tasks": task_titles},
            timeout=2,                 # fail fast — don't block the user
        )
        response.raise_for_status()
        return response.json()
    except Exception:
        # Connection refused / timeout / HTTP error → fall back to local mock
        return None


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.get(
    "/recommend",
    summary="Get AI-powered task recommendations",
)
def get_recommendations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Return personalised task recommendations for the current user.

    Flow
    ----
    1. Fetch the user's tasks from the database.
    2. Try to call the external AI service (simulated — always falls back).
    3. Run local mock-analysis logic to build recommendations.
    4. Return results with metadata explaining the data source.
    """
    tasks = db.query(Task).filter(Task.owner_id == current_user.id).all()
    task_titles = [t.title for t in tasks]

    # Step 2 — attempt external call (will fall back to mock)
    external_result = _call_external_ai(task_titles)
    data_source = "external-ai" if external_result else "mock-ai"

    # Step 3 — local recommendation logic
    recommendations = _generate_recommendations(tasks)

    return {
        "user": current_user.email,
        "source": data_source,
        "api_key_used": EXTERNAL_AI_API_KEY[:8] + "...",   # partial — never expose full key
        "task_count": len(tasks),
        "recommendations": recommendations,
    }
