import json
from pathlib import Path
from typing import Dict, List, Optional, Any
import re
from datetime import datetime

class DocumentationService:
    def __init__(self, documentation_path: str = None):
        """Initialize the documentation service.
        
        Args:
            documentation_path: Path to the documentation directory. 
                               If None, will look for documentation/ in the project root.
        """
        if documentation_path is None:
            # Get project root (go up from api-local to orchestrator root)
            project_root = Path(__file__).parent.parent.parent
            self.documentation_path = project_root / "documentation"
        else:
            self.documentation_path = Path(documentation_path)
        
        self.manifest_path = self.documentation_path / "manifest.json"
        self._manifest = None
        self._search_index = None
    
    def _load_manifest(self) -> Dict[str, Any]:
        """Load the documentation manifest."""
        if self._manifest is None:
            if self.manifest_path.exists():
                with open(self.manifest_path, 'r', encoding='utf-8') as f:
                    self._manifest = json.load(f)
            else:
                self._manifest = {"categories": [], "navigation": []}
        return self._manifest
    
    def _parse_frontmatter(self, content: str) -> tuple[Dict[str, Any], str]:
        """Parse frontmatter from markdown content.
        
        Returns:
            Tuple of (metadata_dict, content_without_frontmatter)
        """
        metadata = {}
        
        # Check if content starts with frontmatter
        if content.startswith('---\n'):
            # Find the end of frontmatter
            end_match = re.search(r'\n---\n', content[4:])
            if end_match:
                frontmatter_end = end_match.start() + 4
                frontmatter_content = content[4:frontmatter_end]
                content_without_frontmatter = content[frontmatter_end + 5:]  # +5 for "\n---\n"
                
                # Parse YAML-like frontmatter
                for line in frontmatter_content.strip().split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        key = key.strip()
                        value = value.strip().strip('"\'')
                        
                        # Handle arrays (tags)
                        if value.startswith('[') and value.endswith(']'):
                            # Simple array parsing
                            value = [item.strip().strip('"\'') for item in value[1:-1].split(',') if item.strip()]
                        
                        metadata[key] = value
                
                return metadata, content_without_frontmatter
        
        return metadata, content
    
    def _load_document(self, category: str, filename: str) -> Optional[Dict[str, Any]]:
        """Load a single documentation file."""
        file_path = self.documentation_path / category / filename
        
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            metadata, body_content = self._parse_frontmatter(content)
            
            # Add file information
            stat = file_path.stat()
            
            return {
                "id": filename.replace('.md', ''),
                "filename": filename,
                "category": category,
                "title": metadata.get("title", filename.replace('.md', '').replace('-', ' ').title()),
                "description": metadata.get("description", ""),
                "tags": metadata.get("tags", []),
                "order": metadata.get("order", 999),
                "last_updated": metadata.get("last_updated", datetime.fromtimestamp(stat.st_mtime).isoformat()[:10]),
                "content": content,
                "body": body_content,
                "metadata": metadata,
                "file_size": stat.st_size,
                "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat()
            }
        except Exception as e:
            print(f"Error loading document {file_path}: {e}")
            return None
    
    def get_all_documentation(self) -> Dict[str, Any]:
        """Get all documentation - only guides, tutorials, and reference (no nodes)."""
        manifest = self._load_manifest()
        
        # Get generic documentation only
        guides = {}
        for nav_category in manifest.get("navigation", []):
            category = nav_category["category"]
            guides[category] = []
            
            for item in nav_category["items"]:
                doc = self._load_document(category, item["file"])
                if doc:
                    guides[category].append(doc)
            
            # Sort by order
            guides[category].sort(key=lambda x: x["order"])
        
        return {
            "categories": manifest.get("categories", []),
            "guides": guides,
            "meta": {
                "total_guides": sum(len(category_docs) for category_docs in guides.values()),
                "last_updated": datetime.now().isoformat()
            }
        }
    
    def get_documentation_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get documentation for a specific category."""
        all_docs = self.get_all_documentation()
        return all_docs["guides"].get(category, [])
    
    def get_document(self, category: str, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific document."""
        # Find the filename from manifest
        manifest = self._load_manifest()
        for nav_category in manifest.get("navigation", []):
            if nav_category["category"] == category:
                for item in nav_category["items"]:
                    if item["id"] == doc_id:
                        return self._load_document(category, item["file"])
        
        return None
    
    def _build_search_index(self) -> List[Dict[str, Any]]:
        """Build search index from all documentation."""
        if self._search_index is not None:
            return self._search_index
        
        all_docs = self.get_all_documentation()
        index = []
        
        # Index guides only
        for category, docs in all_docs["guides"].items():
            for doc in docs:
                index.append({
                    "id": doc["id"],
                    "category": category,
                    "type": "guide",
                    "title": doc["title"],
                    "description": doc["description"],
                    "tags": doc["tags"],
                    "content": doc["body"],
                    "url": f"/documentation/{category}/{doc['id']}"
                })
        
        self._search_index = index
        return index
    
    def search(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search through all documentation."""
        if not query or len(query) < 2:
            return []
        
        index = self._build_search_index()
        query_lower = query.lower()
        results = []
        
        for item in index:
            score = 0
            
            # Title match (highest weight)
            if query_lower in item["title"].lower():
                score += 10
                if item["title"].lower().startswith(query_lower):
                    score += 5
            
            # Description match
            if query_lower in item["description"].lower():
                score += 5
            
            # Tags match
            for tag in item["tags"]:
                if query_lower in tag.lower():
                    score += 3
            
            # Content match (lowest weight, but check for multiple matches)
            content_matches = item["content"].lower().count(query_lower)
            if content_matches > 0:
                score += min(content_matches, 5)  # Cap at 5 points for content
            
            if score > 0:
                # Extract snippet around first match
                content_lower = item["content"].lower()
                match_pos = content_lower.find(query_lower)
                if match_pos >= 0:
                    start = max(0, match_pos - 100)
                    end = min(len(item["content"]), match_pos + 100)
                    snippet = item["content"][start:end]
                    if start > 0:
                        snippet = "..." + snippet
                    if end < len(item["content"]):
                        snippet = snippet + "..."
                else:
                    snippet = item["description"][:200] + ("..." if len(item["description"]) > 200 else "")
                
                results.append({
                    **item,
                    "score": score,
                    "snippet": snippet
                })
        
        # Sort by score (descending) and return limited results
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]
    
    def get_categories(self) -> List[Dict[str, Any]]:
        """Get all documentation categories."""
        manifest = self._load_manifest()
        categories = manifest.get("categories", [])
        return sorted(categories, key=lambda x: x.get("order", 999))