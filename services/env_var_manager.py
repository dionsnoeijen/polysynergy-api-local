from polysynergy_node_runner.services.env_var_manager import EnvVarManager, get_env_var_manager_from_env

from core.settings import settings

def get_env_var_manager() -> EnvVarManager:
    return EnvVarManager(
        access_key=settings.AWS_ACCESS_KEY_ID,
        secret_key=settings.AWS_SECRET_ACCESS_KEY,
        region=settings.AWS_REGION
    )
