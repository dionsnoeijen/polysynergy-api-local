from polysynergy_node_runner.services.execution_storage_service import (
    DynamoDbExecutionStorageService,
    get_execution_storage_service_from_env
)

from core.settings import settings

def get_execution_storage_service() -> DynamoDbExecutionStorageService:
    return get_execution_storage_service_from_env(
        access_key=settings.AWS_ACCESS_KEY_ID,
        secret_key=settings.AWS_SECRET_ACCESS_KEY,
        region=settings.AWS_REGION
    )