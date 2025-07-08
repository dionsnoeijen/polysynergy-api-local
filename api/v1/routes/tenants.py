from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db.session import get_db
from models.tenant import Tenant
from schemas.tenant import TenantCreate
import uuid

router = APIRouter()

@router.get("/")
def list_tenants(db: Session = Depends(get_db)):
    return db.query(Tenant).all()

@router.post("/")
def create_tenant(payload: TenantCreate, db: Session = Depends(get_db)):
    existing = db.query(Tenant).filter(Tenant.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Tenant already exists")

    tenant = Tenant(id=str(uuid.uuid4()), name=payload.name)
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant