from typing import Dict, List, Optional
from pydantic import BaseModel, Field

class Symbol(BaseModel):
    name: str
    kind: str  # class, function, method
    line_number: int
    docstring: Optional[str] = None
    args: Optional[List[str]] = None

class FileContext(BaseModel):
    path: str
    language: str
    size: int
    symbols: List[Symbol] = Field(default_factory=list)
    imports: List[str] = Field(default_factory=list)

class RepositoryContext(BaseModel):
    repository: str
    commit_sha: str
    generated_at: str
    context_schema_version: str = "1.0"
    repolens_version: str = "1.0"
    files: Dict[str, FileContext] = Field(default_factory=dict)
