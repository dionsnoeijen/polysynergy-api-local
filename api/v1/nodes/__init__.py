from fastapi import APIRouter
from . import nodes

router = APIRouter()

router.include_router(nodes.router, tags=["Nodes"])