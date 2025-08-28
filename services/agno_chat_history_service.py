from typing import Optional, List, Dict, Any
from datetime import datetime

from core.settings import settings

try:
    from agno.storage.sqlite import SqliteStorage
    from agno.storage.dynamodb import DynamoDbStorage
    from agno.storage.base import Storage
    AGNO_AVAILABLE = True
except ImportError:
    AGNO_AVAILABLE = False
    print("Warning: Agno storage modules not available. Chat history will not work.")

class AgnoChatHistoryService:
    """
    Service that uses Agno Storage instances to retrieve chat history.
    Works with existing storage instances without creating new databases.
    """
    
    def __init__(self):
        if not AGNO_AVAILABLE:
            raise ImportError("Agno storage modules are required for chat history functionality")
    
    async def get_session_history(
        self,
        storage_config: Dict[str, Any],
        session_id: str,
        user_id: Optional[str] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Retrieve session history using Agno Storage interfaces.
        Creates a temporary Storage instance to read existing data.
        """
        try:
            storage_type = storage_config.get('type')
            
            if storage_type == 'LocalAgentStorage':
                storage = self._get_sqlite_storage(storage_config)
                session = storage.read(session_id, user_id)
            elif storage_type == 'DynamoDBAgentStorage':
                storage = self._get_dynamodb_storage(storage_config)
                session = storage.read(session_id)
            else:
                raise ValueError(f"Unsupported storage type: {storage_type}")

            if not session:
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
            
            # Convert session to dict to access memory field
            session_dict = session.to_dict() if hasattr(session, 'to_dict') else session.__dict__
            
            # Parse the Agno memory format from the session
            return self._parse_agno_memory(session_dict.get('memory'), session_id, limit)
            
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
    
    def _get_sqlite_storage(self, config: Dict[str, Any]) -> SqliteStorage:
        """Get SQLite storage instance for reading existing data."""
        table_name = config.get('table_name', 'agent_sessions')
        db_file = config.get('db_file', 'tmp/agent_storage.db')
        
        return SqliteStorage(
            table_name=table_name,
            db_file=db_file
        )
    
    def _get_dynamodb_storage(self, config: Dict[str, Any]) -> DynamoDbStorage:
        """Get DynamoDB storage instance for reading existing data."""
        import os
        table_name = config.get('table_name', 'agno_agent_sessions')
        region_name = config.get('region_name', 'eu-central-1')
        
        # Use provided credentials or fall back to environment/default
        aws_access_key_id = settings.AWS_ACCESS_KEY_ID or os.environ.get("AWS_ACCESS_KEY_ID")
        aws_secret_access_key = settings.AWS_SECRET_ACCESS_KEY or os.environ.get("AWS_SECRET_ACCESS_KEY")

        endpoint_url = config.get('endpoint_url') # For LocalStack/custom endpoints
        
        return DynamoDbStorage(
            table_name=table_name,
            region_name=region_name,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            endpoint_url=endpoint_url
        )
    
    def _parse_agno_memory(self, memory_data: Any, session_id: str, limit: int) -> Dict[str, Any]:
        """Parse Agno's Memory object structure."""
        import json
        messages = []
        participants = set()
        
        try:
            # If memory_data is a string, parse it
            if isinstance(memory_data, str):
                memory_obj = json.loads(memory_data)
            else:
                memory_obj = memory_data
            
            # Extract runs from the memory data - this is Agno's standard structure
            runs = memory_obj.get('runs', []) if isinstance(memory_obj, dict) else []
            
            for run in runs:
                # Each run contains an array of messages
                run_messages = run.get('messages', [])
                
                for msg in run_messages:
                    role = msg.get('role', 'unknown')
                    content = msg.get('content', '')
                    created_at = msg.get('created_at', 0)
                    
                    # Skip system messages for chat history
                    if role == 'system':
                        continue
                    
                    # Map Agno roles to our format
                    sender = 'user' if role == 'user' else 'agent'
                    
                    # Convert timestamp to ISO format if it's a number
                    timestamp = datetime.fromtimestamp(created_at).isoformat() if created_at else datetime.now().isoformat()
                    
                    messages.append({
                        "sender": sender,
                        "text": content,
                        "timestamp": timestamp
                    })
                    
                    participants.add(sender)
            
            # Sort messages by timestamp
            messages.sort(key=lambda x: x['timestamp'])
            
            # Apply limit
            if limit and len(messages) > limit:
                messages = messages[-limit:]  # Get the most recent messages
            
        except Exception as e:
            print(f"Error parsing Agno memory data: {e}")
            import traceback
            traceback.print_exc()
        
        return {
            "session_id": session_id,
            "messages": messages,
            "total_messages": len(messages),
            "session_info": {
                "created_at": None,  # Agno Memory doesn't track these
                "last_activity": None,
                "participants": list(participants)
            }
        }
    
    async def list_sessions(
        self,
        storage_config: Dict[str, Any],
        user_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        List available sessions using Agno Storage interface.
        Note: This depends on Agno's storage backend capabilities.
        """
        # Agno Storage doesn't provide a standard list interface
        # This would require custom implementation per storage type
        print("Session listing not yet implemented - Agno Storage doesn't expose session enumeration")
        return []
    
    async def delete_session(
        self,
        storage_config: Dict[str, Any],
        session_id: str
    ):
        """
        Delete a session using Agno Storage interface.
        """
        try:
            storage_type = storage_config.get('type')
            
            if storage_type == 'LocalAgentStorage':
                storage = self._get_sqlite_storage(storage_config)
            elif storage_type == 'DynamoDBAgentStorage':
                storage = self._get_dynamodb_storage(storage_config)
            else:
                raise ValueError(f"Unsupported storage type: {storage_type}")
            
            # Use Agno's Storage interface delete_session method
            storage.delete_session(session_id)
                
        except Exception as e:
            print(f"Error deleting session: {e}")
            raise


def get_agno_chat_history_service() -> AgnoChatHistoryService:
    """Dependency injection for AgnoChatHistoryService."""
    return AgnoChatHistoryService()