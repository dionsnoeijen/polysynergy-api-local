#!/usr/bin/env python3

import types
import logging
import uuid
import asyncio
from typing import get_origin, get_args

from polysynergy_node_runner.execution_context.connection import Connection
from polysynergy_node_runner.execution_context.connection_context import ConnectionContext
from polysynergy_node_runner.execution_context.context import Context
from polysynergy_node_runner.execution_context.executable_node import ExecutableNode
from polysynergy_node_runner.execution_context.execution_state import ExecutionState
from polysynergy_node_runner.execution_context.flow import Flow
from polysynergy_node_runner.execution_context.flow_state import FlowState
from polysynergy_node_runner.execution_context.utils.connections import get_driving_connections, get_in_connections, \
    get_out_connections
from polysynergy_node_runner.services.active_listeners_service import get_active_listeners_service, \
    ActiveListenersService
from polysynergy_node_runner.services.env_var_manager import get_env_var_manager
from polysynergy_node_runner.services.execution_storage_service import DynamoDbExecutionStorageService, \
    get_execution_storage_service
from polysynergy_node_runner.execution_context.send_flow_event import send_flow_event
from polysynergy_node_runner.services.secrets_manager import get_secrets_manager

logger = logging.getLogger()
logger.setLevel(logging.INFO)

storage: DynamoDbExecutionStorageService = get_execution_storage_service()
active_listeners_service: ActiveListenersService = get_active_listeners_service()

NODE_SETUP_VERSION_ID = "44dc5b41-75f6-4d47-b4ad-0e6dc47686ab"

from datetime import datetime
from openai import OpenAI
from polysynergy_node_runner.setup_context.dock_property import dock_text_area
from polysynergy_node_runner.setup_context.node import Node
from polysynergy_node_runner.setup_context.node_decorator import node
from polysynergy_node_runner.setup_context.node_error import NodeError
from polysynergy_node_runner.setup_context.node_variable_settings import NodeVariableSettings
from polysynergy_node_runner.setup_context.node_variable_settings import NodeVariableSettings, dock_property
from polysynergy_node_runner.setup_context.path_settings import PathSettings
from polysynergy_nodes.image.types import Image
from polysynergy_nodes.qr.services.s3_image_service import S3ImageService
import base64
import os


class GenerateImageV1_0(ExecutableNode):
    # Input prompt
    prompt: str = None

    # Model selection
    model: str = "dall-e-2"

    # Image size
    size: str = "1024x1024"

    # Quality (DALL-E 3 only)
    quality: str = "standard"

    # Style (DALL-E 3 only)
    style: str = "vivid"

    # Outputs
    generated_image: Image = None

    image_url: str = None

    true_path: dict = None

    false_path: dict = None

    def get_openai_client(self) -> OpenAI:
        """Create OpenAI client with API key from environment"""
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")

        return OpenAI(api_key=api_key)

    def validate_parameters(self):
        """Validate model and size combinations"""
        if not self.prompt or self.prompt.strip() == "":
            raise ValueError("Prompt cannot be empty")

        # DALL-E 2 size restrictions
        if self.model == "dall-e-2":
            valid_sizes = ["256x256", "512x512", "1024x1024"]
            if self.size not in valid_sizes:
                raise ValueError(f"DALL-E 2 only supports sizes: {', '.join(valid_sizes)}")

        # DALL-E 3 size restrictions
        if self.model == "dall-e-3":
            valid_sizes = ["1024x1024", "1792x1024", "1024x1792"]
            if self.size not in valid_sizes:
                raise ValueError(f"DALL-E 3 only supports sizes: {', '.join(valid_sizes)}")

    def generate_image_with_openai(self) -> bytes:
        """Generate image using OpenAI API"""
        client = self.get_openai_client()

        # Build parameters based on model
        params = {
            "model": self.model,
            "prompt": self.prompt.strip(),
            "size": self.size,
            "response_format": "b64_json",
            "n": 1
        }

        # Add DALL-E 3 specific parameters
        if self.model == "dall-e-3":
            params["quality"] = self.quality
            params["style"] = self.style

        try:
            response = client.images.generate(**params)
            b64_json = response.data[0].b64_json
            return base64.b64decode(b64_json)

        except Exception as e:
            raise Exception(f"OpenAI image generation failed: {str(e)}")

    def parse_dimensions(self):
        """Parse width and height from size string"""
        width, height = self.size.split('x')
        return int(width), int(height)

    def generate_s3_key(self):
        """Generate S3 key for generated image"""
        tenant_id = os.getenv('TENANT_ID', 'unknown')
        project_id = os.getenv('PROJECT_ID', 'unknown')
        node_id = os.getenv('NODE_ID', self.__class__.__name__.lower())
        execution_id = os.getenv('EXECUTION_ID', 'direct')

        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')[:-3]

        # Create filename with model and size info
        model_short = self.model.replace('-', '')  # dalle2, dalle3
        size_short = self.size.replace('x', 'x')  # Keep size format

        key = f"{tenant_id}/{project_id}/{node_id}/{execution_id}/generated_{model_short}_{size_short}_{timestamp}.png"

        return key

    def execute(self):
        try:
            # Validate parameters
            self.validate_parameters()

            # Generate image
            image_data = self.generate_image_with_openai()
            width, height = self.parse_dimensions()

            # Upload to S3
            s3_service = S3ImageService()
            s3_key = self.generate_s3_key()

            upload_result = s3_service.upload_image(
                image_data=image_data,
                key=s3_key,
                content_type='image/png',
                metadata={
                    'model': self.model,
                    'size': self.size,
                    'quality': self.quality if self.model == "dall-e-3" else "standard",
                    'style': self.style if self.model == "dall-e-3" else "natural",
                    'prompt': self.prompt[:200],  # Truncate long prompts
                    'prompt_length': str(len(self.prompt))
                }
            )

            if not upload_result['success']:
                raise Exception(f"Failed to upload generated image: {upload_result.get('error')}")

            # Prepare output
            self.image_url = upload_result['url']

            self.generated_image = {
                "url": upload_result['url'],
                "mime_type": "image/png",
                "width": width,
                "height": height,
                "size": len(image_data),
                "metadata": {
                    "generation": {
                        "model": self.model,
                        "size": self.size,
                        "quality": self.quality if self.model == "dall-e-3" else "standard",
                        "style": self.style if self.model == "dall-e-3" else "natural",
                        "prompt": self.prompt[:200] + "..." if len(self.prompt) > 200 else self.prompt,
                        "prompt_length": len(self.prompt)
                    },
                    "s3_key": s3_key,
                    "bucket": upload_result.get('bucket')
                }
            }

            self.true_path = self.generated_image

        except Exception as e:
            self.false_path = NodeError.format(e)
            self.generated_image = None
            self.image_url = None


class PlayV1_0(ExecutableNode):
    title: str = None

    info: str = None

    true_path: bool = True

    def execute(self):
        pass


def create_execution_environment(mock=False, run_id: str = "", stage: str = None, sub_stage: str = None):
    storage.clear_previous_execution(NODE_SETUP_VERSION_ID)

    execution_flow = {"run_id": run_id, "nodes_order": [], "connections": [], "execution_data": []}

    state = ExecutionState()
    flow = Flow()

    node_context = Context(
        run_id=run_id,
        node_setup_version_id=NODE_SETUP_VERSION_ID,
        state=state,
        flow=flow,
        storage=storage,
        active_listeners=active_listeners_service,
        secrets_manager=get_secrets_manager(),
        env_var_manager=get_env_var_manager(),
        stage=stage if stage else "mock",
        sub_stage=sub_stage if sub_stage else "mock",
        execution_flow=execution_flow
    )

    connection_context = ConnectionContext(
        state=state
    )

    connections = []

    if mock or 'flow' != 'mock': connections.append(
        Connection(uuid='7c47e68c-e0e2-472b-aef4-ae8f2199468a', source_node_id='d1377c09-bcfc-450a-9493-afebf6db02e3',
                   source_handle='true_path', target_node_id='adde2e77-8eba-42b3-8e68-81f503f0dc5b',
                   target_handle='node', context=connection_context))

    state.connections = connections

    def make_node_adde2e77_8eba_42b3_8e68_81f503f0dc5b_instance(node_context):
        node_adde2e77_8eba_42b3_8e68_81f503f0dc5b = GenerateImageV1_0(id='adde2e77-8eba-42b3-8e68-81f503f0dc5b',
                                                                      handle='excess_fish_violet', stateful=True,
                                                                      context=node_context)

        def factory():
            return make_node_adde2e77_8eba_42b3_8e68_81f503f0dc5b_instance(node_context)

        node_adde2e77_8eba_42b3_8e68_81f503f0dc5b.factory = factory
        node_adde2e77_8eba_42b3_8e68_81f503f0dc5b.path = 'polysynergy_nodes.image.generate_image.GenerateImage'
        node_adde2e77_8eba_42b3_8e68_81f503f0dc5b.flow_state = FlowState.FLOW_STOP
        node_adde2e77_8eba_42b3_8e68_81f503f0dc5b.prompt = 'The amazing image.'
        node_adde2e77_8eba_42b3_8e68_81f503f0dc5b.model = 'dall-e-2'
        node_adde2e77_8eba_42b3_8e68_81f503f0dc5b.size = '1024x1024'
        node_adde2e77_8eba_42b3_8e68_81f503f0dc5b.quality = 'standard'
        node_adde2e77_8eba_42b3_8e68_81f503f0dc5b.style = 'vivid'
        node_adde2e77_8eba_42b3_8e68_81f503f0dc5b.generated_image = '{"url":"https://polysynergy-8865bb5f-3bacf510-media.s3.amazonaws.com/2c14a98b-0f82-47e8-a808-02a160e024bd/77436ed0-28c5-4910-9e31-e824cc1b9662/generateimagev1_0/direct/generated_dalle2_1024x1024_20250809_085216_948.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIA27LB4CRGTLVNLPAW%2F20250809%2Feu-central-1%2Fs3%2Faws4_request&X-Amz-Date=20250809T085218Z&X-Amz-Expires=86400&X-Amz-SignedHeaders=host&X-Amz-Signature=52e42b777c99487ea7c2d3a4056d3449a1a61735135dad7cce4950c8ff7a3502","size":3148011,"width":1024,"height":1024}'
        node_adde2e77_8eba_42b3_8e68_81f503f0dc5b.image_url = 'https://polysynergy-8865bb5f-3bacf510-media.s3.amazonaws.com/2c14a98b-0f82-47e8-a808-02a160e024bd/77436ed0-28c5-4910-9e31-e824cc1b9662/generateimagev1_0/direct/generated_dalle2_1024x1024_20250809_085216_948.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIA27LB4CRGTLVNLPAW%2F20250809%2Feu-central-1%2Fs3%2Faws4_request&X-Amz-Date=20250809T085218Z&X-Amz-Expires=86400&X-Amz-SignedHeaders=host&X-Amz-Signature=52e42b777c99487ea7c2d3a4056d3449a1a61735135dad7cce4950c8ff7a3502'
        node_adde2e77_8eba_42b3_8e68_81f503f0dc5b.true_path = '{"url":"https://polysynergy-8865bb5f-3bacf510-media.s3.amazonaws.com/2c14a98b-0f82-47e8-a808-02a160e024bd/77436ed0-28c5-4910-9e31-e824cc1b9662/generateimagev1_0/direct/generated_dalle2_1024x1024_20250809_085216_948.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIA27LB4CRGTLVNLPAW%2F20250809%2Feu-central-1%2Fs3%2Faws4_request&X-Amz-Date=20250809T085218Z&X-Amz-Expires=86400&X-Amz-SignedHeaders=host&X-Amz-Signature=52e42b777c99487ea7c2d3a4056d3449a1a61735135dad7cce4950c8ff7a3502","size":3148011,"width":1024,"height":1024}'
        node_adde2e77_8eba_42b3_8e68_81f503f0dc5b.false_path = False
        node_adde2e77_8eba_42b3_8e68_81f503f0dc5b.set_driving_connections(
            get_driving_connections(connections, 'adde2e77-8eba-42b3-8e68-81f503f0dc5b'))
        node_adde2e77_8eba_42b3_8e68_81f503f0dc5b.set_in_connections(
            get_in_connections(connections, 'adde2e77-8eba-42b3-8e68-81f503f0dc5b'))
        node_adde2e77_8eba_42b3_8e68_81f503f0dc5b.set_out_connections(
            get_out_connections(connections, 'adde2e77-8eba-42b3-8e68-81f503f0dc5b'))
        return node_adde2e77_8eba_42b3_8e68_81f503f0dc5b

    if mock or 'image' != 'mock': state.register_node(
        make_node_adde2e77_8eba_42b3_8e68_81f503f0dc5b_instance(node_context))

    def make_node_d1377c09_bcfc_450a_9493_afebf6db02e3_instance(node_context):
        node_d1377c09_bcfc_450a_9493_afebf6db02e3 = PlayV1_0(id='d1377c09-bcfc-450a-9493-afebf6db02e3',
                                                             handle='governing_heron_magenta', stateful=True,
                                                             context=node_context)

        def factory():
            return make_node_d1377c09_bcfc_450a_9493_afebf6db02e3_instance(node_context)

        node_d1377c09_bcfc_450a_9493_afebf6db02e3.factory = factory
        node_d1377c09_bcfc_450a_9493_afebf6db02e3.path = 'polysynergy_nodes.play.play.Play'
        node_d1377c09_bcfc_450a_9493_afebf6db02e3.flow_state = FlowState.ENABLED
        node_d1377c09_bcfc_450a_9493_afebf6db02e3.title = None
        node_d1377c09_bcfc_450a_9493_afebf6db02e3.info = None
        node_d1377c09_bcfc_450a_9493_afebf6db02e3.true_path = True
        node_d1377c09_bcfc_450a_9493_afebf6db02e3.set_driving_connections(
            get_driving_connections(connections, 'd1377c09-bcfc-450a-9493-afebf6db02e3'))
        node_d1377c09_bcfc_450a_9493_afebf6db02e3.set_in_connections(
            get_in_connections(connections, 'd1377c09-bcfc-450a-9493-afebf6db02e3'))
        node_d1377c09_bcfc_450a_9493_afebf6db02e3.set_out_connections(
            get_out_connections(connections, 'd1377c09-bcfc-450a-9493-afebf6db02e3'))
        return node_d1377c09_bcfc_450a_9493_afebf6db02e3

    if mock or 'flow' != 'mock': state.register_node(
        make_node_d1377c09_bcfc_450a_9493_afebf6db02e3_instance(node_context))

    return flow, execution_flow, state


async def execute_with_mock_start_node(node_id: str, run_id: str, sub_stage: str):
    flow, execution_flow, state = create_execution_environment(True, run_id=run_id, stage="mock", sub_stage=sub_stage)

    node_id = str(node_id)
    node = state.get_node_by_id(str(node_id))
    if node is None:
        raise ValueError(f"Node ID {node_id} not found.")

    await flow.execute_node(node)
    storage.store_connections_result(
        flow_id=NODE_SETUP_VERSION_ID,
        run_id=run_id,
        connections=[c.to_dict() for c in state.connections],
    )

    return execution_flow


async def execute_with_production_start(event=None, run_id: str = None, stage: str = None):
    flow, execution_flow, state = create_execution_environment(run_id=run_id, stage=stage)

    entry_nodes = [n for n in state.nodes if
                   n.path in ['polysynergy_nodes.route.route.Route', 'polysynergy_nodes.schedule.schedule.Schedule']]

    if not entry_nodes:
        raise ValueError("No valid entry node found (expected 'route' or 'schedule').")

    if event:
        for node in entry_nodes:
            if node.path == 'polysynergy_nodes.route.route.Route':
                node.method = event.get("httpMethod", "GET")
                node.headers = event.get("headers", {})
                node.body = event.get("body", "")
                node.query = event.get("queryStringParameters", {})
                node.cookies = event.get("cookies", {})
                node.route_variables = event.get("pathParameters", {})

    await flow.execute_node(entry_nodes[0])

    storage.store_connections_result(
        flow_id=NODE_SETUP_VERSION_ID,
        run_id=run_id,
        connections=[c.to_dict() for c in state.connections],
    )

    return execution_flow, flow, state


import json


def lambda_handler(event, context):
    stage = event.get("stage", "mock")
    sub_stage = event.get("sub_stage", "mock")
    node_id = event.get("node_id")

    run_id = str(uuid.uuid4())

    try:
        # Is this a mock run triggered from the user interface?
        # in that case, it should start with the node_id that is provided.
        is_ui_mock = stage == "mock" and node_id is not None
        if is_ui_mock:
            print("Running in mock mode with node_id:", node_id)
            has_listener = active_listeners_service.has_listener(NODE_SETUP_VERSION_ID)
            print("Has listener:", has_listener, NODE_SETUP_VERSION_ID)
            if has_listener:
                send_flow_event(
                    NODE_SETUP_VERSION_ID,
                    run_id,
                    None,
                    'run_start'
                )
            execution_flow = asyncio.run(execute_with_mock_start_node(node_id, run_id, sub_stage))
            if has_listener:
                send_flow_event(
                    NODE_SETUP_VERSION_ID,
                    run_id,
                    None,
                    'run_end'
                )
            return {
                "statusCode": 200,
                "body": json.dumps(execution_flow)
            }
        else:
            # This is a production run triggered from the Router.
            # then this could still be a mock run. Imagine testing it with some
            # front-end or other application. We need to check the lambda name itself
            # to determine if that is true. We do want do run a production_start
            # because the flow will take the actual arguments from the application you
            # are testing with...
            is_test_run = False
            if context.function_name.endswith("_mock"):
                is_test_run = True

            has_listener = False
            if is_test_run:
                has_listener = active_listeners_service.has_listener(NODE_SETUP_VERSION_ID)

                if has_listener:
                    send_flow_event(
                        NODE_SETUP_VERSION_ID,
                        run_id,
                        None,
                        'run_start'
                    )

            # Handle async execution properly for production
            try:
                # Check if we're already in an event loop
                asyncio.get_running_loop()
                # If we get here, we're in a running loop, run in a separate thread
                import concurrent.futures

                def run_production_async():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        return loop.run_until_complete(execute_with_production_start(event, run_id, stage))
                    finally:
                        loop.close()

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_production_async)
                    execution_flow, flow, state = future.result()
            except RuntimeError:
                # No running loop, we can use asyncio.run
                execution_flow, flow, state = asyncio.run(execute_with_production_start(event, run_id, stage))
            print('request_id: ', context.aws_request_id)

            for node in execution_flow.get("nodes_order", []):
                print("NODE TYPE:", node.get("type"), "| PATH:", node.get("path", ''))

            last_http_response = next(
                (node for node in reversed(execution_flow.get("nodes_order", []))
                 if node.get("type", "").startswith("HttpResponse")),
                None
            )

            if last_http_response:
                variables = last_http_response.get("variables", {})
                http_response_node = state.get_node_by_id(last_http_response.get("id", ""))
                response = {
                    "statusCode": http_response_node.response.get('status', 100),
                    "headers": http_response_node.response.get('headers', {}),
                    "body": http_response_node.response.get('body', '')
                }

                print("FINAL RESPONSE", last_http_response, variables, response)

                if is_test_run and has_listener:
                    send_flow_event(
                        NODE_SETUP_VERSION_ID,
                        run_id,
                        None,
                        'run_end'
                    )

                return response

            if is_test_run and has_listener:
                send_flow_event(
                    NODE_SETUP_VERSION_ID,
                    run_id,
                    None,
                    'run_end'
                )

            logger.error(
                "Error: No valid HttpResponse node found. Make sure the flow leads to a response. 500 Response given.")
            return {
                "statusCode": 500,
                "body": json.dumps({
                    "error": "No valid HttpResponse node found. Make sure the flow leads to a response.",
                    "request_id": context.aws_request_id
                })
            }

    except ValueError as e:
        return {
            "statusCode": 404,
            "body": json.dumps({"error": str(e)})
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
