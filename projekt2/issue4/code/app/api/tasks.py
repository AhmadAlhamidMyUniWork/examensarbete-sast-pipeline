from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.database import get_db
from app.models.task import Task, TaskStatus
from app.models.user import User, UserRole
from app.schemas.task import TaskCreate, TaskOut, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["Tasks"])


# ---------------------------------------------------------------------------
# GET /tasks  — list tasks
# ---------------------------------------------------------------------------
@router.get(
    "/",
    response_model=List[TaskOut],
    summary="List tasks",
)
def get_tasks(
    status_filter: Optional[TaskStatus] = Query(None, alias="status", description="Filter by status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[TaskOut]:
    """
    Return tasks visible to the current user.

    Role logic
    ----------
    - **admin** : sees ALL tasks in the system (across all users)
    - **user**  : sees only tasks where owner_id == their own id

    Optional query parameter `?status=pending|in_progress|done` narrows results.
    """
    # Admin gets a global view; regular users see only their own tasks
    if current_user.role == UserRole.admin:
        query = db.query(Task)
    else:
        query = db.query(Task).filter(Task.owner_id == current_user.id)

    # Optional status filter (works for both roles)
    if status_filter:
        query = query.filter(Task.status == status_filter)

    return query.all()


# ---------------------------------------------------------------------------
# POST /tasks  — create a task
# ---------------------------------------------------------------------------
@router.post(
    "/",
    response_model=TaskOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new task",
)
def create_task(
    task_data: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskOut:
    """
    Create a new task owned by the currently authenticated user.
    The `owner_id` is taken from the JWT — the client cannot set it.
    """
    new_task = Task(
        **task_data.dict(),
        owner_id=current_user.id,   # always bound to the logged-in user
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task


# ---------------------------------------------------------------------------
# PUT /tasks/{task_id}  — update a task
# ---------------------------------------------------------------------------
@router.put(
    "/{task_id}",
    response_model=TaskOut,
    summary="Update an existing task",
)
def update_task(
    task_id: int,
    task_data: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskOut:
    """
    Update one or more fields of an existing task.

    Ownership note
    --------------
    Per the issue spec ownership is kept deliberately loose:
    any authenticated user can edit any task (no strict owner check).
    Admin users can naturally update any task as well.
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id={task_id} not found",
        )

    # exclude_unset=True → only fields explicitly sent in the request body
    # are applied, so omitted fields keep their current DB values
    update_fields = task_data.dict(exclude_unset=True)
    if not update_fields:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No fields provided for update",
        )

    for field, value in update_fields.items():
        setattr(task, field, value)

    db.commit()
    db.refresh(task)
    return task


# ---------------------------------------------------------------------------
# DELETE /tasks/{task_id}  — delete a task (optional endpoint)
# ---------------------------------------------------------------------------
@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a task",
)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """
    Permanently delete a task.

    Role logic
    ----------
    - **admin**  : can delete any task
    - **user**   : can only delete tasks they own
      (this is the one place where a lightweight owner check is applied
       to avoid accidental cross-user deletions)
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id={task_id} not found",
        )

    # Only enforce ownership on DELETE (not on PUT, per spec)
    if current_user.role != UserRole.admin and task.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own tasks",
        )

    db.delete(task)
    db.commit()
