from fastapi import APIRouter
from . import (
    project,
    blueprint,
    node_setup,
    stage,
    route,
    schedule,
    chat_window,
    chat_window_access,
    embed_token,
    service,
    secret,
    env_var,
    publish_matrix,
    api_key,
    avatar,
    listener,
    export_import,
    file_manager,
    agno_chat_history,
    templates,
)

router = APIRouter()

router.include_router(project.router, prefix="/projects", tags=["Project"])
router.include_router(blueprint.router, prefix="/blueprints", tags=["Blueprints"])
router.include_router(node_setup.router, prefix="/node-setup", tags=["Node Setup"])
router.include_router(stage.router, prefix="/stages", tags=["Stages"])
router.include_router(route.router, prefix="/routes", tags=["Routes"])
router.include_router(schedule.router, prefix="/schedules", tags=["Schedules"])
router.include_router(chat_window.router, prefix="/chat-windows", tags=["Chat Windows"])
router.include_router(chat_window_access.router, tags=["Chat Window Access"])
router.include_router(embed_token.router, prefix="/embed-tokens", tags=["Embed Tokens"])
router.include_router(service.router, prefix="/services", tags=["Services"])
router.include_router(secret.router, prefix="/secrets", tags=["Secrets"])
router.include_router(env_var.router, prefix="/env-vars", tags=["Environment Variables"])
router.include_router(publish_matrix.router, prefix="/publish-matrix", tags=["Publish Matrix"])
router.include_router(api_key.router, prefix="/api-keys", tags=["API Keys"])
router.include_router(avatar.router, prefix="/avatars", tags=["Avatars"])
router.include_router(listener.router, prefix="/listeners", tags=["Active Listeners"])
router.include_router(export_import.router, tags=["Export/Import"])
router.include_router(file_manager.router, prefix="/projects", tags=["File Manager"])
router.include_router(agno_chat_history.router, prefix="/agno-chat", tags=["Agno Chat History"])
router.include_router(templates.router, prefix="/templates", tags=["Templates"])
