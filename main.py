import models
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.v1.nodes import router as v1_nodes_router
from api.v1.project import router as v1_project_router
from api.v1.account import router as v1_account_router
from api.v1.execution import router as v1_execution_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # of ["*"] voor dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_nodes_router, prefix="/api/v1")
app.include_router(v1_project_router, prefix="/api/v1")
app.include_router(v1_account_router, prefix="/api/v1")
app.include_router(v1_execution_router, prefix="/api/v1")

