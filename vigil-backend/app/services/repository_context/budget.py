"""Context budget configuration for LLM-ready repository context (Member 2 Phase 11)."""

from pydantic import BaseModel, Field


class ContextBudget(BaseModel):
    """Configurable budget limits for LLM context generation."""

    max_files: int = Field(default=25, ge=1, description="Maximum number of files in structure/relevant lists")
    max_lines_per_file: int = Field(default=100, ge=1, description="Maximum preview lines per file snippet if included")
    max_functions: int = Field(default=50, ge=1, description="Maximum functions to list in the functions section")
    max_classes: int = Field(default=30, ge=1, description="Maximum classes to list in the classes section")
    max_dependency_relationships: int = Field(
        default=40, ge=1, description="Maximum dependency relationships to list"
    )
    max_commits: int = Field(default=10, ge=1, description="Maximum commits to list in the git context section")
    max_context_chars: int = Field(
        default=32000, ge=500, description="Hard cap on total characters generated for the prompt"
    )
