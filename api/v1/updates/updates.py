from fastapi import APIRouter, HTTPException, Path
from pathlib import Path as PathLib
import os

router = APIRouter()

# Determine updates path based on environment
# In Docker: /updates (mounted volume)
# Locally: ../updates relative to api-local
if os.path.exists("/updates"):
    UPDATES_PATH = PathLib("/updates")
else:
    # Local development - go up from api-local to orchestrator root
    UPDATES_PATH = PathLib(__file__).parent.parent.parent.parent.parent / "updates"

UPDATE_TYPES = {
    "changelog": "changelog.md",
    "roadmap": "roadmap.md",
    "known-issues": "known-issues.md"
}

@router.get("/debug/info")
async def debug_info():
    """Debug endpoint to check paths."""
    import os
    return {
        "updates_path": str(UPDATES_PATH),
        "updates_path_exists": UPDATES_PATH.exists(),
        "updates_path_is_dir": UPDATES_PATH.is_dir() if UPDATES_PATH.exists() else False,
        "files_in_updates": list(UPDATES_PATH.glob("*")) if UPDATES_PATH.exists() else [],
        "current_working_directory": os.getcwd(),
        "file_location": str(PathLib(__file__).parent)
    }

@router.get("/{update_type}")
async def get_update(
    update_type: str = Path(..., description="Type of update (changelog, roadmap, known-issues)")
):
    """Get update content (changelog, roadmap, or known-issues)."""
    try:
        if update_type not in UPDATE_TYPES:
            raise HTTPException(
                status_code=404,
                detail=f"Update type '{update_type}' not found. Valid types: {', '.join(UPDATE_TYPES.keys())}"
            )

        filename = UPDATE_TYPES[update_type]
        file_path = UPDATES_PATH / filename

        if not file_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Update file '{filename}' not found"
            )

        # Read the markdown content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        return {
            "type": update_type,
            "content": content,
            "filename": filename
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading update: {str(e)}")
