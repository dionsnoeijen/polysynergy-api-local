from fastapi import APIRouter, HTTPException, Query, Path
from fastapi.responses import FileResponse
from typing import Optional, List
from services.documentation_service import DocumentationService
from pathlib import Path as PathLib

router = APIRouter()

@router.get("/")
async def get_all_documentation():
    """Get all documentation including guides and nodes."""
    try:
        # Use the mounted documentation directory
        documentation_service = DocumentationService("/documentation")
        return documentation_service.get_all_documentation()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading documentation: {str(e)}")

@router.get("/categories")
async def get_categories():
    """Get all documentation categories."""
    try:
        documentation_service = DocumentationService("/documentation")
        return {
            "categories": documentation_service.get_categories()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading categories: {str(e)}")

@router.get("/search")
async def search_documentation(
    q: str = Query(..., description="Search query", min_length=2),
    limit: int = Query(20, description="Maximum number of results", ge=1, le=50)
):
    """Search through all documentation."""
    try:
        documentation_service = DocumentationService("/documentation")
        results = documentation_service.search(q, limit)
        return {
            "query": q,
            "results": results,
            "total": len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching documentation: {str(e)}")

@router.get("/{category}")
async def get_category_documentation(
    category: str = Path(..., description="Documentation category (guides, tutorials, reference)")
):
    """Get all documentation for a specific category."""
    try:
        documentation_service = DocumentationService("/documentation")
        docs = documentation_service.get_documentation_by_category(category)
        if not docs and category not in ["guides", "tutorials", "reference"]:
            raise HTTPException(status_code=404, detail=f"Category '{category}' not found")
        
        return {
            "category": category,
            "documents": docs,
            "total": len(docs)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading category documentation: {str(e)}")

@router.get("/{category}/{doc_id}")
async def get_document(
    category: str = Path(..., description="Documentation category"),
    doc_id: str = Path(..., description="Document ID")
):
    """Get a specific document."""
    try:
        documentation_service = DocumentationService("/documentation")
        doc = documentation_service.get_document(category, doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found in category '{category}'")
        
        return doc
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading document: {str(e)}")

@router.get("/assets/{file_path:path}")
async def get_asset(file_path: str):
    """Serve documentation assets (images, etc.)."""
    try:
        asset_path = PathLib("/documentation/assets") / file_path
        
        # Security: Ensure the path stays within the assets directory
        if not str(asset_path.resolve()).startswith("/documentation/assets"):
            raise HTTPException(status_code=403, detail="Access denied")
        
        if not asset_path.exists():
            raise HTTPException(status_code=404, detail="Asset not found")
        
        return FileResponse(asset_path)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error serving asset: {str(e)}")