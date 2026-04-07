import jmespath
import json
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class JmesRequest(BaseModel):
    data: dict | list
    expression: str


class JmesResponse(BaseModel):
    result: str | None = None
    error: str | None = None


@router.post("/jmes", response_model=JmesResponse)
async def execute_jmes_query(request: JmesRequest):
    try:
        result = jmespath.search(request.expression, request.data)
        return JmesResponse(result=json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as e:
        return JmesResponse(error=str(e))
