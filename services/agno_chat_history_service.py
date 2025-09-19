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
                
                query = text(f"""
                    SELECT runs, created_at, updated_at
                    FROM {table_name}
                    WHERE session_id = :session_id
                """)
                
                result = db.execute(query, {"session_id": session_id})
                row = result.fetchone()
                
                if not row or not row[0]:  # row[0] is 'runs' column
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
                
                # Extract runs from JSON column and transform to chat messages
                runs_data = row[0]  # runs column
                messages = []
                
                # Handle runs as array (like your JSON example)
                if isinstance(runs_data, list):
                    runs_list = runs_data
                else:
                    runs_list = [runs_data] if runs_data else []
                
                # Apply limit to runs
                if limit:
                    runs_list = runs_list[-limit:]  # Get last N runs
                
                for run in runs_list:
                    # Skip incomplete runs
                    if not isinstance(run, dict) or run.get('status') != 'COMPLETED':
                        continue
                    
                    # Skip team member runs (they have parent_run_id)
                    # Member responses should only appear in transparency details
                    if run.get('parent_run_id'):
                        continue
                        
                    # Skip if no input or content
                    if not run.get('input') or not run.get('content'):
                        continue
                        
                    timestamp_iso = self._to_iso_timestamp(run.get('created_at'))
                    run_id = run.get('run_id')
                    
                    # Extract node identification (team_id or agent_id = frontend node.id)
                    node_id = run.get('team_id') or run.get('agent_id')
                    
                    # Extract user input
                    input_data = run.get('input')
                    user_content = None
                    if isinstance(input_data, dict) and 'input_content' in input_data:
                        user_content = input_data['input_content']
                    elif isinstance(input_data, str):
                        user_content = input_data
                        
                    # Add user message
                    if user_content and user_content.strip():
                        # Refresh any expired S3 URLs in user content as well
                        user_text = user_content.strip()
                        print(f"DEBUG: Processing user content: {user_text[:100]}...")
                        refreshed_user_content = refresh_s3_urls_in_text(user_text)
                        
                        if refreshed_user_content != user_text:
                            print(f"DEBUG: ✅ S3 URLs refreshed in user message - length changed from {len(user_text)} to {len(refreshed_user_content)}")
                        else:
                            print(f"DEBUG: ❌ No S3 URLs found or refreshed in user message")
                        
                        messages.append({
                            "sender": "user",
                            "text": refreshed_user_content,
                            "timestamp": timestamp_iso,
                            "run_id": run_id,
                            "node_id": node_id
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
                            "node_id": node_id
                        })
                
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