import pytest
from unittest.mock import AsyncMock, patch

from app.integrations.repolens.schema import RepositoryContext, FileContext, Symbol
from app.integrations.repolens.parser import parse_python_file
from app.integrations.repolens.service import RepositoryContextService
from app.integrations.repolens.storage import ContextStorage

import tempfile
import os
import shutil

@pytest.fixture
def temp_storage():
    temp_dir = tempfile.mkdtemp()
    storage = ContextStorage(base_dir=temp_dir)
    yield storage
    shutil.rmtree(temp_dir)

@pytest.fixture
def mock_github_client():
    client = AsyncMock()
    return client

def test_parse_python_file():
    code = """
import os
from typing import List

class MyService:
    def __init__(self):
        pass

    def do_work(self, arg1: str) -> None:
        pass

def standalone_func():
    pass
    """
    ctx = parse_python_file("service.py", code)
    assert ctx.path == "service.py"
    assert ctx.language == "python"
    assert len(ctx.imports) == 2
    assert "os" in ctx.imports
    assert "typing.List" in ctx.imports

    symbols = ctx.symbols
    assert len(symbols) == 4
    names = [s.name for s in symbols]
    assert "MyService" in names
    assert "MyService.__init__" in names
    assert "MyService.do_work" in names
    assert "standalone_func" in names
    
    # check method args
    do_work = next(s for s in symbols if s.name == "MyService.do_work")
    assert "arg1" in do_work.args

@pytest.mark.asyncio
async def test_generate_initial_context(temp_storage, mock_github_client):
    service = RepositoryContextService(client=mock_github_client, storage=temp_storage)

    mock_github_client.request.side_effect = [
        # 1. get tree
        {
            "tree": [
                {"path": "app/main.py", "type": "blob"},
                {"path": "node_modules/test.js", "type": "blob"}, # should be ignored
                {"path": "docs/readme.md", "type": "blob"}, # should be ignored by extension
            ]
        },
        # 2. get content for main.py
        {
            "type": "file",
            "content": "ZGVmIGhlbGxvKCk6CiAgICBwYXNzCg==" # def hello():\n    pass
        }
    ]

    ctx = await service.generate_initial_context(123, "owner", "repo", "sha123")
    
    assert ctx.repository == "owner/repo"
    assert ctx.commit_sha == "sha123"
    assert "app/main.py" in ctx.files
    assert "node_modules/test.js" not in ctx.files
    
    file_ctx = ctx.files["app/main.py"]
    assert len(file_ctx.symbols) == 1
    assert file_ctx.symbols[0].name == "hello"

@pytest.mark.asyncio
async def test_update_context_for_commit_incremental(temp_storage, mock_github_client):
    service = RepositoryContextService(client=mock_github_client, storage=temp_storage)

    # First, save a previous context
    prev_ctx = RepositoryContext(
        repository="owner/repo",
        commit_sha="oldsha",
        generated_at="2024-01-01T00:00:00",
        files={
            "app/removed.py": FileContext(path="app/removed.py", language="python", size=100),
            "app/modified.py": FileContext(path="app/modified.py", language="python", size=100, symbols=[Symbol(name="old_func", kind="function", line_number=1)])
        }
    )
    temp_storage.save_context(prev_ctx)

    mock_github_client.get_commit.return_value = {
        "files": [
            {"filename": "app/removed.py", "status": "removed"},
            {"filename": "app/modified.py", "status": "modified"},
            {"filename": "app/added.py", "status": "added"}
        ]
    }
    
    mock_github_client.request.side_effect = [
        # modified file content
        {
            "type": "file",
            "content": "ZGVmIG5ld19mdW5jKCk6CiAgICBwYXNz" # def new_func(): pass
        },
        # added file content
        {
            "type": "file",
            "content": "Y2xhc3MgTmV3Q2xhc3M6CiAgICBwYXNz" # class NewClass: pass
        }
    ]

    new_ctx = await service.update_context_for_commit(123, "owner", "repo", "newsha")
    
    assert new_ctx.commit_sha == "newsha"
    assert "app/removed.py" not in new_ctx.files
    assert "app/modified.py" in new_ctx.files
    assert "app/added.py" in new_ctx.files
    
    # modified file should have new symbols
    assert new_ctx.files["app/modified.py"].symbols[0].name == "new_func"
    assert new_ctx.files["app/added.py"].symbols[0].name == "NewClass"

@pytest.mark.asyncio
async def test_update_context_failure_keeps_old_state(temp_storage, mock_github_client):
    service = RepositoryContextService(client=mock_github_client, storage=temp_storage)

    prev_ctx = RepositoryContext(
        repository="owner/repo",
        commit_sha="oldsha",
        generated_at="2024-01-01T00:00:00",
        files={}
    )
    temp_storage.save_context(prev_ctx)

    mock_github_client.get_commit.side_effect = Exception("API error")

    with pytest.raises(RuntimeError):
        await service.update_context_for_commit(123, "owner", "repo", "newsha")
        
    # The old context should remain intact
    loaded = temp_storage.load_context("owner/repo")
    assert loaded.commit_sha == "oldsha"

def test_security_path_traversal(temp_storage):
    service = RepositoryContextService(storage=temp_storage)
    assert service._should_ignore("../../secrets.txt") is True
    assert service._should_ignore("/etc/passwd") is True
    assert service._should_ignore("node_modules/test.py") is True
    assert service._should_ignore("app/main.py") is False
