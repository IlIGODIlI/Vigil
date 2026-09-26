from datetime import datetime, timezone
import base64
from typing import Optional, List, Dict
import os
import re

from app.integrations.github.client import GitHubClient, github_client
from app.integrations.repolens.schema import RepositoryContext, FileContext
from app.integrations.repolens.storage import ContextStorage
from app.integrations.repolens.parser import parse_python_file

# Ignore paths that match these patterns to prevent scanning irrelevant/large files
IGNORE_PATTERNS = [
    re.compile(r"^node_modules/"),
    re.compile(r"^\.venv/"),
    re.compile(r"^\.git/"),
    re.compile(r"^dist/"),
    re.compile(r"^build/"),
    re.compile(r"^vendor/"),
]

# Supported extensions
SUPPORTED_EXTENSIONS = {".py"}

class RepositoryContextService:
    def __init__(self, client: Optional[GitHubClient] = None, storage: Optional[ContextStorage] = None):
        self._client = client or github_client
        self._storage = storage or ContextStorage()

    def _should_ignore(self, path: str) -> bool:
        # Check against basic patterns
        for pattern in IGNORE_PATTERNS:
            if pattern.search(path):
                return True
        # Check extension
        ext = os.path.splitext(path)[1]
        if ext not in SUPPORTED_EXTENSIONS:
            return True
        # Simple path traversal protection
        if ".." in path or path.startswith("/"):
            return True
        return False

    async def _fetch_file_content(self, installation_id: int, owner: str, repo: str, path: str, ref: str) -> Optional[str]:
        """Fetch the content of a file from GitHub."""
        try:
            # GitHub API GET /repos/{owner}/{repo}/contents/{path}?ref={ref}
            result = await self._client.request(
                method="GET",
                endpoint=f"/repos/{owner}/{repo}/contents/{path}",
                installation_id=installation_id,
                params={"ref": ref}
            )
            if isinstance(result, dict) and result.get("type") == "file":
                content_b64 = result.get("content", "")
                if content_b64:
                    return base64.b64decode(content_b64).decode("utf-8", errors="replace")
        except Exception:
            return None
        return None

    def _parse_file(self, path: str, content: str) -> FileContext:
        ext = os.path.splitext(path)[1]
        if ext == ".py":
            return parse_python_file(path, content)
        # Fallback for unknown (should not happen due to _should_ignore)
        return FileContext(path=path, language="unknown", size=len(content))

    async def generate_initial_context(self, installation_id: int, owner: str, repo: str, sha: str) -> RepositoryContext:
        """Generate a complete context from scratch."""
        full_name = f"{owner}/{repo}"
        context = RepositoryContext(
            repository=full_name,
            commit_sha=sha,
            generated_at=datetime.now(timezone.utc).isoformat()
        )

        try:
            # Get the recursive tree
            tree_data = await self._client.request(
                method="GET",
                endpoint=f"/repos/{owner}/{repo}/git/trees/{sha}",
                installation_id=installation_id,
                params={"recursive": "1"}
            )
            
            tree = tree_data.get("tree", []) if isinstance(tree_data, dict) else []
            for item in tree:
                if item.get("type") == "blob":
                    path = item.get("path", "")
                    if self._should_ignore(path):
                        continue
                    
                    content = await self._fetch_file_content(installation_id, owner, repo, path, sha)
                    if content is not None:
                        file_ctx = self._parse_file(path, content)
                        context.files[path] = file_ctx
                        
            self._storage.save_context(context)
            return context
        except Exception as e:
            raise RuntimeError(f"Failed to generate initial context: {str(e)}")

    async def update_context_for_commit(self, installation_id: int, owner: str, repo: str, sha: str) -> RepositoryContext:
        """Incrementally update context based on a commit."""
        full_name = f"{owner}/{repo}"
        context = self._storage.load_context(full_name)
        
        if not context:
            # If no previous context, generate from scratch
            return await self.generate_initial_context(installation_id, owner, repo, sha)
            
        try:
            # Get the commit details to find changed files
            commit_data = await self._client.get_commit(installation_id, owner, repo, sha)
            files = commit_data.get("files", [])
            
            for file_obj in files:
                filename = file_obj.get("filename")
                status = file_obj.get("status")
                
                if not filename or self._should_ignore(filename):
                    continue
                    
                if status == "removed":
                    if filename in context.files:
                        del context.files[filename]
                elif status == "renamed":
                    previous_filename = file_obj.get("previous_filename")
                    if previous_filename and previous_filename in context.files:
                        del context.files[previous_filename]
                    # Fetch new content
                    content = await self._fetch_file_content(installation_id, owner, repo, filename, sha)
                    if content is not None:
                        context.files[filename] = self._parse_file(filename, content)
                elif status in ("added", "modified"):
                    content = await self._fetch_file_content(installation_id, owner, repo, filename, sha)
                    if content is not None:
                        context.files[filename] = self._parse_file(filename, content)

            context.commit_sha = sha
            context.generated_at = datetime.now(timezone.utc).isoformat()
            self._storage.save_context(context)
            return context
        except Exception as e:
            # Keep previous valid context on failure
            raise RuntimeError(f"Failed to update context: {str(e)}")

    def get_context(self, repository: str) -> Optional[RepositoryContext]:
        return self._storage.load_context(repository)

repository_context_service = RepositoryContextService()
