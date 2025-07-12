from fastapi import Depends

from db.local_session import get_db
from db.project_session import get_active_project_db
from services.local_secrets_service import LocalSecretsService
from services.state_service import get_state
from sqlalchemy.orm import Session

def get_local_secrets_service(
    local_db: Session = Depends(get_db),
    project_db: Session = Depends(get_active_project_db)
) -> LocalSecretsService:
    encryption_key = get_state("encryption_key", local_db)
    return LocalSecretsService(encryption_key, project_db)