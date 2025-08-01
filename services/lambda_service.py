import json
import boto3
import logging
from core.settings import settings
from botocore.exceptions import ClientError
from botocore.config import Config

logger = logging.getLogger(__name__)

class LambdaService:
    def __init__(self):
        self._lambda_client = boto3.client(
            'lambda',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
            config=Config(
                read_timeout=910,
                connect_timeout=5,
                retries={
                    'max_attempts': 1,
                    'mode': 'standard'
                }
            )
        )
        self._ecr_client = boto3.client(
            'ecr',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        self._s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        self.latest_image_uri = '754508895309.dkr.ecr.eu-central-1.amazonaws.com/polysynergy/polysynergy-lambda:latest'

    def get_function(self, function_name: str):
        try:
            return self._lambda_client.get_function(FunctionName=function_name)
        except self._lambda_client.exceptions.ResourceNotFoundException:
            return None

    def get_function_arn(self, function_name: str) -> str | None:
        function = self.get_function(function_name)
        if function:
            return function['Configuration']['FunctionArn']
        return None

    def get_function_image_uri(self, function_name: str) -> str | None:
        """Get the image URI of a Lambda function."""
        function = self.get_function(function_name)

        if function:
            return (function.get('Configuration', {}).get('ImageUri') or
                    function.get('Code', {}).get('ResolvedImageUri') or
                    function.get('Code', {}).get('ImageUri'))
        return None

    def get_latest_image_digest(self) -> str | None:
        """Get the resolved image digest for the latest image tag."""
        try:
            response = self._ecr_client.describe_images(
                repositoryName='polysynergy/polysynergy-lambda',
                imageIds=[{'imageTag': 'latest'}]
            )
            if response['imageDetails']:
                return response['imageDetails'][0]['imageDigest']
            return None
        except Exception as e:
            logger.error(f"Error getting latest image digest: {str(e)}")
            return None

    def update_function_configuration(self, function_name: str, tenant_id: str, project_id: str) -> None:
        self._lambda_client.update_function_configuration(
            FunctionName=function_name,
            Environment={
                'Variables': {
                    'PROJECT_ID': str(project_id),
                    'TENANT_ID': str(tenant_id),
                    'AWS_S3_PUBLIC_BUCKET_NAME': settings.AWS_S3_PUBLIC_BUCKET_NAME,
                    'AWS_S3_PRIVATE_BUCKET_NAME': settings.AWS_S3_PRIVATE_BUCKET_NAME,
                    'REDIS_URL': settings.REDIS_URL,
                }
            }
        )

    def update_function_image(self, function_name: str, tenant_id: str, project_id: str) -> str:
        """
        Update a Lambda function to use the latest image and environment variables.
        Returns the function ARN.
        """
        try:
            self._lambda_client.update_function_code(
                FunctionName=function_name,
                ImageUri=self.latest_image_uri,
                Publish=True
            )

            self.update_function_configuration(function_name, tenant_id, project_id)

            return self.get_function_arn(function_name)

        except Exception as e:
            logger.error(f"Error updating function image for {function_name}: {str(e)}")
            raise

    def upload_code_to_s3(self, bucket_name: str, s3_key: str, code: str) -> None:
        """Upload code to S3."""
        try:
            self._s3_client.put_object(
                Bucket=bucket_name,
                Key=s3_key,
                Body=code.encode('utf-8')
            )
        except Exception as e:
            logger.error(f"Error uploading code to S3 {bucket_name}/{s3_key}: {str(e)}")
            raise

    def create_or_update_lambda(self, function_name: str, code: str, tenant_id: str, project_id: str) -> str:
        try:
            # First, try to get the existing function
            existing_function = self.get_function(function_name)

            if existing_function:
                # Update existing function
                self.update_function_image(function_name, tenant_id, project_id)
            else:
                # Create new function
                self._lambda_client.create_function(
                    FunctionName=function_name,
                    PackageType='Image',
                    Code={'ImageUri': self.latest_image_uri},
                    Role=settings.AWS_LAMBDA_EXECUTION_ROLE,
                    Timeout=900,
                    MemorySize=1024,
                    Environment={
                        'Variables': {
                            'PROJECT_ID': str(project_id),
                            'TENANT_ID': str(tenant_id),
                            'AWS_S3_PUBLIC_BUCKET_NAME': settings.AWS_S3_PUBLIC_BUCKET_NAME,
                            'AWS_S3_PRIVATE_BUCKET_NAME': settings.AWS_S3_PRIVATE_BUCKET_NAME,
                            "REDIS_URL": settings.REDIS_URL,
                        }
                    }
                )

            s3_key = f"{tenant_id}/{project_id}/{function_name}.py"
            self.upload_code_to_s3(settings.AWS_S3_LAMBDA_BUCKET_NAME, s3_key, code)

            return self.get_function_arn(function_name)
        except Exception as e:
            logger.error(f"Error creating/updating Lambda {function_name}: {str(e)}")
            raise

    def add_api_gateway_permission(self, function_name: str, api_id: str) -> None:
        statement_id = f"apigateway-{api_id}"

        try:
            policy = self._lambda_client.get_policy(FunctionName=function_name)
            policy_doc = json.loads(policy['Policy'])
            for statement in policy_doc.get('Statement', []):
                if statement.get('Sid') == statement_id:
                    logger.debug(f"Permission with StatementId {statement_id} already exists. Skipping.")
                    return  # Al toegevoegd, niks doen
        except self._lambda_client.exceptions.ResourceNotFoundException:
            # Geen policy → mag gewoon verder
            pass

        try:
            self._lambda_client.add_permission(
                FunctionName=function_name,
                StatementId=statement_id,
                Action='lambda:InvokeFunction',
                Principal='apigateway.amazonaws.com',
                SourceArn=f"arn:aws:execute-api:{settings.AWS_REGION}:{settings.AWS_ACCOUNT_ID}:{api_id}/*"
            )
            logger.debug(f"Permission {statement_id} added to function {function_name}.")
        except Exception as e:
            logger.error(f"Error adding API Gateway permission for {function_name}: {str(e)}")
            raise

    def invoke_lambda(self, function_name: str, payload: dict) -> dict:
        logger.debug(f"Invoking Lambda: {function_name} with payload: {payload}")
        try:
            response = self._lambda_client.invoke(
                FunctionName=function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(payload),
            )

            response_payload = json.loads(response['Payload'].read())
            logger.debug(f"Lambda response: {response_payload}")

            return response_payload

        except ClientError as e:
            logger.error(f"Fout bij aanroepen van Lambda {function_name}: {str(e)}")
            raise

    def delete_lambda(self, function_name: str) -> None:
        try:
            logger.debug(f"Deleting Lambda function: {function_name}")
            self._lambda_client.delete_function(FunctionName=function_name)
            logger.info(f"Lambda {function_name} deleted successfully.")
        except self._lambda_client.exceptions.ResourceNotFoundException:
            logger.warning(f"Lambda {function_name} not found during delete. Skipping.")
        except Exception as e:
            logger.error(f"Error deleting Lambda {function_name}: {str(e)}")
            raise

def get_lambda_service():
    return LambdaService()