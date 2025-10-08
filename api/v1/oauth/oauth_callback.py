from fastapi import APIRouter, HTTPException, Query, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from repositories.node_setup_repository import NodeSetupRepository, get_node_setup_repository
from typing import Optional
import boto3
import os
import json
import time
import logging
import sys

# Add node_runner to path for imports
sys.path.append('/Users/dionsnoeijen/polysynergy/orchestrator/node_runner')

logger = logging.getLogger(__name__)

router = APIRouter()


def resolve_variable(value: str, version_uuid, node_setup_repository) -> str:
    """
    Resolve secret and environment variable placeholders in a value.

    Handles:
    - <secret:keyname> - Resolves from AWS Secrets Manager
    - <environment:keyname> - Resolves from DynamoDB environment variables
    - Plain strings - Returns as-is (1-op-1)

    Returns the resolved value or original if not a placeholder.
    """
    if not isinstance(value, str):
        return value

    # Only resolve if it's exactly the secret placeholder format
    if value.startswith("<secret:") and value.endswith(">"):
        secret_key = value[8:-1]  # Extract key from <secret:keyname>
        logger.info(f"Resolving secret: {secret_key}")

        try:
            # Get project_id from environment or version metadata
            project_id = os.getenv("PROJECT_ID")
            if not project_id:
                # Try to get from node setup version
                version = node_setup_repository.get_or_404(version_uuid)
                project_id = str(version.project_id) if hasattr(version, 'project_id') else None

            if not project_id:
                logger.error("PROJECT_ID not found for secret resolution")
                return value

            # Use SecretsManager to resolve
            from polysynergy_node_runner.services.secrets_manager import get_secrets_manager
            secrets_manager = get_secrets_manager()
            stage = os.getenv("STAGE", "mock")

            secret = secrets_manager.get_secret_by_key(secret_key, project_id, stage)
            if secret and secret.get("value"):
                logger.info(f"Secret {secret_key} resolved successfully")
                return secret["value"]
            else:
                logger.warning(f"Secret {secret_key} not found")
                return value

        except Exception as e:
            logger.error(f"Failed to resolve secret {secret_key}: {e}")
            return value

    # Check for environment variable placeholder
    elif value.startswith("<environment:") and value.endswith(">"):
        env_key = value[13:-1]  # Extract key from <environment:keyname>
        logger.info(f"Resolving environment variable: {env_key}")

        try:
            # Get project_id from environment or version metadata
            project_id = os.getenv("PROJECT_ID")
            if not project_id:
                version = node_setup_repository.get_or_404(version_uuid)
                project_id = str(version.project_id) if hasattr(version, 'project_id') else None

            if not project_id:
                logger.error("PROJECT_ID not found for environment variable resolution")
                return value

            # Use EnvVarManager to resolve
            from polysynergy_node_runner.services.env_var_manager import get_env_var_manager
            env_manager = get_env_var_manager()
            stage = os.getenv("STAGE", "mock")

            env_value = env_manager.get_var(project_id, stage, env_key)
            if env_value:
                logger.info(f"Environment variable {env_key} resolved successfully")
                return env_value
            else:
                logger.warning(f"Environment variable {env_key} not found")
                return value

        except Exception as e:
            logger.error(f"Failed to resolve environment variable {env_key}: {e}")
            return value

    # Not a placeholder, return the original value as-is (1-op-1)
    return value

def get_dynamodb_table():
    """Get DynamoDB table for OAuth state storage"""
    try:
        dynamodb = boto3.resource(
            "dynamodb",
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=os.getenv("AWS_REGION", "eu-central-1"),
        )

        table_name = "OAuthTokens"
        table = dynamodb.Table(table_name)

        # Check if table exists, create if not
        try:
            table.load()  # This will raise an exception if table doesn't exist
            logger.info(f"DynamoDB table {table_name} exists")
        except dynamodb.meta.client.exceptions.ResourceNotFoundException:
            logger.info(f"Creating DynamoDB table {table_name}")
            table = dynamodb.create_table(
                TableName=table_name,
                KeySchema=[
                    {
                        'AttributeName': 'node_id',
                        'KeyType': 'HASH'  # Partition key
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'node_id',
                        'AttributeType': 'S'
                    }
                ],
                BillingMode='PAY_PER_REQUEST'  # On-demand pricing
            )

            # Wait for table to be created
            table.wait_until_exists()
            logger.info(f"DynamoDB table {table_name} created successfully")

        return table

    except Exception as e:
        logger.error(f"Failed to connect to DynamoDB: {e}")
        return None

@router.get("/callback")
async def oauth_callback(
    code: Optional[str] = Query(None, description="Authorization code from OAuth provider"),
    state: Optional[str] = Query(None, description="State parameter for CSRF protection"),
    error: Optional[str] = Query(None, description="Error from OAuth provider"),
    error_description: Optional[str] = Query(None, description="Error description"),
    node_setup_repository: NodeSetupRepository = Depends(get_node_setup_repository),
):
    """
    OAuth 2.0 callback endpoint

    This endpoint receives the authorization code from OAuth providers
    and stores it for the corresponding node to retrieve.
    """

    # Handle error response from OAuth provider
    if error:
        error_msg = f"OAuth authorization failed: {error}"
        if error_description:
            error_msg += f" - {error_description}"

        # Return user-friendly error page
        return HTMLResponse(
            content=f"""
            <html>
                <head>
                    <title>Authorization Failed</title>
                    <style>
                        body {{
                            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            min-height: 100vh;
                            margin: 0;
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        }}
                        .container {{
                            background: white;
                            padding: 2rem;
                            border-radius: 10px;
                            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                            max-width: 500px;
                            text-align: center;
                        }}
                        h1 {{ color: #e53e3e; }}
                        p {{ color: #4a5568; margin: 1rem 0; }}
                        .error {{
                            background: #fff5f5;
                            border: 1px solid #feb2b2;
                            padding: 1rem;
                            border-radius: 5px;
                            color: #c53030;
                        }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>❌ Authorization Failed</h1>
                        <div class="error">{error_msg}</div>
                        <p>You can close this window and try again.</p>
                    </div>
                </body>
            </html>
            """,
            status_code=400
        )

    # Validate required parameters
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    if not state:
        raise HTTPException(status_code=400, detail="Missing state parameter")

    # Parse state to get session_id and node info
    try:
        state_data = json.loads(state)
        session_id = state_data.get("session_id")
        node_id = state_data.get("node_id")
        flow_id = state_data.get("flow_id")
        # Legacy support
        tenant_id = state_data.get("tenant_id")
        redirect_url = state_data.get("redirect_url")
        trigger_node_id = state_data.get("trigger_node_id")
    except (json.JSONDecodeError, AttributeError):
        # Fallback for old format
        node_id = state
        flow_id = None
        session_id = None
        tenant_id = None
        redirect_url = None
        trigger_node_id = None

    # Get OAuth configuration from DynamoDB using session_id (much faster!)
    if session_id:
        table = get_dynamodb_table()
        if table:
            try:
                # Retrieve stored OAuth config
                response = table.get_item(Key={"node_id": f"oauth_config#{session_id}"})
                oauth_config = response.get("Item")

                if oauth_config:
                    logger.info(f"Retrieved OAuth config for session {session_id}")

                    # Extract pre-resolved configuration
                    token_url = oauth_config.get("token_url")
                    client_id = oauth_config.get("client_id")
                    client_secret = oauth_config.get("client_secret")
                    node_id = oauth_config.get("actual_node_id")  # Get the real node_id
                    flow_id = oauth_config.get("flow_id")

                    # Exchange authorization code for tokens
                    import httpx

                    api_base_url = os.getenv("API_BASE_URL", "http://localhost:8090")
                    redirect_uri = f"{api_base_url}/api/v1/oauth/callback"

                    # Debug logging for token exchange
                    logger.info(f"[Token Exchange] URL: {token_url}")
                    logger.info(f"[Token Exchange] client_id: {client_id[:20]}..." if client_id else "No client_id")
                    logger.info(f"[Token Exchange] redirect_uri: {redirect_uri}")
                    logger.info(f"[Token Exchange] code length: {len(code) if code else 0}")

                    token_data = {
                        "grant_type": "authorization_code",
                        "code": code,
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "redirect_uri": redirect_uri,
                    }

                    async with httpx.AsyncClient() as client:
                        response = await client.post(
                            token_url,
                            data=token_data,
                            headers={"Content-Type": "application/x-www-form-urlencoded"},
                            timeout=30.0
                        )

                        logger.info(f"[Token Exchange] Response status: {response.status_code}")
                        logger.info(f"[Token Exchange] Response headers: {dict(response.headers)}")

                        if response.status_code == 200:
                            token_data = response.json()
                            logger.info(f"Successfully exchanged authorization code for tokens")

                            # Store tokens in DynamoDB under the actual node_id
                            token_item = {
                                "node_id": node_id,
                                "access_token": token_data.get("access_token"),
                                "refresh_token": token_data.get("refresh_token"),
                                "token_type": token_data.get("token_type", "Bearer"),
                                "expires_in": token_data.get("expires_in"),
                                "token_timestamp": int(time.time()),
                                "record_type": "oauth_tokens"  # To distinguish from config records
                            }

                            if token_data.get("expires_in"):
                                try:
                                    expires_in = int(token_data["expires_in"])
                                    token_item["token_expires"] = int(time.time()) + expires_in
                                except (ValueError, TypeError) as e:
                                    logger.warning(f"Invalid expires_in value: {token_data.get('expires_in')}, error: {e}")
                                    # Don't set token_expires if expires_in is invalid

                            if flow_id:
                                token_item["flow_id"] = flow_id
                            if tenant_id:
                                token_item["tenant_id"] = tenant_id

                            table.put_item(Item=token_item)
                            logger.info(f"Stored tokens for node {node_id}")

                            # Clean up the temporary OAuth config
                            try:
                                table.delete_item(Key={"node_id": f"oauth_config#{session_id}"})
                                logger.info(f"Cleaned up OAuth config for session {session_id}")
                            except Exception as e:
                                logger.warning(f"Failed to clean up config: {e}")

                        else:
                            logger.error(f"Failed to exchange authorization code: {response.status_code} - {response.text}")
                            raise Exception(f"Token exchange failed: {response.text}")

                else:
                    logger.error("OAuth configuration not found or incomplete")
                    raise Exception("OAuth configuration not found")

            except Exception as e:
                logger.error(f"Failed to exchange authorization code using stored config: {e}")
                # No fallback needed - without session_id we can't do anything

    else:
        logger.error("No session_id in state - cannot process OAuth callback")
        raise HTTPException(status_code=400, detail="Invalid OAuth callback state")

    # Return success page or redirect
    if redirect_url:
        return RedirectResponse(url=redirect_url)

    return HTMLResponse(
        content=f"""
        <html>
            <head>
                <title>Authorization Successful</title>
                <style>
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        min-height: 100vh;
                        margin: 0;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    }}
                    .container {{
                        background: white;
                        padding: 2rem;
                        border-radius: 10px;
                        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                        max-width: 500px;
                        text-align: center;
                    }}
                    h1 {{ color: #48bb78; }}
                    p {{ color: #4a5568; margin: 1rem 0; }}
                    .success {{
                        background: #f0fff4;
                        border: 1px solid #9ae6b4;
                        padding: 1rem;
                        border-radius: 5px;
                        color: #276749;
                    }}
                    .close-hint {{
                        margin-top: 2rem;
                        color: #718096;
                        font-size: 0.9rem;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>✅ Authorization Successful!</h1>
                    <div class="success">
                        Your application has been authorized successfully.
                        The flow will continue automatically.
                    </div>
                    <p class="close-hint">You can now close this window.</p>
                </div>
            </body>
        </html>
        """,
        status_code=200
    )


@router.get("/authorize/{node_setup_version_id}/{node_id}")
async def oauth_authorize(
    node_setup_version_id: str,
    node_id: str,
    node_setup_repository: NodeSetupRepository = Depends(get_node_setup_repository),
):
    """
    Start OAuth authorization flow for a specific node

    This endpoint:
    1. Loads the node setup and finds the OAuth node configuration
    2. Resolves secrets (client_secret) from the execution context
    3. Builds the authorization URL
    4. Redirects user to OAuth provider
    """
    try:
        import uuid

        try:
            version_uuid = uuid.UUID(node_setup_version_id)
            version = node_setup_repository.get_or_404(version_uuid)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid UUID format: {node_setup_version_id}")

        # Extract node configuration from the content JSON
        content = version.content

        if not content:
            raise HTTPException(status_code=400, detail="Node setup version has no content")

        # Find the specific node in the content
        nodes = content.get("nodes", [])
        target_node = None

        # Debug: collect info about all nodes
        all_nodes_debug = []
        oauth_nodes_found = []

        for node in nodes:
            if node.get('id') == node_id:
                target_node = node
                continue

        if not target_node:
            raise HTTPException(status_code=404, detail=f"Node {node_id} not found in flow")

        logger.info(f"Found target node: {target_node.get('type', 'unknown')}")
        logger.info(f"All nodes in flow: {all_nodes_debug}")
        logger.info(f"OAuth nodes found: {oauth_nodes_found}")

        # Debug: Let's see what's actually in node_data
        logger.info(f"Node data keys: {list(target_node.keys())}")
        logger.info(f"Node data content: {target_node}")

        # Extract values from the variables array
        # Each variable is an object with 'handle' and 'value'
        variables = target_node.get("variables", [])

        # Create a mapping of handle -> value for easy access
        variable_map = {}
        for var in variables:
            handle = var.get("handle")
            value = var.get("value")
            if handle:
                variable_map[handle] = value

        # Now extract the OAuth configuration values
        auth_url = variable_map.get("auth_url", "")
        token_url = variable_map.get("token_url", "")
        client_id = variable_map.get("client_id", "")
        client_secret = variable_map.get("client_secret", "")
        scopes = variable_map.get("scopes", [])
        service_name = variable_map.get("service_name", "")

        # Default service name if empty
        if not service_name:
            service_name = "OAuth Service"

        # Resolve secrets and environment variables
        resolved_client_secret = resolve_variable(client_secret, version_uuid, node_setup_repository) if client_secret else ""
        resolved_client_id = resolve_variable(client_id, version_uuid, node_setup_repository) if client_id else ""

        # Build the OAuth authorization URL
        from urllib.parse import urlencode

        # Get the redirect URI for OAuth callback
        api_base_url = os.getenv("API_BASE_URL", "http://localhost:8090")
        redirect_uri = f"{api_base_url}/api/v1/oauth/callback"

        # Generate a unique session ID for this OAuth flow
        import secrets
        session_id = secrets.token_urlsafe(32)

        # Store OAuth configuration in DynamoDB for callback to retrieve
        table = get_dynamodb_table()
        if table:
            oauth_config_item = {
                "node_id": f"oauth_config#{session_id}",  # Use session_id as fake node_id with prefix
                "actual_node_id": node_id,  # Store the real node_id
                "flow_id": node_setup_version_id,
                "client_id": resolved_client_id,
                "client_secret": resolved_client_secret,
                "token_url": token_url,
                "auth_url": auth_url,
                "service_name": service_name,
                "config_timestamp": int(time.time()),
                "config_ttl": int(time.time()) + 900,  # 15 minutes TTL
                "record_type": "oauth_config"  # To distinguish from token records
            }

            table.put_item(Item=oauth_config_item)
            logger.info(f"Stored OAuth config with session_id: {session_id}")

        # Build state parameter with session ID
        state_data = {
            "session_id": session_id,
            "node_id": node_id,
            "flow_id": node_setup_version_id,
        }
        state_json = json.dumps(state_data)

        # Build OAuth parameters
        oauth_params = {
            "response_type": "code",
            "client_id": resolved_client_id,
            "redirect_uri": redirect_uri,
            "state": state_json,
        }

        # Add scopes if provided (not always required)
        if scopes:
            # Scopes can be a list or a single string
            if isinstance(scopes, list):
                scope_string = " ".join(scopes)
            else:
                scope_string = scopes if scopes else ""

            if scope_string:
                oauth_params["scope"] = scope_string

        # Add provider-specific parameters
        # Only add Google parameters for Google OAuth
        if "accounts.google.com" in auth_url.lower():
            oauth_params["access_type"] = "offline"  # Request refresh token
            oauth_params["prompt"] = "consent"  # Force consent screen to get refresh token
        elif "microsoftonline.com" in auth_url.lower() or "microsoft.com" in auth_url.lower():
            # Azure AD specific parameters
            oauth_params["prompt"] = "select_account"  # Let user choose account
            # Check if we need to add resource parameter (for SharePoint etc)
            resource = variable_map.get("resource", "")
            if resource:
                oauth_params["resource"] = resolve_variable(resource, version_uuid, node_setup_repository) if resource else resource

        # Ensure response_type is always present
        if "response_type" not in oauth_params or not oauth_params["response_type"]:
            oauth_params["response_type"] = "code"
            logger.warning("Added missing response_type=code to oauth_params")

        # Debug logging before URL construction
        logger.info(f"[OAuth Debug] Final oauth_params: {oauth_params}")
        logger.info(f"[OAuth Debug] Auth URL: {auth_url}")

        # Build the complete authorization URL
        # Check if auth_url already has parameters (contains '?')
        separator = "&" if "?" in auth_url else "?"
        oauth_url = f"{auth_url}{separator}{urlencode(oauth_params)}"

        logger.info(f"[OAuth Debug] Complete OAuth URL: {oauth_url}")
        logger.info(f"Redirecting to OAuth provider: {auth_url}")
        logger.info(f"With client_id: {resolved_client_id[:20]}..." if resolved_client_id else "No client_id")
        logger.info(f"Redirect URI: {redirect_uri}")

        # Redirect the user to the OAuth provider
        return RedirectResponse(url=oauth_url, status_code=302)

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Failed to start OAuth authorization: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to start OAuth authorization: {str(e)}")


@router.post("/register-callback")
async def register_callback(
    node_id: str,
    flow_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
):
    """
    Register a node for OAuth callback

    This endpoint is called by the OAuth node to register itself
    before initiating the OAuth flow.
    """

    # Generate the callback URL
    base_url = os.getenv("API_BASE_URL", "http://localhost:8000")

    # Create state parameter
    state_data = {
        "node_id": node_id,
        "tenant_id": tenant_id,
    }
    if flow_id:
        state_data["flow_id"] = flow_id

    state = json.dumps(state_data)

    # Store registration in DynamoDB (optional, for tracking)
    table = get_dynamodb_table()
    if table:
        try:
            table.put_item(Item={
                "node_id": node_id,
                "flow_id": flow_id,
                "tenant_id": tenant_id,
                "status": "pending",
                "timestamp": int(time.time()),
                "ttl": int(time.time()) + 3600,  # Expire after 1 hour
            })
        except Exception as e:
            logger.error(f"Failed to register callback: {e}")

    return {
        "callback_url": f"{base_url}/api/v1/oauth/callback",
        "state": state,
    }


@router.get("/check-code/{node_id}")
async def check_authorization_code(
    node_id: str,
):
    """
    Check if an authorization code is available for a node

    This endpoint is polled by the OAuth node to check if the user
    has completed the authorization flow.
    """

    table = get_dynamodb_table()
    if not table:
        raise HTTPException(status_code=503, detail="Storage service unavailable")

    try:
        response = table.get_item(Key={"node_id": node_id})
        item = response.get("Item")

        if not item:
            return {"status": "pending"}

        # Check if auth code is available and not expired
        auth_code = item.get("authorization_code")
        auth_ttl = item.get("auth_code_ttl", 0)

        if auth_code and time.time() < auth_ttl:
            # Clear the auth code from the record (one-time use)
            table.update_item(
                Key={"node_id": node_id},
                UpdateExpression="REMOVE authorization_code, auth_code_timestamp, auth_code_ttl"
            )

            return {
                "status": "completed",
                "authorization_code": auth_code,
            }

        return {"status": "pending"}

    except Exception as e:
        logger.error(f"Failed to check authorization code: {e}")
        raise HTTPException(status_code=500, detail="Failed to check authorization status")