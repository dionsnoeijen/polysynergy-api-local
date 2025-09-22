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

    REDIS_URL: str | None = None

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+psycopg2://{self.DATABASE_USER}:"
            f"{self.DATABASE_PASSWORD}@{self.DATABASE_HOST}:"
            f"{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )

    COGNITO_AWS_REGION: str
    COGNITO_USER_POOL_ID: str
    COGNITO_APP_CLIENT_ID: str

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