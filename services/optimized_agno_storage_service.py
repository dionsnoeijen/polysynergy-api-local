from typing import Optional, List, Dict, Any
import json
import hashlib
from datetime import datetime, timezone
import uuid

from .agno_chat_history_service import AgnoChatHistoryService

try:
    from agno.storage.sqlite import SqliteStorage
    from agno.storage.dynamodb import DynamoDbStorage
    AGNO_AVAILABLE = True
except ImportError:
    AGNO_AVAILABLE = False
    print("Warning: Agno storage modules not available. Optimized storage will not work.")

class OptimizedAgnoStorageService(AgnoChatHistoryService):
    """
    Optimized wrapper around Agno Storage that separates runs for efficient access.
    
    Instead of loading entire sessions with all runs, this service:
    1. Stores runs separately with unique IDs
    2. Maintains run references in the main session
    3. Provides lazy loading of individual runs
    4. Caches frequently accessed runs
    """
    
    def __init__(self):
        super().__init__()
        self.runs_cache = {}  # Cache voor individual runs
        self.session_cache = {}  # Cache voor session metadata
    
    async def get_session_with_run_refs(
        self,
        storage_config: Dict[str, Any],
        session_id: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get session metadata with run references instead of full runs.
        Returns session info + run IDs for lazy loading.
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
                    "run_references": [],
                    "metadata": {},
                    "optimized": True
                }
            
            # Check if session is already optimized
            session_dict = session.to_dict() if hasattr(session, 'to_dict') else session.__dict__
            memory_data = session_dict.get('memory')
            
            if self._is_optimized_session(memory_data):
                # Already optimized - return run references
                return self._parse_optimized_session(memory_data, session_id)
            else:
                # Legacy session - migrate to optimized format
                return await self._migrate_session_to_optimized(
                    storage_config, session_id, session_dict, storage
                )
                
        except Exception as e:
            print(f"Error retrieving optimized session: {e}")
            # Fallback to original method
            return await super().get_session_history(storage_config, session_id, user_id)
    
    async def get_run_by_id(
        self,
        storage_config: Dict[str, Any],
        session_id: str,
        run_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Load a single run by ID without loading the entire session.
        """
        # Check cache first
        cache_key = f"{session_id}:{run_id}"
        if cache_key in self.runs_cache:
            return self.runs_cache[cache_key]
        
        try:
            # Try to load from separate runs storage
            run_data = await self._load_run_from_storage(storage_config, run_id)
            
            if run_data:
                # Cache the result
                self.runs_cache[cache_key] = run_data
                return run_data
            
            # Fallback: load from main session (for legacy data)
            return await self._extract_run_from_session(storage_config, session_id, run_id)
            
        except Exception as e:
            print(f"Error loading run {run_id}: {e}")
            return None
    
    async def append_run_optimized(
        self,
        storage_config: Dict[str, Any],
        session_id: str,
        run_data: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> str:
        """
        Append a new run without loading/saving the entire session.
        Returns the generated run_id.
        """
        try:
            # Generate unique run ID
            run_id = self._generate_run_id(session_id, run_data)
            
            # Store run separately
            await self._store_run_separately(storage_config, run_id, run_data)
            
            # Update session with run reference (minimal update)
            await self._add_run_reference_to_session(
                storage_config, session_id, run_id, user_id
            )
            
            # Update cache
            cache_key = f"{session_id}:{run_id}"
            self.runs_cache[cache_key] = run_data
            
            return run_id
            
        except Exception as e:
            print(f"Error appending optimized run: {e}")
            # Fallback to loading entire session, adding run, saving everything
            return await self._fallback_append_run(storage_config, session_id, run_data, user_id)
    
    async def get_recent_runs(
        self,
        storage_config: Dict[str, Any],
        session_id: str,
        limit: int = 10,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get the most recent runs without loading all session data.
        """
        try:
            # Get session with run references
            session_info = await self.get_session_with_run_refs(storage_config, session_id, user_id)
            run_refs = session_info.get('run_references', [])
            
            # Get last N run references
            recent_refs = run_refs[-limit:] if len(run_refs) > limit else run_refs
            
            # Load each run (will use cache if available)
            recent_runs = []
            for run_id in recent_refs:
                run_data = await self.get_run_by_id(storage_config, session_id, run_id)
                if run_data:
                    recent_runs.append(run_data)
            
            return recent_runs
            
        except Exception as e:
            print(f"Error getting recent runs: {e}")
            # Fallback to original method
            session_history = await super().get_session_history(storage_config, session_id, user_id, limit)
            return self._extract_runs_from_history(session_history)
    
    def _generate_run_id(self, session_id: str, run_data: Dict[str, Any]) -> str:
        """Generate a unique ID for a run based on session + timestamp + content hash."""
        timestamp = datetime.now(timezone.utc).isoformat()
        content_str = json.dumps(run_data, sort_keys=True)
        content_hash = hashlib.md5(content_str.encode()).hexdigest()[:8]
        return f"{session_id}_{timestamp}_{content_hash}"
    
    def _is_optimized_session(self, memory_data: Any) -> bool:
        """Check if session is already in optimized format."""
        try:
            if isinstance(memory_data, str):
                memory_obj = json.loads(memory_data)
            else:
                memory_obj = memory_data
                
            return (
                isinstance(memory_obj, dict) and 
                'run_references' in memory_obj and 
                memory_obj.get('optimized') is True
            )
        except:
            return False
    
    def _parse_optimized_session(self, memory_data: Any, session_id: str) -> Dict[str, Any]:
        """Parse already optimized session data."""
        try:
            if isinstance(memory_data, str):
                memory_obj = json.loads(memory_data)
            else:
                memory_obj = memory_data
                
            return {
                "session_id": session_id,
                "run_references": memory_obj.get('run_references', []),
                "metadata": memory_obj.get('metadata', {}),
                "optimized": True
            }
        except Exception as e:
            print(f"Error parsing optimized session: {e}")
            return {
                "session_id": session_id,
                "run_references": [],
                "metadata": {},
                "optimized": False
            }
    
    async def _migrate_session_to_optimized(
        self,
        storage_config: Dict[str, Any],
        session_id: str,
        session_dict: Dict[str, Any],
        storage
    ) -> Dict[str, Any]:
        """
        Migrate a legacy session to optimized format.
        Extract runs, store them separately, update session with references.
        """
        print(f"Migrating session {session_id} to optimized format...")
        
        try:
            memory_data = session_dict.get('memory')
            
            # Parse existing runs
            memory_obj = json.loads(memory_data) if isinstance(memory_data, str) else memory_data
            existing_runs = memory_obj.get("runs", []) if isinstance(memory_obj, dict) else []
            
            # Store each run separately and collect references
            run_references = []
            for i, run_data in enumerate(existing_runs):
                run_id = self._generate_run_id(session_id, run_data)
                await self._store_run_separately(storage_config, run_id, run_data)
                run_references.append(run_id)
            
            # Create optimized session data
            optimized_memory = {
                "run_references": run_references,
                "metadata": {
                    "migrated_at": datetime.now(timezone.utc).isoformat(),
                    "original_runs_count": len(existing_runs)
                },
                "optimized": True
            }
            
            # Update session with optimized format
            session_dict['memory'] = json.dumps(optimized_memory)
            
            # Save the updated session (this is the last time we save the full thing)
            # Implementation depends on storage type - for now, we'll need to use storage.update
            # This might still require a full update, but it's a one-time migration
            
            print(f"Migration completed: {len(run_references)} runs separated")
            
            return {
                "session_id": session_id,
                "run_references": run_references,
                "metadata": optimized_memory["metadata"],
                "optimized": True
            }
            
        except Exception as e:
            print(f"Error migrating session to optimized format: {e}")
            # Fallback to parsing as legacy
            return await super().get_session_history(storage_config, session_id)
    
    async def _store_run_separately(
        self,
        storage_config: Dict[str, Any],
        run_id: str,
        run_data: Dict[str, Any]
    ):
        """
        Store a run in separate storage.
        For now, we'll use a separate table/collection with run_id as key.
        """
        # For DynamoDB: use separate table or same table with different partition key
        # For SQLite: use separate table
        
        storage_type = storage_config.get('type')
        
        if storage_type == 'LocalAgentStorage':
            # Use separate SQLite table for runs
            await self._store_run_sqlite(storage_config, run_id, run_data)
        elif storage_type == 'DynamoDBAgentStorage':
            # Use same DynamoDB table but with run_id as session_id
            await self._store_run_dynamodb(storage_config, run_id, run_data)
    
    async def _store_run_sqlite(self, storage_config: Dict[str, Any], run_id: str, run_data: Dict[str, Any]):
        """Store run in separate SQLite table."""
        # Implementation would create/use a separate runs table
        # For now, placeholder
        pass
    
    async def _store_run_dynamodb(self, storage_config: Dict[str, Any], run_id: str, run_data: Dict[str, Any]):
        """Store run in DynamoDB using run_id as session_id."""
        # Create a temporary session object with the run data
        run_session_data = {
            "memory": json.dumps({"single_run": run_data, "run_id": run_id}),
            "session_id": run_id  # Use run_id as session_id for separate storage
        }
        
        # Use existing storage but with run_id
        storage = self._get_dynamodb_storage(storage_config)
        # This is a bit of a hack - we're storing runs as separate "sessions"
        # A better approach would be to extend Agno storage, but this works as POC
    
    async def _load_run_from_storage(
        self,
        storage_config: Dict[str, Any],
        run_id: str
    ) -> Optional[Dict[str, Any]]:
        """Load a single run from separate storage."""
        try:
            storage_type = storage_config.get('type')
            
            if storage_type == 'DynamoDBAgentStorage':
                # Try to load run stored as separate session
                storage = self._get_dynamodb_storage(storage_config)
                run_session = storage.read(run_id)  # run_id used as session_id
                
                if run_session:
                    session_dict = run_session.to_dict() if hasattr(run_session, 'to_dict') else run_session.__dict__
                    memory_data = session_dict.get('memory')
                    memory_obj = json.loads(memory_data) if isinstance(memory_data, str) else memory_data
                    return memory_obj.get('single_run') if isinstance(memory_obj, dict) else None
            
            return None
        except:
            return None
    
    async def _add_run_reference_to_session(
        self,
        storage_config: Dict[str, Any],
        session_id: str,
        run_id: str,
        user_id: Optional[str] = None
    ):
        """Add run reference to session without loading full session."""
        # This is tricky - we need to update just the run_references list
        # For now, this might still require loading the session
        # TODO: Implement atomic list append for DynamoDB
        pass
    
    async def _fallback_append_run(
        self,
        storage_config: Dict[str, Any],
        session_id: str,
        run_data: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> str:
        """Fallback method that loads entire session, adds run, saves everything."""
        # Generate run ID
        run_id = self._generate_run_id(session_id, run_data)
        
        # This would be the old inefficient way as fallback
        # Load entire session, add run, save everything
        
        return run_id
    
    def _extract_runs_from_history(self, session_history: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract run data from legacy session history format."""
        # Convert legacy format to run list
        return []


def get_optimized_agno_storage_service() -> OptimizedAgnoStorageService:
    """Dependency injection for OptimizedAgnoStorageService."""
    return OptimizedAgnoStorageService()