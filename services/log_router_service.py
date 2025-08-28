from typing import List, Dict, Optional
from core.settings import settings
from .lambda_log_service import LambdaLogService
from .local_log_service import LocalLogService


class LogRouterService:
    """Service that routes log requests to the appropriate log source based on execution mode."""
    
    @staticmethod
    def get_logs(version_id: str, after: Optional[int] = None) -> List[Dict]:
        """
        Get logs for a version, automatically routing to the correct source.
        
        Args:
            version_id: The version ID to get logs for
            after: Optional timestamp to filter logs after this time
            
        Returns:
            List of log entries in the same format regardless of source
        """
        if settings.EXECUTE_NODE_SETUP_LOCAL:
            # Local execution - get logs from LocalLogService
            logs = LocalLogService.get_logs(version_id, after)
            
            # If no logs found locally, it might be because this version
            # hasn't been executed locally yet, so return empty list
            return logs
        else:
            # Remote execution - get logs from CloudWatch via LambdaLogService
            return LambdaLogService.get_lambda_logs(version_id, after)
    
    @staticmethod
    def clear_logs(version_id: str):
        """Clear logs for a version (only applicable for local logs)."""
        if settings.EXECUTE_NODE_SETUP_LOCAL:
            LocalLogService.clear_logs(version_id)
        # For CloudWatch logs, we don't provide clear functionality
        # as they are managed by AWS retention policies
    
    @staticmethod
    def get_log_source() -> str:
        """Get a string indicating which log source is currently active."""
        return "local" if settings.EXECUTE_NODE_SETUP_LOCAL else "cloudwatch"
    
    @staticmethod
    def get_debug_info(version_id: str) -> Dict:
        """Get debug information about the log system (useful for troubleshooting)."""
        info = {
            "log_source": LogRouterService.get_log_source(),
            "execute_local": settings.EXECUTE_NODE_SETUP_LOCAL,
            "version_id": version_id
        }
        
        if settings.EXECUTE_NODE_SETUP_LOCAL:
            info["local_log_stats"] = LocalLogService.get_stats()
        
        return info