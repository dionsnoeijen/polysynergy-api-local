from polysynergy_node_runner.services.s3_service import S3Service


def get_s3_service(
    tenant_id: str,
    project_id: str = "default",
) -> S3Service:
    """
    Get an S3Service instance for the given tenant and project.

    Args:
        tenant_id: The tenant ID
        project_id: The project ID (defaults to "default" for tenant-wide resources)

    Returns:
        Configured S3Service instance
    """
    return S3Service(
        tenant_id=tenant_id,
        project_id=project_id
    )
