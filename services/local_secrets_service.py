from typing import Type

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime
from models.secret import ProjectSecret

class LocalSecretsService:
    def __init__(self, encryption_key: str, db: Session):
        self.fernet = Fernet(encryption_key.encode())
        self.db = db

    def encrypt(self, value: str) -> str:
        return self.fernet.encrypt(value.encode()).decode()

    def decrypt(self, value: str) -> str | None:
        try:
            return self.fernet.decrypt(value.encode()).decode()
        except InvalidToken:
            return None

    def list(self) -> list[Type[ProjectSecret]]:
        return self.db.query(ProjectSecret).all()

    def get(self, secret_id: str) -> ProjectSecret | None:
        return self.db.query(ProjectSecret).filter(ProjectSecret.id == secret_id).first()

    def create(self, key: str, value: str, stage: str) -> ProjectSecret:
        encrypted = self.encrypt(value)
        secret = ProjectSecret(
            id=str(uuid4()),
            key=key,
            value=encrypted,
            stage=stage,
            created_at=datetime.utcnow()
        )
        self.db.add(secret)
        self.db.commit()
        self.db.refresh(secret)
        return secret

    def update(self, secret_id: str, new_value: str) -> ProjectSecret | None:
        secret = self.get(secret_id)
        if not secret:
            return None
        secret.value = self.encrypt(new_value)
        self.db.commit()
        return secret

    def delete(self, secret_id: str) -> bool:
        secret = self.get(secret_id)
        if not secret:
            return False
        self.db.delete(secret)
        self.db.commit()
        return True