from fastapi import Depends

from db.project_session import get_active_project_db
from services.local_secrets_service import LocalSecretsService
from services.state_service import get_state
from sqlalchemy.orm import Session

def get_local_secrets_service(db: Session = Depends(get_active_project_db)) -> LocalSecretsService:
    encryption_key = get_state("encryption_key", db)
    return LocalSecretsService(encryption_key, db)