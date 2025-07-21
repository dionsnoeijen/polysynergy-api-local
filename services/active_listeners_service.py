from polysynergy_node_runner.services.active_listeners_service import (
    ActiveListenersService,
    get_active_listeners_service_from_env
)

from core.settings import settings

def get_active_listeners_service() -> ActiveListenersService:
    return get_active_listeners_service_from_env(
        access_key=settings.AWS_ACCESS_KEY_ID,
        secret_key=settings.AWS_SECRET_ACCESS_KEY,
        region=settings.AWS_REGION
    )
