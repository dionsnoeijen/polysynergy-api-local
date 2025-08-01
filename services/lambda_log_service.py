import boto3
from fastapi import HTTPException
from typing import List, Dict, Optional
from core.settings import settings

class LambdaLogService:

    @staticmethod
    def get_lambda_logs(version_id: str, after: Optional[int] = None) -> List[Dict]:
        client = boto3.client(
            "logs",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )

        log_variants = ["mock", "published", "config"]
        logs_collected = []

        for variant in log_variants:
            function_name = f"node_setup_{version_id}_{variant}"
            log_group = f"/aws/lambda/{function_name}"

            try:
                streams = client.describe_log_streams(
                    logGroupName=log_group,
                    orderBy="LastEventTime",
                    descending=True,
                    limit=1
                )

                if not streams["logStreams"]:
                    continue

                stream_name = streams["logStreams"][0]["logStreamName"]

                kwargs = {
                    "logGroupName": log_group,
                    "logStreamName": stream_name,
                    "limit": 100,
                    "startFromHead": False,
                }
                if after:
                    kwargs["startTime"] = after + 1

                events = client.get_log_events(**kwargs)

                for event in events["events"]:
                    logs_collected.append({
                        "function": function_name,
                        "timestamp": event["timestamp"],
                        "message": event["message"],
                        "variant": variant
                    })

            except client.exceptions.ResourceNotFoundException:
                continue
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"{function_name}: {str(e)}")

        return sorted(logs_collected, key=lambda x: x["timestamp"])