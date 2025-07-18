import json

import boto3
import logging
from core.settings import settings
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class ScheduledLambdaService:
    def __init__(self):
        self.events_client = boto3.client(
            'events',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        self.lambda_client = boto3.client(
            'lambda',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )

    def linux_to_aws_cron(self, linux_cron: str) -> str:
        """
        Zet een standaard Linux-cron (5 velden) om naar een AWS EventBridge cron-expressie (6 velden).
        AWS vereist: Minutes Hours Day-of-month Month Day-of-week Year
        Linux heeft: Minutes Hours Day-of-month Month Day-of-week
        """
        parts = linux_cron.strip().split()
        if len(parts) != 5:
            raise ValueError("Linux cron must have exactly 5 fields")

        minute, hour, dom, month, dow = parts

        # AWS vereist een `?` voor één van dag-velden als de ander iets specifieks bevat.
        if dom != '*' and dow != '*':
            # Beide zijn specifiek → we kiezen dag-van-week als leidend en vervangen dag-van-maand met ?
            dom = '?'
        elif dom != '*':
            dow = '?'
        elif dow != '*':
            dom = '?'
        else:
            # beide zijn '*', dan maakt het niet uit → kies dom = ? voor consistentie
            dom = '?'

        # Voeg het jaartal toe als '*' voor "elke jaar"
        return f"cron({minute} {hour} {dom} {month} {dow} *)"

    def create_scheduled_lambda(self, function_name, cron_expression, s3_key: str):
        rule_name = f"{function_name}-schedule"
        logger.debug(f"Creating/updating schedule rule {rule_name} with cron {cron_expression}")

        try:
            response = self.events_client.put_rule(
                Name=rule_name,
                ScheduleExpression=self.linux_to_aws_cron(cron_expression),
                State='ENABLED',
                Description=f"Scheduled execution for {function_name}"
            )
            rule_arn = response['RuleArn']

            self.lambda_client.add_permission(
                FunctionName=function_name,
                StatementId=f"{rule_name}-invoke",
                Action='lambda:InvokeFunction',
                Principal='events.amazonaws.com',
                SourceArn=rule_arn
            )

            self.events_client.put_targets(
                Rule=rule_name,
                Targets=[
                    {
                        'Id': function_name,
                        'Arn': f"arn:aws:lambda:{settings.AWS_REGION}:{settings.AWS_ACCOUNT_ID}:function:{function_name}",
                        'Input': json.dumps({"s3_key": s3_key})
                    }
                ]
            )

            logger.debug(f"Scheduled rule {rule_name} successfully created/updated.")
            return rule_name

        except ClientError as e:
            logger.error(f"Failed to create/update schedule for {function_name}: {str(e)}")
            raise

    def update_scheduled_lambda(self, function_name, cron_expression, s3_key: str, active: bool = True):
        rule_name = f"{function_name}-schedule"
        logger.debug(f"Updating schedule rule {rule_name} with new cron {cron_expression} and active={active}")

        try:
            aws_cron = self.linux_to_aws_cron(cron_expression)

            response = self.events_client.put_rule(
                Name=rule_name,
                ScheduleExpression=aws_cron,
                State='ENABLED' if active else 'DISABLED',
                Description=f"Updated scheduled execution for {function_name}"
            )
            rule_arn = response['RuleArn']

            self.events_client.put_targets(
                Rule=rule_name,
                Targets=[
                    {
                        'Id': function_name,
                        'Arn': f"arn:aws:lambda:{settings.AWS_REGION}:{settings.AWS_ACCOUNT_ID}:function:{function_name}",
                        'Input': json.dumps({
                            "s3_key": s3_key
                        })
                    }
                ]
            )

            logger.debug(
                f"Schedule rule {rule_name} successfully updated with state={'ENABLED' if active else 'DISABLED'}.")
            return rule_name

        except ClientError as e:
            logger.error(f"Failed to update schedule for {function_name}: {str(e)}")
            raise

    def remove_scheduled_lambda(self, function_name):
        rule_name = f"{function_name}-schedule"
        logger.debug(f"Removing schedule rule {rule_name}")

        try:
            self.events_client.remove_targets(Rule=rule_name, Ids=[function_name])
            self.events_client.delete_rule(Name=rule_name)
            self.lambda_client.remove_permission(FunctionName=function_name, StatementId=f"{rule_name}-invoke")
            logger.debug(f"Schedule rule {rule_name} successfully removed.")
        except ClientError as e:
            logger.warning(f"Failed to remove schedule for {function_name}: {str(e)}")

def get_scheduled_lambda_service():
    return ScheduledLambdaService()
