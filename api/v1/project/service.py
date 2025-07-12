from uuid import uuid4, UUID

from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from typing import List

from db.session import get_db
from models import NodeSetupVersion
from models.service import Service
from models.node_setup import NodeSetup
from schemas.service import ServiceOut, ServiceCreateIn

router = APIRouter()


@router.get("/", response_model=List[ServiceOut])
def list_services(db: Session = Depends(get_db)):
    services = db.query(Service).all()

    for s in services:
        try:
            node_setup = (
                db.query(NodeSetup)
                .filter_by(content_type="service", object_id=s.id)
                .first()
            )
            s.node_setup = node_setup
        except Exception:
            s.node_setup = None

    return services


@router.post("/", response_model=ServiceOut, status_code=status.HTTP_201_CREATED)
def create_service(
    data: ServiceCreateIn,
    db: Session = Depends(get_db)
):
    service = Service(
        id=str(uuid4()),
        name=data.name,
        meta=data.meta.dict() if data.meta else {},
    )
    db.add(service)
    db.flush()

    node_setup = NodeSetup(
        id=str(uuid4()),
        content_type="service",
        object_id=service.id,
    )
    db.add(node_setup)
    db.flush()

    version = NodeSetupVersion(
        id=str(uuid4()),
        node_setup_id=node_setup.id,
        version_number=1,
        content=data.node_setup_content or {},
    )
    db.add(version)

    db.commit()
    db.refresh(service)
    service.node_setup = node_setup

    return service

@router.put("/{service_id}/", response_model=ServiceOut)
def update_service(
    service_id: UUID,
    data: ServiceCreateIn,  # zelfde schema als voor create, tenzij je iets specifieks wilt
    db: Session = Depends(get_db)
):
    service = db.query(Service).filter(Service.id == str(service_id)).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    service.name = data.name
    service.meta = data.meta.dict() if data.meta else {}

    # Optional: update node_setup content
    if data.node_setup_content:
        try:
            node_setup = db.query(NodeSetup).filter_by(
                content_type="service",
                object_id=str(service_id)
            ).first()
            version_1 = db.query(NodeSetupVersion).filter_by(
                node_setup_id=node_setup.id,
                version_number=1
            ).first()
            version_1.content = data.node_setup_content
        except Exception:
            pass

    db.commit()
    db.refresh(service)

    return service

@router.delete("/{service_id}/", status_code=status.HTTP_204_NO_CONTENT)
def delete_service(
    service_id: UUID,
    db: Session = Depends(get_db)
):
    service = db.query(Service).filter(Service.id == str(service_id)).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    db.delete(service)
    db.commit()
