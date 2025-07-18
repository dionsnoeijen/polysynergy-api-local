from polysynergy_node_runner.services.s3_service import S3Service, get_s3_service_from_env

from core.settings import settings

def get_s3_service(
    tenant_id: str,
    public: bool = False,
) -> S3Service:
    return S3Service(
        tenant_id=tenant_id,
        public=public,
        access_key=settings.AWS_ACCESS_KEY_ID,
        secret_key=settings.AWS_SECRET_ACCESS_KEY,
        region=settings.AWS_REGION
    )