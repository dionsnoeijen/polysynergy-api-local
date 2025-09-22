import sys, six  # type: ignore
# maak de virtuele submodule meteen "echt" voor het import-systeem
sys.modules.setdefault("six.moves", six.moves)

from dotenv import load_dotenv
load_dotenv()

import time
import uuid
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from api.v1.nodes import router as v1_nodes_router
from api.v1.project import router as v1_project_router
from api.v1.account import router as v1_account_router
from api.v1.execution import router as v1_execution_router
from api.v1.documentation.documentation import router as v1_documentation_router

from ws.v1.execution import router as websocket_execution_router

# Setup logging
from core.logging_config import setup_logging, get_logger, LogContext
setup_logging()
logger = get_logger(__name__)

# Setup Sentry error tracking
from core.settings import settings
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.SENTRY_ENVIRONMENT,
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            StarletteIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
        ],
        traces_sample_rate=0.1,  # 10% van requests voor performance monitoring
        profiles_sample_rate=0.1,  # 10% profiling
        attach_stacktrace=True,
        send_default_pii=False,  # Geen persoonlijke info
        before_send=lambda event, hint: filter_sentry_event(event, hint),
    )
    logger.info_ctx("Sentry error tracking enabled", environment=settings.SENTRY_ENVIRONMENT)

def filter_sentry_event(event, hint):
    """Filter events before sending to Sentry"""
    # Skip health checks
    if "transaction" in event and "/health" in event["transaction"]:
        return None

    # Add custom context
    if "request" in event:
        request = event["request"]
        if "headers" in request:
            # Add request ID if available
            request_id = request["headers"].get("x-request-id")
            if request_id:
                event["tags"]["request_id"] = request_id

    return event

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info_ctx("PolySynergy API starting up",
                    environment="production" if "AWS_LAMBDA_FUNCTION_NAME" in os.environ else "local")
    yield
    # Shutdown
    logger.info("PolySynergy API shutting down")

app = FastAPI(title="PolySynergy API", version="1.0.0", lifespan=lifespan)

# Request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    # Add request ID to response headers
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

# Logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    request_id = getattr(request.state, "request_id", "unknown")

    # Add request ID to Sentry scope
    if settings.SENTRY_DSN:
        import sentry_sdk
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("request_id", request_id)
            scope.set_context("request", {
                "url": str(request.url),
                "method": request.method,
                "path": request.url.path
            })

    # Skip health checks to reduce noise
    if request.url.path == "/health":
        return await call_next(request)

    # Log request start
    with LogContext(request_id=request_id, path=request.url.path, method=request.method):
        logger.info(f"Request started: {request.method} {request.url.path}")

        try:
            response = await call_next(request)
            duration = round(time.time() - start_time, 3)

            # Log based on status code
            with LogContext(
                request_id=request_id,
                path=request.url.path,
                method=request.method,
                status_code=response.status_code,
                duration=duration
            ):
                if response.status_code >= 500:
                    logger.error(f"Request failed: {request.method} {request.url.path} - {response.status_code} in {duration}s")
                elif response.status_code >= 400:
                    logger.warning(f"Request client error: {request.method} {request.url.path} - {response.status_code} in {duration}s")
                else:
                    logger.info(f"Request completed: {request.method} {request.url.path} - {response.status_code} in {duration}s")

            return response

        except Exception as e:
            duration = round(time.time() - start_time, 3)
            with LogContext(
                request_id=request_id,
                path=request.url.path,
                method=request.method,
                duration=duration,
                error_type=type(e).__name__,
                error_message=str(e)
            ):
                logger.exception(f"Request exception: {request.method} {request.url.path}")

            # Sentry will automatically capture this exception

            return JSONResponse(
                status_code=500,
                content={
                    "detail": "Internal server error",
                    "request_id": request_id
                }
            )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # of ["*"] voor dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handler voor betere error logging
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "unknown")

    with LogContext(
        request_id=request_id,
        path=request.url.path,
        method=request.method,
        error_type=type(exc).__name__,
        error_message=str(exc)
    ):
        logger.exception("Unhandled exception")

    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "request_id": request_id
        }
    )

app.include_router(v1_nodes_router, prefix="/api/v1")
app.include_router(v1_project_router, prefix="/api/v1")
app.include_router(v1_account_router, prefix="/api/v1")
app.include_router(v1_execution_router, prefix="/api/v1")
app.include_router(v1_documentation_router, prefix="/api/v1/documentation", tags=["documentation"])
app.include_router(websocket_execution_router, prefix="/ws/v1")

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "polysynergy-api"}


