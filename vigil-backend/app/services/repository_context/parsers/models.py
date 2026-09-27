"""Data models for extracted code symbols, imports, functions, classes, and file parse results."""

from typing import List, Optional
from pydantic import BaseModel, Field


class ParsedImport(BaseModel):
    """Structured representation of an import statement."""

    source_file: str = Field(description="Path of the file containing the import")
    imported_module: str = Field(description="The imported module name or path")
    symbols: List[str] = Field(default_factory=list, description="Specific imported symbols/names")
    alias: Optional[str] = Field(default=None, description="Import alias if specified (e.g. as foo)")
    import_type: str = Field(
        default="unknown",
        description="Type of import: 'local', 'external', 'standard_lib', or 'unknown'",
    )
    line_number: int = Field(default=1, ge=1, description="1-indexed line number of the import statement")


class ParsedFunction(BaseModel):
    """Structured representation of a function or method."""

    name: str = Field(description="Function or method name")
    file: str = Field(description="Path of the file where the function is defined")
    line_start: int = Field(ge=1, description="1-indexed starting line number")
    line_end: int = Field(ge=1, description="1-indexed ending line number")
    parameters: List[str] = Field(default_factory=list, description="List of parameter names")
    containing_class: Optional[str] = Field(
        default=None, description="Name of the enclosing class if this is a method"
    )
    is_async: bool = Field(default=False, description="Whether the function is asynchronous")
    kind: str = Field(default="function", description="'function' or 'method'")
    language: str = Field(default="python", description="Source code language")
    docstring: Optional[str] = Field(default=None, description="Docstring or comment if available")


class ParsedClass(BaseModel):
    """Structured representation of a class."""

    name: str = Field(description="Class name")
    file: str = Field(description="Path of the file where the class is defined")
    line_start: int = Field(ge=1, description="1-indexed starting line number")
    line_end: int = Field(ge=1, description="1-indexed ending line number")
    bases: List[str] = Field(default_factory=list, description="List of base / parent class names")
    methods: List[str] = Field(default_factory=list, description="List of method names defined in this class")
    language: str = Field(default="python", description="Source code language")
    docstring: Optional[str] = Field(default=None, description="Docstring or comment if available")


class ParsedFileResult(BaseModel):
    """Complete code understanding result for a single parsed source file."""

    file_path: str = Field(description="Path of the source file")
    language: str = Field(description="Programming language of the source file")
    functions: List[ParsedFunction] = Field(default_factory=list, description="Functions and methods extracted")
    classes: List[ParsedClass] = Field(default_factory=list, description="Classes extracted")
    imports: List[ParsedImport] = Field(default_factory=list, description="Imports extracted")
    calls: List[str] = Field(default_factory=list, description="Function/method call expressions observed")
    parse_error: Optional[str] = Field(default=None, description="Error message if parsing failed or was partial")

    def get_symbol_names(self) -> List[str]:
        """Return names of all top-level and class-level symbols."""
        names = [c.name for c in self.classes]
        names.extend(f.name for f in self.functions)
        return names
