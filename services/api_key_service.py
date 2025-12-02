from datetime import datetime
import uuid
import os

import boto3
from boto3.dynamodb.conditions import Key

from core.settings import settings
from models import Project
from schemas.api_key import ApiKeyOut, ApiKeyCreateIn, ApiKeyUpdateIn


class ApiKeyService:
    GSI_NAME = "gsi_keyid"

    def __init__(self):
        # Build DynamoDB resource config
        dynamodb_config = {"region_name": settings.AWS_REGION}

        # Use local endpoint if configured (self-hosted mode)
        local_endpoint = settings.DYNAMODB_LOCAL_ENDPOINT
        if local_endpoint:
            dynamodb_config["endpoint_url"] = local_endpoint
            dynamodb_config["aws_access_key_id"] = "dummy"
            dynamodb_config["aws_secret_access_key"] = "dummy"
        else:
            dynamodb_config["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
            dynamodb_config["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY

        self.dynamodb = boto3.resource("dynamodb", **dynamodb_config)
        self.table = self.dynamodb.Table("router_api_keys")

    def _pk(self, project: Project) -> str:
        return f"apikey#{project.tenant_id}#{project.id}"

    def _get_item_by_key_id(self, key_id: str) -> None | dict:
        resp = self.table.query(
            IndexName=self.GSI_NAME,
            KeyConditionExpression=Key("key_id").eq(key_id),
            Limit=1,
        )
        items = resp.get("Items", [])
        return items[0] if items else None

    def list_keys(self, project: Project) -> list[ApiKeyOut]:
        resp = self.table.query(
            KeyConditionExpression=Key("PK").eq(self._pk(project)),
        )
        items = resp.get("Items", [])
        return [ApiKeyOut(**item) for item in items]

    def get_one(self, key_id: str, project: Project) -> ApiKeyOut:
        item = self._get_item_by_key_id(str(key_id))
        if not item or item["project_id"] != str(project.id):
            raise ValueError("API key not found or doesn't belong to this project.")
        return ApiKeyOut(**item)

    def create(self, data: ApiKeyCreateIn, project: Project) -> ApiKeyOut:
        key_id = str(uuid.uuid4())
        item = {
            "PK": self._pk(project),
            "SK": key_id,
            "key_id": key_id,
            "tenant_id": str(project.tenant_id),
            "project_id": str(project.id),
            "label": data.label,
            "key": data.key,
            "type": "api_key",
            "created_at": datetime.utcnow().isoformat(),
        }
        self.table.put_item(Item=item)
        return ApiKeyOut(**item)

    def update(self, key_id: str, data: ApiKeyUpdateIn, project: Project) -> ApiKeyOut:
        item = self._get_item_by_key_id(str(key_id))
        if not item or item["project_id"] != str(project.id):
            raise ValueError("API key not found or doesn't belong to this project.")

        self.table.update_item(
            Key={"PK": item["PK"], "SK": item["SK"]},
            UpdateExpression="SET label = :label",
            ExpressionAttributeValues={":label": data.label},
        )

        item["label"] = data.label  # update local object for return
        return ApiKeyOut(**item)

    def delete(self, key_id: str, project: Project) -> None:
        item = self._get_item_by_key_id(str(key_id))
        if not item or item["project_id"] != str(project.id):
            raise ValueError("API key not found or doesn't belong to this project.")
        self.table.delete_item(Key={"PK": item["PK"], "SK": item["SK"]})

    def assign_keys_to_route(self, route_id: str, api_key_refs: list[str], project: Project) -> dict:
        # Let’s assume you implement this later with DB integration
        return {"route_id": route_id, "api_keys_assigned": api_key_refs}


def get_api_key_service() -> ApiKeyService:
    return ApiKeyService()