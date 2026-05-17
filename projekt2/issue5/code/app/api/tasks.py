from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.database import get_db
from app.models.task import Task, TaskStatus
from app.models.user import User, UserRole
from app.schemas.task import TaskCreate, TaskOut, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.get("/", response_model=List[TaskOut])
def get_tasks(status_filter: Optional[TaskStatus] = Query(None, alias="status"),
              db: Session = Depends(get_db),
              current_user: User = Depends(get_current_user)) -> List[TaskOut]:
    query = db.query(Task) if current_user.role == UserRole.admin else \
            db.query(Task).filter(Task.owner_id == current_user.id)
    if status_filter:
        query = query.filter(Task.status == status_filter)
    return query.all()


@router.post("/", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(task_data: TaskCreate, db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user)) -> TaskOut:
    task = Task(**task_data.dict(), owner_id=current_user.id)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.put("/{task_id}", response_model=TaskOut)
def update_task(task_id: int, task_data: TaskUpdate, db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user)) -> TaskOut:
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task {task_id} not found")
    fields = task_data.dict(exclude_unset=True)
    if not fields:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No fields to update")
    for k, v in fields.items():
        setattr(task, k, v)
    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user)) -> None:
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task {task_id} not found")
    if current_user.role != UserRole.admin and task.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only delete your own tasks")
    db.delete(task)
    db.commit()
