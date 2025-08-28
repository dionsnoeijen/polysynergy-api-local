import threading
import time
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from collections import defaultdict


class LocalLogService:
    """Service for capturing and storing logs during local node execution."""
    
    # In-memory storage for logs by version_id
    _logs_storage = defaultdict(list)
    _lock = threading.Lock()
    _last_cleanup = time.time()
    
    # Configuration
    MAX_LOGS_PER_VERSION = 1000
    LOG_TTL_SECONDS = 3600  # 1 hour
    CLEANUP_INTERVAL = 300  # 5 minutes
    
    @classmethod
    def add_log(cls, version_id: str, message: str, variant: str = "local"):
        """Add a log entry for a specific version."""
        timestamp = int(time.time() * 1000)  # Milliseconds like CloudWatch
        
        log_entry = {
            "function": f"node_setup_{version_id}_{variant}",
            "timestamp": timestamp,
            "message": message,
            "variant": variant
        }
        
        with cls._lock:
            # Add log entry
            cls._logs_storage[version_id].append(log_entry)
            
            # Keep only the most recent logs to prevent memory issues
            if len(cls._logs_storage[version_id]) > cls.MAX_LOGS_PER_VERSION:
                cls._logs_storage[version_id] = cls._logs_storage[version_id][-cls.MAX_LOGS_PER_VERSION:]
            
            # Periodic cleanup of old logs
            if time.time() - cls._last_cleanup > cls.CLEANUP_INTERVAL:
                cls._cleanup_old_logs()
                cls._last_cleanup = time.time()
    
    @classmethod
    def get_logs(cls, version_id: str, after: Optional[int] = None) -> List[Dict]:
        """Get logs for a specific version, optionally filtered by timestamp."""
        with cls._lock:
            logs = cls._logs_storage.get(version_id, [])
            
            if after is not None:
                # Filter logs after the specified timestamp
                logs = [log for log in logs if log["timestamp"] > after]
            
            # Return sorted by timestamp (same as CloudWatch behavior)
            return sorted(logs, key=lambda x: x["timestamp"])
    
    @classmethod
    def clear_logs(cls, version_id: str):
        """Clear all logs for a specific version."""
        with cls._lock:
            if version_id in cls._logs_storage:
                del cls._logs_storage[version_id]
    
    @classmethod
    def _cleanup_old_logs(cls):
        """Remove logs older than TTL_SECONDS."""
        cutoff_time = int((time.time() - cls.LOG_TTL_SECONDS) * 1000)
        
        for version_id in list(cls._logs_storage.keys()):
            original_count = len(cls._logs_storage[version_id])
            cls._logs_storage[version_id] = [
                log for log in cls._logs_storage[version_id]
                if log["timestamp"] > cutoff_time
            ]
            
            # Remove empty entries
            if not cls._logs_storage[version_id]:
                del cls._logs_storage[version_id]
    
    @classmethod
    def get_stats(cls) -> Dict:
        """Get statistics about stored logs (useful for debugging)."""
        with cls._lock:
            total_logs = sum(len(logs) for logs in cls._logs_storage.values())
            return {
                "versions_with_logs": len(cls._logs_storage),
                "total_logs": total_logs,
                "last_cleanup": cls._last_cleanup,
                "storage_keys": list(cls._logs_storage.keys())
            }


class LogCapture:
    """Context manager to capture stdout/stderr during local execution."""
    
    def __init__(self, version_id: str, variant: str = "local"):
        self.version_id = version_id
        self.variant = variant
        self.original_stdout = None
        self.original_stderr = None
        self.captured_output = []
    
    def __enter__(self):
        import sys
        import io
        
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        
        # Create string buffers
        self.stdout_buffer = io.StringIO()
        self.stderr_buffer = io.StringIO()
        
        # Replace stdout/stderr with our buffers
        sys.stdout = self.stdout_buffer
        sys.stderr = self.stderr_buffer
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        import sys
        
        # Restore original stdout/stderr
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
        
        # Capture the output
        stdout_content = self.stdout_buffer.getvalue()
        stderr_content = self.stderr_buffer.getvalue()
        
        # Process and store the captured logs
        self._process_captured_output(stdout_content, stderr_content)
    
    def _process_captured_output(self, stdout_content: str, stderr_content: str):
        """Process captured stdout/stderr and store as individual log entries."""
        
        # Process stdout
        if stdout_content.strip():
            for line in stdout_content.strip().split('\n'):
                if line.strip():  # Skip empty lines
                    LocalLogService.add_log(self.version_id, line.strip(), self.variant)
        
        # Process stderr (usually errors/warnings)
        if stderr_content.strip():
            for line in stderr_content.strip().split('\n'):
                if line.strip():  # Skip empty lines
                    # Mark stderr content as errors
                    message = f"[ERROR] {line.strip()}" if not line.strip().startswith('[') else line.strip()
                    LocalLogService.add_log(self.version_id, message, self.variant)
    
    def add_custom_log(self, message: str):
        """Add a custom log message during execution."""
        LocalLogService.add_log(self.version_id, message, self.variant)