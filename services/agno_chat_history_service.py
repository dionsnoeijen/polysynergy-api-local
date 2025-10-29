from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib

from core.settings import settings

# Try to import S3 refresh functionality, fall back gracefully if dependencies missing
try:
    from utils.s3_url_refresh import refresh_s3_urls_in_text
    S3_REFRESH_AVAILABLE = True
    print("DEBUG: S3 refresh functionality loaded successfully")
except ImportError as e:
    print(f"DEBUG: S3 refresh not available: {e}")
    def refresh_s3_urls_in_text(text, expiration=3600):
        print("DEBUG: S3 refresh skipped - boto3 dependencies not available")
        return text
    S3_REFRESH_AVAILABLE = False

class AgnoChatHistoryService:
    """
    Service that retrieves chat history from Agno v2 agno_sessions table.
    Uses AGNO_DB_* settings to connect to the Agno database.
    Extracts runs from JSON column and transforms to chat messages.
    """

    # Configuration flags
    FILTER_SYSTEM_INSTRUCTIONS = True  # Set to False to see RAG context (useful for debugging)
    STRICT_STATUS_CHECK = True  # Strict mode: only accept status='COMPLETED' like before

    def __init__(self):
        self.agno_db_url = self._build_agno_db_url()
        self.engine = create_engine(self.agno_db_url, pool_pre_ping=True)
        self.SessionLocal = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
    
    def _get_table_name(self, project) -> str:
        """Generate the correct table name for the given project with ai schema.""" 
        # Create short hashes from tenant_id and project_id 
        tenant_hash = hashlib.md5(str(project.tenant_id).encode()).hexdigest()[:8]
        project_hash = hashlib.md5(str(project.id).encode()).hexdigest()[:8]
        table_name = f"{tenant_hash}-{project_hash}-agno-sessions"
        # Return with ai schema prefix
        return f"ai.\"{table_name}\""
    
    def _build_agno_db_url(self) -> str:
        """Build PostgreSQL connection URL for Agno database."""
        if not all([settings.AGNO_DB_HOST, settings.AGNO_DB_USER, settings.AGNO_DB_PASSWORD, settings.AGNO_DB_NAME]):
            raise ValueError("AGNO_DB_* settings are required but not all are configured")
        
        port = settings.AGNO_DB_PORT or 5432
        return (
            f"postgresql+psycopg2://{settings.AGNO_DB_USER}:"
            f"{settings.AGNO_DB_PASSWORD}@{settings.AGNO_DB_HOST}:"
            f"{port}/{settings.AGNO_DB_NAME}"
        )

    @contextmanager
    def get_agno_db_session(self):
        """Context manager for Agno database sessions."""
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()

    async def get_session_history(
        self,
        storage_config: Dict[str, Any],  # Keep for API compatibility but ignore
        session_id: str,
        user_id: Optional[str] = None,
        limit: int = 100,
        project=None
    ) -> Dict[str, Any]:
        """
        Retrieve session history from Agno v2 sessions table.
        Queries PostgreSQL agno_sessions table, extracts runs from JSON column.
        Returns prompt->response pairs from runs data.
        """
        try:
            with self.get_agno_db_session() as db:
                # Generate table name from project
                table_name = self._get_table_name(project)
                
                # Simple connection test
                test_query = text("SELECT current_database(), current_user")
                test_result = db.execute(test_query).fetchone()
                print(f"Connected to database: {test_result[0]} as user: {test_result[1]}")

                # First check if session exists
                check_query = text(f"""
                    SELECT runs, created_at, updated_at
                    FROM {table_name}
                    WHERE session_id = :session_id
                """)

                check_result = db.execute(check_query, {"session_id": session_id})
                check_row = check_result.fetchone()

                if not check_row or not check_row[0]:
                    print(f"DEBUG: No session found or empty runs for session_id: {session_id}")
                    return {
                        "session_id": session_id,
                        "messages": [],
                        "total_messages": 0,
                        "session_info": {
                            "created_at": None,
                            "last_activity": None,
                            "participants": []
                        }
                    }

                session_created_at = check_row[1]
                session_updated_at = check_row[2]

                # Try JSONB operations to extract individual runs (more efficient)
                # Fallback to old method if JSONB query fails
                runs_list = []
                try:
                    query = text(f"""
                        SELECT
                            jsonb_array_elements(runs) as run
                        FROM {table_name}
                        WHERE session_id = :session_id
                            AND runs IS NOT NULL
                            AND jsonb_array_length(runs) > 0
                    """)

                    print(f"DEBUG: Executing JSONB query for session: {session_id}")

                    result = db.execute(query, {"session_id": session_id})
                    rows = result.fetchall()

                    print(f"DEBUG: JSONB query returned {len(rows)} run rows")

                    if rows:
                        runs_list = [row[0] for row in rows]  # row[0] is the 'run' jsonb object
                    else:
                        print(f"DEBUG: JSONB query returned no rows, trying fallback method")

                except Exception as e:
                    print(f"DEBUG: JSONB query failed: {e}, falling back to old method")
                    # Fallback: get runs array directly and parse in Python
                    runs_data = check_row[0]
                    if isinstance(runs_data, list):
                        runs_list = runs_data
                    else:
                        runs_list = [runs_data] if runs_data else []
                    print(f"DEBUG: Fallback method extracted {len(runs_list)} runs")

                if not runs_list:
                    print(f"DEBUG: No runs found after extraction (JSONB or fallback)")
                    return {
                        "session_id": session_id,
                        "messages": [],
                        "total_messages": 0,
                        "session_info": {
                            "created_at": session_created_at.isoformat() if session_created_at else None,
                            "last_activity": session_updated_at.isoformat() if session_updated_at else None,
                            "participants": []
                        }
                    }

                # Extract runs from query results
                messages = []

                # Apply limit in Python (after expansion)
                if limit and len(runs_list) > limit:
                    runs_list = runs_list[-limit:]  # Take last N runs
                    print(f"DEBUG: Applied limit {limit}, using last {len(runs_list)} runs")

                # NO SORTING - use exact order from database
                print(f"DEBUG: Processing {len(runs_list)} runs (FILTER_SYSTEM_INSTRUCTIONS={self.FILTER_SYSTEM_INSTRUCTIONS}, STRICT_STATUS_CHECK={self.STRICT_STATUS_CHECK})")

                processed_count = 0
                skipped_count = 0

                for run in runs_list:
                    # Skip incomplete runs - STRICT like before
                    if not isinstance(run, dict) or run.get('status') != 'COMPLETED':
                        continue

                    # Skip if no input or content - BOTH required like before
                    if not run.get('input') or not run.get('content'):
                        continue

                    # DEBUG: Log the run structure to understand where team instructions are stored
                    print(f"DEBUG: Run structure keys: {list(run.keys())}")
                    if 'member_responses' in run:
                        print(f"DEBUG: Found member_responses: {run.get('member_responses')}")
                    if 'input' in run:
                        input_data = run.get('input')
                        print(f"DEBUG: Input structure: {type(input_data)} - {list(input_data.keys()) if isinstance(input_data, dict) else 'not dict'}")

                    timestamp_iso = self._to_iso_timestamp(run.get('created_at'))
                    run_id = run.get('run_id')

                    print(f"DEBUG: Processing run {run_id} with timestamp {timestamp_iso} (raw: {run.get('created_at')})")
                    print(f"DEBUG: Run {run_id} all timestamp fields: created_at={run.get('created_at')}, updated_at={run.get('updated_at')}, started_at={run.get('started_at')}, finished_at={run.get('finished_at')}")

                    # Extract node identification (team_id or agent_id = frontend node.id)
                    node_id = run.get('team_id') or run.get('agent_id')

                    print(f"DEBUG: Run {run_id} - parent_run_id: {run.get('parent_run_id')}, node_id: {node_id}")

                    # Team member metadata
                    parent_run_id = run.get('parent_run_id')
                    is_team_member = bool(parent_run_id)
                    parent_team_id = None
                    member_index = None

                    # If this is a team member response, get team info
                    if is_team_member:
                        # The parent run should have team_id
                        # For now, we'll set parent_team_id to the team_id if available
                        parent_team_id = run.get('team_id')
                        # Extract member index from member metadata if available
                        member_index = run.get('member_index')
                    
                    # Extract user input from messages with role "user" (excluding system/team instructions)
                    input_data = run.get('input')
                    user_content = None

                    # Look for actual user input in the messages array
                    if isinstance(input_data, dict) and 'messages' in input_data:
                        messages_list = input_data['messages']
                        if isinstance(messages_list, list):
                            # Find the first message with role "user" that's not a system instruction
                            for msg in messages_list:
                                if isinstance(msg, dict) and msg.get('role') == 'user':
                                    content = msg.get('content', '')
                                    # Skip if it looks like team instructions
                                    if content and not content.startswith('You are a member of a team of agents'):
                                        user_content = content
                                        break
                    elif isinstance(input_data, dict) and 'input_content' in input_data:
                        user_content = input_data['input_content']
                    elif isinstance(input_data, str):
                        user_content = input_data

                    # Add user message (only if it's real user input and not system instructions)
                    if user_content and user_content.strip():
                        user_text = user_content.strip()

                        # Filter out system instructions - be more aggressive
                        if self._is_system_instruction(user_text):
                            print(f"DEBUG: Skipping system instruction: {user_text[:100]}...")
                            # Skip to next run without adding message
                        else:
                            print(f"DEBUG: Processing user content: {user_text[:100]}...")

                            refreshed_user_content = refresh_s3_urls_in_text(user_text)

                            if refreshed_user_content != user_text:
                                print(f"DEBUG: ✅ S3 URLs refreshed in user message - length changed from {len(user_text)} to {len(refreshed_user_content)}")
                            else:
                                print(f"DEBUG: ❌ No S3 URLs found or refreshed in user message")

                            # Extract images from input_data if present
                            images = None
                            if isinstance(input_data, dict) and 'images' in input_data:
                                images = input_data['images']
                                print(f"DEBUG: Found {len(images) if images else 0} images in user message")

                            messages.append({
                                "sender": "user",
                                "text": refreshed_user_content,
                                "timestamp": timestamp_iso,
                                "run_id": run_id,
                                "node_id": node_id,
                                "is_team_member": is_team_member,
                                "parent_team_id": parent_team_id,
                                "member_index": member_index,
                                "images": images
                            })
                    
                    # Add assistant response
                    content = run.get('content')
                    if content and str(content).strip():
                        # Refresh any expired S3 URLs in the content
                        content_text = str(content).strip()
                        print(f"DEBUG: Processing content: {content_text[:100]}...")
                        refreshed_content = refresh_s3_urls_in_text(content_text)
                        
                        if refreshed_content != content_text:
                            print(f"DEBUG: ✅ S3 URLs refreshed in agent message - length changed from {len(content_text)} to {len(refreshed_content)}")
                        else:
                            print(f"DEBUG: ❌ No S3 URLs found or refreshed in agent message")
                        
                        messages.append({
                            "sender": "agent",
                            "text": refreshed_content,
                            "timestamp": timestamp_iso,
                            "run_id": run_id,
                            "node_id": node_id,
                            "is_team_member": is_team_member,
                            "parent_team_id": parent_team_id,
                            "member_index": member_index
                        })

                # Add index to preserve original order as secondary sort key
                for idx, msg in enumerate(messages):
                    msg['_original_index'] = idx

                # Sort messages by timestamp (primary) and original index (secondary)
                # This ensures chronological order while preserving insertion order for same timestamps
                messages.sort(key=lambda x: (x.get('timestamp', ''), x.get('_original_index', 0)))

                # Remove temporary index field
                for msg in messages:
                    msg.pop('_original_index', None)

                return {
                    "session_id": session_id,
                    "messages": messages,
                    "total_messages": len(messages),
                    "session_info": {
                        "created_at": messages[0]["timestamp"] if messages else None,
                        "last_activity": messages[-1]["timestamp"] if messages else None,
                        "participants": ["user", "agent"] if messages else []
                    }
                }
            
        except Exception as e:
            print(f"Error retrieving session history: {e}")
            import traceback
            traceback.print_exc()
            return {
                "session_id": session_id,
                "messages": [],
                "total_messages": 0,
                "session_info": {
                    "created_at": None,
                    "last_activity": None,
                    "participants": []
                }
            }
    
    async def get_run_detail(self, run_id: str, project=None) -> Dict[str, Any]:
        """
        Get detailed information for a specific run.
        Searches through all sessions to find the run.
        Returns the full run object for transparency.
        """
        try:
            with self.get_agno_db_session() as db:
                # Search for run in all sessions (inefficient but works)
                # Better would be to add run_id index or separate runs table
                table_name = self._get_table_name(project)
                query = text(f"""
                    SELECT session_id, runs
                    FROM {table_name}
                    WHERE runs IS NOT NULL
                """)
                
                result = db.execute(query)
                rows = result.fetchall()
                
                # Search through all sessions for the run
                for row in rows:
                    runs_data = row[1]  # runs column
                    if isinstance(runs_data, list):
                        for run in runs_data:
                            if isinstance(run, dict) and run.get('run_id') == run_id:
                                return run
                
                raise ValueError(f"Run {run_id} not found")
                
        except Exception as e:
            print(f"Error retrieving run detail: {e}")
            raise
    

    def _is_system_instruction(self, content: str) -> bool:
        """
        Detect if content is a system instruction that should be filtered out.
        Returns True if it looks like system/team instructions.
        """
        if not content:
            return False

        content_lower = content.lower().strip()

        # Common system instruction patterns
        system_patterns = [
            'you are a member of a team of agents',
            'you are an ai assistant',
            'you are a helpful assistant',
            'your goal is to complete the following task',
            'your task is to',
            '<task>',
            '<expected_output>',
            '<your_role>',
            '<instructions>',
            'hr informatie verstrekker',
            'jij bent een hr expert',
        ]

        # Check if content starts with or contains system instruction patterns
        for pattern in system_patterns:
            if pattern in content_lower:
                return True

        # Check if it's XML-like instructions
        if '<' in content and '>' in content and any(tag in content_lower for tag in ['role', 'task', 'instructions']):
            return True

        return False

    def _to_iso_timestamp(self, timestamp) -> str:
        """Convert timestamp to ISO string."""
        try:
            if timestamp is None:
                return datetime.now(timezone.utc).isoformat()
            if isinstance(timestamp, (int, float)):
                return datetime.fromtimestamp(float(timestamp), tz=timezone.utc).isoformat()
            if isinstance(timestamp, datetime):
                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=timezone.utc)
                return timestamp.isoformat()
            return str(timestamp)
        except Exception:
            return datetime.now(timezone.utc).isoformat()

    async def list_sessions(
        self,
        storage_config: Dict[str, Any],  # Keep for API compatibility but ignore
        user_id: Optional[str] = None,
        limit: int = 50,
        project=None
    ) -> List[Dict[str, Any]]:
        """
        List available sessions from agno_sessions table.
        """
        try:
            with self.get_agno_db_session() as db:
                # Get sessions with metadata
                table_name = self._get_table_name(project)
                query = text(f"""
                    SELECT 
                        session_id,
                        user_id,
                        created_at,
                        updated_at,
                        runs
                    FROM {table_name}
                    ORDER BY updated_at DESC
                    LIMIT :limit
                """)
                
                result = db.execute(query, {"limit": limit})
                rows = result.fetchall()
                
                sessions = []
                for row in rows:
                    # Count runs in JSON
                    runs_data = row[4] or []  # runs column
                    run_count = len(runs_data) if isinstance(runs_data, list) else (1 if runs_data else 0)
                    
                    sessions.append({
                        "session_id": row[0],  # session_id
                        "user_id": row[1] or user_id,  # user_id
                        "created_at": self._to_iso_timestamp(row[2]),  # created_at
                        "last_activity": self._to_iso_timestamp(row[3]),  # updated_at
                        "message_count": run_count,
                        "session_name": None  # Could be extracted from first message if needed
                    })
                
                return sessions
                
        except Exception as e:
            print(f"Error listing sessions: {e}")
            return []

    async def delete_session(
        self,
        storage_config: Dict[str, Any],  # Keep for API compatibility but ignore
        session_id: str,
        project=None
    ):
        """
        Delete a session from agno_sessions table.
        """
        try:
            with self.get_agno_db_session() as db:
                # Delete session
                table_name = self._get_table_name(project)
                query = text(f'DELETE FROM {table_name} WHERE session_id = :session_id')
                result = db.execute(query, {"session_id": session_id})
                db.commit()
                print(f"Deleted session {session_id}: {result.rowcount} rows affected")
                
        except Exception as e:
            print(f"Error deleting session: {e}")
            raise


def get_agno_chat_history_service() -> AgnoChatHistoryService:
    """Dependency injection for AgnoChatHistoryService."""
    return AgnoChatHistoryService()