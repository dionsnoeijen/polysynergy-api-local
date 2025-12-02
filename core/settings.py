from pydantic import EmailStr
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_NAME: str
    DATABASE_USER: str
    DATABASE_PASSWORD: str
    DATABASE_HOST: str
    DATABASE_PORT: int = 5432

    # Agno Session Database (separate from main API database)
    AGNO_DB_NAME: str | None = None
    AGNO_DB_USER: str | None = None
    AGNO_DB_PASSWORD: str | None = None
    AGNO_DB_HOST: str | None = None
    AGNO_DB_PORT: int | None = None

    # Sections Database (for dynamic section content tables)
    SECTIONS_DB_NAME: str | None = None
    SECTIONS_DB_USER: str | None = None
    SECTIONS_DB_PASSWORD: str | None = None
    SECTIONS_DB_HOST: str | None = None
    SECTIONS_DB_PORT: int | None = None

    # Lambda-specific database URLs (for AWS Lambda functions)
    # These should point to publicly accessible RDS instances or VPC-configured endpoints
    LAMBDA_DATABASE_URL: str | None = None
    LAMBDA_SECTIONS_DATABASE_URL: str | None = None

    REDIS_URL: str | None = None

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+psycopg2://{self.DATABASE_USER}:"
            f"{self.DATABASE_PASSWORD}@{self.DATABASE_HOST}:"
            f"{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )

    @property
    def SECTIONS_DATABASE_URL(self) -> str:
        """
        Get sections database URL.
        Defaults to sections_db service if not configured.
        """
        if self.SECTIONS_DB_HOST and self.SECTIONS_DB_USER and self.SECTIONS_DB_PASSWORD and self.SECTIONS_DB_NAME:
            port = self.SECTIONS_DB_PORT or 5432
            return (
                f"postgresql://{self.SECTIONS_DB_USER}:"
                f"{self.SECTIONS_DB_PASSWORD}@{self.SECTIONS_DB_HOST}:"
                f"{port}/{self.SECTIONS_DB_NAME}"
            )
        # Default to Docker Compose sections_db service
        return "postgresql://sections_user:sections_password@sections_db:5432/sections_db"

    # Authentication mode: True = SAAS (Cognito), False = Standalone (local)
    SAAS_MODE: bool = True

    # Cognito settings (required when SAAS_MODE=True)
    COGNITO_AWS_REGION: str | None = None
    COGNITO_USER_POOL_ID: str | None = None
    COGNITO_APP_CLIENT_ID: str | None = None

    # Standalone auth settings (required when SAAS_MODE=False)
    JWT_SECRET_KEY: str | None = None
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Self-Hosted Configuration
    # DynamoDB Local endpoint (leave empty for AWS DynamoDB)
    DYNAMODB_LOCAL_ENDPOINT: str | None = None

    # MinIO S3-compatible storage (leave empty for AWS S3)
    S3_LOCAL_ENDPOINT: str | None = None
    S3_ACCESS_KEY: str | None = None
    S3_SECRET_KEY: str | None = None

    # Routes table name (used by router service)
    ROUTES_TABLE_NAME: str | None = None

    # Encryption Configuration
    # Main encryption key for secrets in DynamoDB
    ENCRYPTION_KEY: str | None = None
    # Migration keys (for copying data from AWS to self-hosted)
    AWS_ENCRYPTION_KEY: str | None = None
    LOCAL_ENCRYPTION_KEY: str | None = None

    AWS_REGION: str
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_ACCOUNT_ID: str

    AWS_ACM_CERT_ARN: str
    AWS_LAMBDA_EXECUTION_ROLE: str
    AWS_LAMBDA_LAYER_ARN: str

    AWS_S3_PUBLIC_BUCKET_NAME: str = "polysynergy-public-dev"
    AWS_S3_PRIVATE_BUCKET_NAME: str = "polysynergy-private-dev"
    AWS_S3_LAMBDA_BUCKET_NAME: str = "polysynergy-lambdas"

    EMAIL_HOST_USER: str
    EMAIL_HOST_PASSWORD: str
    EMAIL_FROM: EmailStr = "no-reply@polysynergy.com"

    PORTAL_URL: str
    ROUTER_URL: str

    DEBUG: bool = False

    EXECUTE_NODE_SETUP_LOCAL: bool = False

    DYNAMODB_ENV_VARS_TABLE: str

    OPENAI_API_KEY: str

    NODE_PACKAGES: str = "polysynergy_nodes,polysynergy_nodes_agno"

    # Sentry error tracking
    SENTRY_DSN: str | None = None
    SENTRY_ENVIRONMENT: str = "development"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8"
    }


settings = Settings()