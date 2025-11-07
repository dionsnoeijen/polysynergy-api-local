"""
Schedule Executor for local development.
Uses existing mock execution pattern to reuse proven code execution logic.
"""

import logging
import asyncio
import os
import uuid
import traceback
import inspect
import time
from datetime import datetime
from typing import Dict, Any, Optional

from models.schedule import Schedule
from services.local_log_service import LogCapture

logger = logging.getLogger(__name__)


class ScheduleExecutor:
    """
    Executes schedule code directly using the existing mock execution pattern.
    Reuses the proven execute_local_background logic for consistency.
    """

    def __init__(self):
        self.execution_timeout = 300  # 5 minutes max execution time

    async def execute_schedule(self, schedule: Schedule) -> Dict[str, Any]:
        """
        Execute a schedule's Python code using the existing mock execution pattern.

        Args:
            schedule: Schedule object containing execution details

        Returns:
            Dict containing execution result with keys:
            - success: bool
            - output: str
            - error: str (if failed)
            - execution_time: float (seconds)
            - timestamp: str (ISO format)
        """
        start_time = time.time()
        timestamp = datetime.utcnow().isoformat()
        run_id = str(uuid.uuid4())

        try:
            logger.info(f"Executing schedule '{schedule.name}' (ID: {schedule.id}) with run_id: {run_id}")

            # Prepare execution environment similar to mock execution
            self._prepare_execution_environment(schedule)

            # Execute using the same pattern as mock execution
            result = await self._execute_schedule_code(schedule, run_id)

            execution_time = time.time() - start_time

            if result['success']:
                logger.info(f"Schedule '{schedule.name}' completed successfully in {execution_time:.2f}s")
            else:
                logger.error(f"Schedule '{schedule.name}' failed after {execution_time:.2f}s: {result.get('error', 'Unknown error')}")

            return {
                'success': result['success'],
                'output': result.get('output', ''),
                'error': result.get('error', ''),
                'execution_time': execution_time,
                'timestamp': timestamp,
                'run_id': run_id
            }

        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Execution failed: {str(e)}"
            logger.error(f"Schedule '{schedule.name}' execution error: {error_msg}")

            return {
                'success': False,
                'output': '',
                'error': error_msg,
                'execution_time': execution_time,
                'timestamp': timestamp,
                'run_id': run_id
            }

    def _prepare_execution_environment(self, schedule: Schedule):
        """
        Prepare the execution environment similar to mock execution.

        Args:
            schedule: Schedule object
        """
        # Set core environment variables like in mock execution
        os.environ['PROJECT_ID'] = str(schedule.project_id)
        if hasattr(schedule, 'tenant_id') and schedule.tenant_id:
            os.environ['TENANT_ID'] = str(schedule.tenant_id)

        # Add schedule-specific environment variables
        os.environ['SCHEDULE_ID'] = str(schedule.id)
        os.environ['SCHEDULE_NAME'] = schedule.name
        os.environ['EXECUTION_TIME'] = datetime.utcnow().isoformat()
        os.environ['ENVIRONMENT'] = 'local_schedule'

        # Add any schedule-specific environment variables
        if hasattr(schedule, 'environment_variables') and schedule.environment_variables:
            for key, value in schedule.environment_variables.items():
                os.environ[key] = str(value)

    async def _execute_schedule_code(self, schedule: Schedule, run_id: str) -> Dict[str, Any]:
        """
        Execute schedule code using the same pattern as mock execution.

        Args:
            schedule: Schedule object
            run_id: Unique run identifier

        Returns:
            Dict with execution result
        """
        # Use LogCapture like in mock execution for consistent logging
        with LogCapture(f"schedule_{schedule.id}", "execution") as log_capture:
            log_capture.add_custom_log(f"START Schedule execution - RequestId: {run_id} Schedule: {schedule.id}")

            try:
                log_capture.add_custom_log(f"Loading and executing schedule code for '{schedule.name}'...")

                # Create namespace for code execution
                namespace = {}

                # Execute the schedule code (same as mock execution)
                log_capture.add_custom_log("Loading and executing node setup code...")
                exec(schedule.code, namespace)
                log_capture.add_custom_log("Code loaded successfully, looking for lambda_handler...")

                # Call lambda_handler if it exists (like in Lambda execution)
                if 'lambda_handler' in namespace:
                    log_capture.add_custom_log("Found lambda_handler, executing...")

                    # Get the stage from the schedule object, default to 'local'
                    schedule_stage = getattr(schedule, 'stage', 'local')

                    # Create a mock event and context for schedule execution
                    mock_event = {
                        "stage": schedule_stage,
                        "sub_stage": "local",
                        "run_id": run_id,
                        "node_id": None,  # This will trigger production start
                        "execution_type": "schedule"  # Add this to identify schedule executions
                    }

                    mock_context = type('Context', (), {
                        'function_name': f"schedule_{schedule.id}",
                        'aws_request_id': run_id
                    })()

                    # Execute the lambda handler
                    result = namespace['lambda_handler'](mock_event, mock_context)
                    log_capture.add_custom_log(f"Lambda handler executed with result: {result}")
                else:
                    log_capture.add_custom_log("No lambda_handler found - code executed via exec()")

                log_capture.add_custom_log(f"END Schedule execution - RequestId: {run_id}")

                return {
                    'success': True,
                    'output': 'Schedule executed successfully',
                    'error': ''
                }

            except Exception:
                error_details = traceback.format_exc()
                log_capture.add_custom_log(f"[ERROR] Schedule execution failed: {error_details}")

                return {
                    'success': False,
                    'output': '',
                    'error': error_details
                }

    def _find_execution_function(self, namespace: dict, log_capture) -> Optional[callable]:
        """
        Find the main execution function in the schedule code namespace.

        Args:
            namespace: Code execution namespace
            log_capture: Log capture instance for logging

        Returns:
            Callable function or None if not found
        """
        # Common function names for schedule execution
        function_names = [
            'main',
            'execute',
            'run',
            'run_schedule',
            'execute_schedule',
            'schedule_main',
            '__main__'
        ]

        for func_name in function_names:
            fn = namespace.get(func_name)
            if callable(fn):
                log_capture.add_custom_log(f"Found execution function: {func_name}")
                return fn

        # Look for any callable function (excluding built-ins and imports)
        callables = [
            (name, obj) for name, obj in namespace.items()
            if callable(obj) and not name.startswith('_') and hasattr(obj, '__module__')
        ]

        if len(callables) == 1:
            name, fn = callables[0]
            log_capture.add_custom_log(f"Found single callable function: {name}")
            return fn
        elif len(callables) > 1:
            log_capture.add_custom_log(f"Found multiple callable functions: {[name for name, _ in callables]}")

        return None