# Import both models here so that SQLAlchemy's Base.metadata knows about
# all tables before create_all() is called in main.py startup.
from app.models.user import User  # noqa: F401
from app.models.task import Task  # noqa: F401
