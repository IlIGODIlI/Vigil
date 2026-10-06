"""Python AST code parser extracting functions, classes, methods, imports, and calls."""

import ast
import logging
import sys
from typing import List, Optional, Set

from app.services.repository_context.parsers.models import (
    ParsedClass,
    ParsedFileResult,
    ParsedFunction,
    ParsedImport,
)

logger = logging.getLogger(__name__)

# Standard library module names in Python 3.10+
STANDARD_LIBRARY_MODULES: Set[str] = (
    getattr(sys, "stdlib_module_names", None)
    or {
        "abc", "argparse", "ast", "asyncio", "base64", "collections", "contextlib",
        "copy", "csv", "dataclasses", "datetime", "decimal", "difflib", "email",
        "enum", "functools", "glob", "hashlib", "http", "importlib", "inspect",
        "io", "itertools", "json", "logging", "math", "multiprocessing", "os",
        "pathlib", "pickle", "random", "re", "shutil", "socket", "sqlite3",
        "ssl", "string", "subprocess", "sys", "tempfile", "threading", "time",
        "typing", "unittest", "urllib", "uuid", "warnings", "weakref", "zipfile",
    }
)


class PythonASTVisitor(ast.NodeVisitor):
    """AST Visitor that traverses Python syntax trees to collect rich metadata."""

    def __init__(self, file_path: str, local_packages: Optional[Set[str]] = None):
        self.file_path = file_path
        self.local_packages = local_packages or set()
        self.functions: List[ParsedFunction] = []
        self.classes: List[ParsedClass] = []
        self.imports: List[ParsedImport] = []
        self.calls: List[str] = []

        # State tracking
        self._current_class_name: Optional[str] = None
        self._current_class_methods: List[str] = []

    def _classify_import(self, module_name: Optional[str], level: int = 0) -> str:
        """Classify an import as 'local', 'standard_lib', or 'external'."""
        if level > 0:
            return "local"
        if not module_name:
            return "unknown"

        top_module = module_name.split(".")[0]
        if top_module in STANDARD_LIBRARY_MODULES:
            return "standard_lib"

        if top_module in self.local_packages:
            return "local"

        # Check common local conventions (e.g. app.*, src.*, tests.*)
        if top_module in {"app", "src", "tests", "test", "backend", "frontend", "core", "models", "services"}:
            return "local"

        return "external"

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            import_type = self._classify_import(alias.name)
            self.imports.append(
                ParsedImport(
                    source_file=self.file_path,
                    imported_module=alias.name,
                    symbols=[],
                    alias=alias.asname,
                    import_type=import_type,
                    line_number=node.lineno,
                )
            )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        raw_module = node.module or ""
        level = node.level or 0
        dots = "." * level
        full_module = f"{dots}{raw_module}" if level > 0 else raw_module

        import_type = self._classify_import(raw_module, level=level)
        symbols = [alias.name for alias in node.names]
        alias_name = node.names[0].asname if len(node.names) == 1 else None

        self.imports.append(
            ParsedImport(
                source_file=self.file_path,
                imported_module=full_module,
                symbols=symbols,
                alias=alias_name,
                import_type=import_type,
                line_number=node.lineno,
            )
        )
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        # Extract base class names
        bases: List[str] = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute):
                bases.append(f"{self._get_attribute_name(base)}")
            elif isinstance(base, ast.Constant) and isinstance(base.value, str):
                bases.append(base.value)

        line_start = node.lineno
        line_end = getattr(node, "end_lineno", node.lineno)

        prev_class_name = self._current_class_name
        prev_methods = self._current_class_methods
        self._current_class_name = node.name
        self._current_class_methods = []

        self.generic_visit(node)

        class_obj = ParsedClass(
            name=node.name,
            file=self.file_path,
            line_start=line_start,
            line_end=line_end,
            bases=bases,
            methods=list(self._current_class_methods),
            language="python",
            docstring=ast.get_docstring(node),
        )
        self.classes.append(class_obj)

        self._current_class_name = prev_class_name
        self._current_class_methods = prev_methods

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._handle_function(node, is_async=False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._handle_function(node, is_async=True)

    def _handle_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        is_async: bool,
    ) -> None:
        is_method = self._current_class_name is not None
        kind = "method" if is_method else "function"

        # Extract argument names
        params: List[str] = []
        if getattr(node.args, "posonlyargs", None):
            params.extend(a.arg for a in node.args.posonlyargs)
        params.extend(a.arg for a in node.args.args)
        if node.args.vararg:
            params.append(f"*{node.args.vararg.arg}")
        if getattr(node.args, "kwonlyargs", None):
            params.extend(a.arg for a in node.args.kwonlyargs)
        if node.args.kwarg:
            params.append(f"**{node.args.kwarg.arg}")

        line_start = node.lineno
        line_end = getattr(node, "end_lineno", node.lineno)

        func_obj = ParsedFunction(
            name=node.name,
            file=self.file_path,
            line_start=line_start,
            line_end=line_end,
            parameters=params,
            containing_class=self._current_class_name,
            is_async=is_async,
            kind=kind,
            language="python",
            docstring=ast.get_docstring(node),
        )
        self.functions.append(func_obj)

        if is_method:
            self._current_class_methods.append(node.name)

        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        call_name = self._get_call_name(node.func)
        if call_name and call_name not in self.calls:
            self.calls.append(call_name)
        self.generic_visit(node)

    def _get_call_name(self, func_node: ast.AST) -> Optional[str]:
        if isinstance(func_node, ast.Name):
            return func_node.id
        if isinstance(func_node, ast.Attribute):
            base = self._get_call_name(func_node.value)
            return f"{base}.{func_node.attr}" if base else func_node.attr
        return None

    def _get_attribute_name(self, attr_node: ast.Attribute) -> str:
        if isinstance(attr_node.value, ast.Name):
            return f"{attr_node.value.id}.{attr_node.attr}"
        if isinstance(attr_node.value, ast.Attribute):
            return f"{self._get_attribute_name(attr_node.value)}.{attr_node.attr}"
        return attr_node.attr


class PythonASTParser:
    """Parser for Python source code using Python's standard `ast` library."""

    @staticmethod
    def parse(
        file_path: str,
        content: str,
        local_packages: Optional[Set[str]] = None,
    ) -> ParsedFileResult:
        """Parse Python source code string into structured code understanding data."""
        visitor = PythonASTVisitor(file_path=file_path, local_packages=local_packages)

        try:
            tree = ast.parse(content, filename=file_path)
            visitor.visit(tree)
            parse_error = None
        except SyntaxError as e:
            parse_error = f"SyntaxError at line {e.lineno}, col {e.offset}: {e.msg}"
            logger.debug("Syntax error in %s: %s", file_path, parse_error)
        except Exception as e:
            parse_error = f"Parse failed: {str(e)}"
            logger.warning("AST parse error in %s: %s", file_path, e)

        return ParsedFileResult(
            file_path=file_path,
            language="python",
            functions=visitor.functions,
            classes=visitor.classes,
            imports=visitor.imports,
            calls=visitor.calls,
            parse_error=parse_error,
        )
