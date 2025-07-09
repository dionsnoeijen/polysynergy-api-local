from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from collections.abc import Generator
from pathlib import Path
from services.state_service import get_state
from fastapi import Depends
from db.local_session import get_db

from models_project.base import ProjectBase


def get_project_engine(file_path: str):
    engine = create_engine(
        file_path,
        connect_args={"check_same_thread": False}
    )
    return engine

def init_project_db(file_path: str):
    engine = get_project_engine(file_path)
    ProjectBase.metadata.create_all(bind=engine)

def get_project_db(file_path: str) -> Generator[Session, None, None]:
    engine = get_project_engine(file_path)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_active_project_db(state_db: Session = Depends(get_db)) -> Generator[Session, None, None]:
    file_path = get_state("active_project", state_db)
    file_path = file_path.strip('"')

    if not file_path:
        raise RuntimeError("No active project is set in state.")
    yield from get_project_db(file_path)