import json
import boto3
import logging
from core.settings import settings
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class LambdaWarmupService:
    def __init__(self):
        self._events_client = boto3.client(
            'events',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        self._lambda_client = boto3.client(
            'lambda',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )

    def _get_rule_name(self, function_name: str) -> str:
        """Generate warmup rule name for a Lambda function."""
        return f"warmup-{function_name}"

    def warmup_rule_exists(self, function_name: str) -> bool:
        """Check if a warmup rule exists for the given Lambda function."""
        rule_name = self._get_rule_name(function_name)
        try:
            self._events_client.describe_rule(Name=rule_name)
            return True
        except self._events_client.exceptions.ResourceNotFoundException:
            return False
        except Exception as e:
            logger.error(f"Error checking warmup rule existence for {function_name}: {str(e)}")
            return False

    def create_warmup_rule(self, function_name: str) -> None:
        """
        Create an EventBridge rule to keep a Lambda function warm.
        The rule triggers every 5 minutes with a warmup payload.
        """
        rule_name = self._get_rule_name(function_name)

        try:
            # Create or update the EventBridge rule
            self._events_client.put_rule(
                Name=rule_name,
                ScheduleExpression='rate(5 minutes)',
                State='ENABLED',
                Description=f'Warmup rule for Lambda function {function_name}'
            )
            logger.debug(f"Created/updated warmup rule: {rule_name}")

            # Add Lambda permission for EventBridge to invoke it
            statement_id = f"warmup-{function_name}"
            try:
                self._lambda_client.add_permission(
                    FunctionName=function_name,
                    StatementId=statement_id,
                    Action='lambda:InvokeFunction',
                    Principal='events.amazonaws.com',
                    SourceArn=f"arn:aws:events:{settings.AWS_REGION}:{settings.AWS_ACCOUNT_ID}:rule/{rule_name}"
                )
                logger.debug(f"Added EventBridge permission to Lambda {function_name}")
            except self._lambda_client.exceptions.ResourceConflictException:
                # Permission already exists, that's fine
                logger.debug(f"Permission already exists for {function_name}")

            # Add Lambda as target for the rule
            self._events_client.put_targets(
                Rule=rule_name,
                Targets=[
                    {
                        'Id': '1',
                        'Arn': f"arn:aws:lambda:{settings.AWS_REGION}:{settings.AWS_ACCOUNT_ID}:function:{function_name}",
                        'Input': json.dumps({"warmup": True})
                    }
                ]
            )
            logger.info(f"Created warmup rule for Lambda {function_name}")

        except Exception as e:
            logger.error(f"Error creating warmup rule for {function_name}: {str(e)}")
            raise

    def delete_warmup_rule(self, function_name: str) -> None:
        """Delete the warmup rule for a Lambda function."""
        rule_name = self._get_rule_name(function_name)

        try:
            # Remove all targets from the rule first
            try:
                self._events_client.remove_targets(
                    Rule=rule_name,
                    Ids=['1']
                )
                logger.debug(f"Removed targets from warmup rule: {rule_name}")
            except self._events_client.exceptions.ResourceNotFoundException:
                logger.debug(f"Rule {rule_name} not found, nothing to remove")
                return

            # Delete the rule
            self._events_client.delete_rule(Name=rule_name)
            logger.info(f"Deleted warmup rule: {rule_name}")

            # Remove Lambda permission
            statement_id = f"warmup-{function_name}"
            try:
                self._lambda_client.remove_permission(
                    FunctionName=function_name,
                    StatementId=statement_id
                )
                logger.debug(f"Removed EventBridge permission from Lambda {function_name}")
            except self._lambda_client.exceptions.ResourceNotFoundException:
                logger.debug(f"Permission {statement_id} not found for {function_name}")

        except self._events_client.exceptions.ResourceNotFoundException:
            logger.warning(f"Warmup rule {rule_name} not found during delete")
        except Exception as e:
            logger.error(f"Error deleting warmup rule for {function_name}: {str(e)}")
            raise


def get_lambda_warmup_service():
    return LambdaWarmupService()
