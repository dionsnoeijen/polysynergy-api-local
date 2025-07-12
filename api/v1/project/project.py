import uuid
import shutil

from fastapi import APIRouter, HTTPException, Depends
from cryptography.fernet import Fernet
from pathlib import Path
from sqlalchemy.orm import Session

from db.local_session import get_db
from db.project_session import get_active_project_db
from models.meta import ProjectMeta
from services.state_service import set_state

MOUNTED_PREFIX = "/Users/dionsnoeijen/polysynergy/orchestrator/api-local/tmp/projects"
DOCKER_PROJECTS_DIR = "/app/tmp/projects"

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parents[3]
TEMPLATE_DB = BASE_DIR / "project_db" / "project.psy"
TMP_DIR = BASE_DIR / "tmp" / "projects"
TMP_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/")
def create_project(db: Session = Depends(get_db)):
    project_id = str(uuid.uuid4())
    db_path = TMP_DIR / f"{project_id}.psy"

    try:
        shutil.copy(TEMPLATE_DB, db_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Copying template DB failed: {str(e)}")

    set_state('active_project', f"sqlite:///{str(db_path)}", db)

    encryption_key = Fernet.generate_key().decode()
    set_state('encryption_key', encryption_key, db)

    project_db = next(get_active_project_db(db))
    meta = ProjectMeta(id=project_id)

    project_db.add(meta)
    project_db.commit()

    return { "project_id": project_id }

@router.post("/load/")
def load_project(
    data: dict,
    db: Session = Depends(get_db)
):
    filename = data.get("psy")

    if not filename:
        raise HTTPException(status_code=400, detail="Missing file path")

    path = Path(filename)

    if not str(path).startswith(MOUNTED_PREFIX):
        raise HTTPException(status_code=400, detail="Invalid path")

    relative = path.relative_to(MOUNTED_PREFIX)
    internal_path = Path(DOCKER_PROJECTS_DIR) / relative

    if not internal_path.exists():
        raise HTTPException(status_code=404, detail="File not found in container")

    set_state('active_project', f"sqlite:///{str(internal_path)}", db)

    project_db = next(get_active_project_db(db))

    meta = project_db.query(ProjectMeta).first()

    return { "project_id": str(meta.id) }