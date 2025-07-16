from polysynergy_node_runner.services.secrets_manager import SecretsManager, get_secrets_manager_from_env

from core.settings import settings

def get_secrets_manager() -> SecretsManager:
    return get_secrets_manager_from_env(
        access_key=settings.AWS_ACCESS_KEY_ID,
        secret_key=settings.AWS_SECRET_ACCESS_KEY,
        region=settings.AWS_REGION
    )
