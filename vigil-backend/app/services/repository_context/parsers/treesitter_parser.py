"""Tree-sitter code parser for JavaScript, TypeScript, JSX, TSX, and Java."""

import logging
from typing import Dict, List, Optional, Set
from tree_sitter import Language, Node, Parser
import tree_sitter_java
import tree_sitter_javascript
import tree_sitter_typescript

from app.services.repository_context.parsers.models import (
    ParsedClass,
    ParsedFileResult,
    ParsedFunction,
    ParsedImport,
)

logger = logging.getLogger(__name__)

# Node.js built-in modules
NODE_STANDARD_LIBS: Set[str] = {
    "assert", "async_hooks", "buffer", "child_process", "cluster", "console",
    "constants", "crypto", "dgram", "diagnostics_channel", "dns", "domain",
    "events", "fs", "fs/promises", "http", "http2", "https", "inspector",
    "module", "net", "os", "path", "perf_hooks", "process", "punycode",
    "querystring", "readline", "repl", "stream", "stream/promises", "string_decoder",
    "timers", "timers/promises", "tls", "trace_events", "tty", "url", "util",
    "v8", "vm", "wasi", "worker_threads", "zlib", "node:fs", "node:path", "node:http",
}


class TreeSitterParser:
    """Parser using Tree-sitter for multi-language code symbol and import extraction."""

    def __init__(self):
        self._parsers: Dict[str, Parser] = {}
        self._init_languages()

    def _init_languages(self) -> None:
        try:
            self._parsers["javascript"] = Parser(Language(tree_sitter_javascript.language()))
            self._parsers["typescript"] = Parser(Language(tree_sitter_typescript.language_typescript()))
            self._parsers["tsx"] = Parser(Language(tree_sitter_typescript.language_tsx()))
            self._parsers["java"] = Parser(Language(tree_sitter_java.language()))
        except Exception as e:
            logger.error("Failed to initialize tree-sitter grammars: %s", e)

    def parse(self, file_path: str, content: str, language: str) -> ParsedFileResult:
        """Parse source code in a supported Tree-sitter language."""
        lang_key = language.lower()
        if lang_key in {"jsx"}:
            lang_key = "javascript"
        elif lang_key in {"tsx"}:
            lang_key = "tsx"

        parser = self._parsers.get(lang_key)
        if not parser:
            return ParsedFileResult(
                file_path=file_path,
                language=language,
                parse_error=f"No tree-sitter parser configured for language: {language}",
            )

        source_bytes = content.encode("utf-8", errors="replace")

        try:
            tree = parser.parse(source_bytes)
            root_node = tree.root_node

            if lang_key in {"javascript", "typescript", "tsx"}:
                return self._parse_js_ts(root_node, file_path, language, source_bytes)
            elif lang_key == "java":
                return self._parse_java(root_node, file_path, source_bytes)
            else:
                return ParsedFileResult(
                    file_path=file_path,
                    language=language,
                    parse_error=f"Unsupported language: {language}",
                )
        except Exception as e:
            logger.warning("Tree-sitter parsing error in %s: %s", file_path, e)
            return ParsedFileResult(
                file_path=file_path,
                language=language,
                parse_error=f"Parsing error: {str(e)}",
            )

    # -------------------------------------------------------------------------
    # JavaScript & TypeScript extraction
    # -------------------------------------------------------------------------
    def _parse_js_ts(
        self,
        root_node: Node,
        file_path: str,
        language: str,
        source_bytes: bytes,
    ) -> ParsedFileResult:
        functions: List[ParsedFunction] = []
        classes: List[ParsedClass] = []
        imports: List[ParsedImport] = []
        calls: List[str] = []

        def get_node_text(node: Optional[Node]) -> str:
            if not node:
                return ""
            return source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace").strip()

        def extract_parameters(param_node: Optional[Node]) -> List[str]:
            if not param_node:
                return []
            params: List[str] = []
            for child in param_node.children:
                if child.type in {"identifier", "formal_parameter"}:
                    name_node = child.child_by_field_name("name") or child
                    params.append(get_node_text(name_node))
                elif child.type == "required_parameter":
                    # TypeScript: name: type
                    pattern = child.child_by_field_name("pattern")
                    params.append(get_node_text(pattern or child))
                elif child.type == "optional_parameter":
                    pattern = child.child_by_field_name("pattern")
                    params.append(f"{get_node_text(pattern or child)}?")
                elif child.type == "rest_pattern":
                    params.append(get_node_text(child))
            return [p for p in params if p and p not in {",", "(", ")", "{", "}"}]

        def visit_node(node: Node, current_class: Optional[str] = None):
            # 1. Imports
            if node.type == "import_statement":
                source_node = node.child_by_field_name("source")
                raw_source = get_node_text(source_node).strip("'\"`")
                line_no = node.start_point[0] + 1

                # Classify import
                if raw_source.startswith(".") or raw_source.startswith("/"):
                    import_type = "local"
                elif raw_source in NODE_STANDARD_LIBS or raw_source.startswith("node:"):
                    import_type = "standard_lib"
                else:
                    import_type = "external"

                # Extract imported symbols
                symbols: List[str] = []
                for child in node.children:
                    if child.type == "import_clause":
                        for sub in child.children:
                            if sub.type == "identifier":
                                symbols.append(get_node_text(sub))
                            elif sub.type == "named_imports":
                                for spec in sub.children:
                                    if spec.type == "import_specifier":
                                        name = spec.child_by_field_name("name")
                                        if name:
                                            symbols.append(get_node_text(name))
                            elif sub.type == "namespace_import":
                                for ns in sub.children:
                                    if ns.type == "identifier":
                                        symbols.append(get_node_text(ns))

                imports.append(
                    ParsedImport(
                        source_file=file_path,
                        imported_module=raw_source,
                        symbols=symbols,
                        import_type=import_type,
                        line_number=line_no,
                    )
                )

            # 2. Classes
            elif node.type == "class_declaration":
                name_node = node.child_by_field_name("name")
                class_name = get_node_text(name_node)
                line_start = node.start_point[0] + 1
                line_end = node.end_point[0] + 1

                # Extract base classes from heritage / extends clause
                bases: List[str] = []
                for child in node.children:
                    if child.type == "class_heritage":
                        for clause in child.children:
                            if clause.type == "extends_clause":
                                value_node = clause.child_by_field_name("value")
                                if value_node:
                                    bases.append(get_node_text(value_node))
                                else:
                                    for c in clause.children:
                                        if c.type in {"identifier", "member_expression", "type_identifier"}:
                                            bases.append(get_node_text(c))
                            elif clause.type in {"identifier", "member_expression", "type_identifier"}:
                                bases.append(get_node_text(clause))

                # Extract method names
                method_names: List[str] = []
                body_node = node.child_by_field_name("body")
                if body_node:
                    for body_child in body_node.children:
                        if body_child.type == "method_definition":
                            m_name = get_node_text(body_child.child_by_field_name("name"))
                            if m_name:
                                method_names.append(m_name)
                                # Visit method as function
                                is_async = any(c.type == "async" for c in body_child.children)
                                functions.append(
                                    ParsedFunction(
                                        name=m_name,
                                        file=file_path,
                                        line_start=body_child.start_point[0] + 1,
                                        line_end=body_child.end_point[0] + 1,
                                        parameters=extract_parameters(
                                            body_child.child_by_field_name("parameters")
                                        ),
                                        containing_class=class_name,
                                        is_async=is_async,
                                        kind="method",
                                        language=language,
                                    )
                                )
                                method_body = body_child.child_by_field_name("body")
                                if method_body:
                                    visit_node(method_body, current_class=class_name)

                classes.append(
                    ParsedClass(
                        name=class_name,
                        file=file_path,
                        line_start=line_start,
                        line_end=line_end,
                        bases=bases,
                        methods=method_names,
                        language=language,
                    )
                )

            # 3. Functions (function declarations)
            elif node.type == "function_declaration":
                name_node = node.child_by_field_name("name")
                func_name = get_node_text(name_node)
                is_async = any(c.type == "async" for c in node.children)
                params = extract_parameters(node.child_by_field_name("parameters"))

                functions.append(
                    ParsedFunction(
                        name=func_name,
                        file=file_path,
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                        parameters=params,
                        containing_class=current_class,
                        is_async=is_async,
                        kind="method" if current_class else "function",
                        language=language,
                    )
                )

            # 4. Lexical arrow functions / expressions: const foo = () => {}
            elif node.type in {"lexical_declaration", "variable_declaration"}:
                for declarator in node.children:
                    if declarator.type == "variable_declarator":
                        name_node = declarator.child_by_field_name("name")
                        value_node = declarator.child_by_field_name("value")
                        if value_node and value_node.type in {"arrow_function", "function_expression"}:
                            func_name = get_node_text(name_node)
                            is_async = any(c.type == "async" for c in value_node.children)
                            params = extract_parameters(value_node.child_by_field_name("parameters"))

                            functions.append(
                                ParsedFunction(
                                    name=func_name,
                                    file=file_path,
                                    line_start=declarator.start_point[0] + 1,
                                    line_end=declarator.end_point[0] + 1,
                                    parameters=params,
                                    containing_class=current_class,
                                    is_async=is_async,
                                    kind="method" if current_class else "function",
                                    language=language,
                                )
                            )

            # 5. Calls: foo() or obj.method()
            elif node.type == "call_expression":
                func_node = node.child_by_field_name("function")
                call_name = get_node_text(func_node)
                if call_name and call_name not in calls and len(call_name) < 100:
                    calls.append(call_name)

            # Recurse children (except class bodies which we processed above)
            if node.type != "class_declaration":
                for child in node.children:
                    visit_node(child, current_class=current_class)

        visit_node(root_node)

        return ParsedFileResult(
            file_path=file_path,
            language=language,
            functions=functions,
            classes=classes,
            imports=imports,
            calls=calls,
        )

    # -------------------------------------------------------------------------
    # Java extraction
    # -------------------------------------------------------------------------
    def _parse_java(
        self,
        root_node: Node,
        file_path: str,
        source_bytes: bytes,
    ) -> ParsedFileResult:
        functions: List[ParsedFunction] = []
        classes: List[ParsedClass] = []
        imports: List[ParsedImport] = []
        calls: List[str] = []

        def get_node_text(node: Optional[Node]) -> str:
            if not node:
                return ""
            return source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace").strip()

        def extract_java_parameters(param_node: Optional[Node]) -> List[str]:
            if not param_node:
                return []
            params: List[str] = []
            for child in param_node.children:
                if child.type == "formal_parameter":
                    name_node = child.child_by_field_name("name")
                    if name_node:
                        params.append(get_node_text(name_node))
            return params

        def visit_node(node: Node, current_class: Optional[str] = None):
            # 1. Imports
            if node.type == "import_declaration":
                line_no = node.start_point[0] + 1
                full_text = get_node_text(node).rstrip(";").replace("import ", "").replace("static ", "").strip()

                if full_text.startswith("java.") or full_text.startswith("javax."):
                    import_type = "standard_lib"
                elif full_text.startswith("org.junit") or full_text.startswith("org.springframework"):
                    import_type = "external"
                else:
                    import_type = "local"

                # Symbol is last token
                symbol = full_text.split(".")[-1]
                imports.append(
                    ParsedImport(
                        source_file=file_path,
                        imported_module=full_text,
                        symbols=[symbol] if symbol != "*" else ["*"],
                        import_type=import_type,
                        line_number=line_no,
                    )
                )

            # 2. Classes / Interfaces / Records
            elif node.type in {"class_declaration", "interface_declaration", "record_declaration"}:
                name_node = node.child_by_field_name("name")
                class_name = get_node_text(name_node)
                line_start = node.start_point[0] + 1
                line_end = node.end_point[0] + 1

                bases: List[str] = []
                superclass_node = node.child_by_field_name("superclass")
                if superclass_node:
                    base_name = get_node_text(superclass_node).replace("extends ", "").strip()
                    if base_name:
                        bases.append(base_name)

                interfaces_node = node.child_by_field_name("interfaces")
                if interfaces_node:
                    interfaces_text = get_node_text(interfaces_node).replace("implements ", "").strip()
                    for iface in interfaces_text.split(","):
                        if iface.strip():
                            bases.append(iface.strip())

                method_names: List[str] = []
                body_node = node.child_by_field_name("body")
                if body_node:
                    for body_child in body_node.children:
                        if body_child.type in {"method_declaration", "constructor_declaration"}:
                            m_name_node = body_child.child_by_field_name("name")
                            m_name = get_node_text(m_name_node)
                            if m_name:
                                method_names.append(m_name)
                                params = extract_java_parameters(
                                    body_child.child_by_field_name("parameters")
                                )
                                functions.append(
                                    ParsedFunction(
                                        name=m_name,
                                        file=file_path,
                                        line_start=body_child.start_point[0] + 1,
                                        line_end=body_child.end_point[0] + 1,
                                        parameters=params,
                                        containing_class=class_name,
                                        is_async=False,
                                        kind="method",
                                        language="java",
                                    )
                                )

                classes.append(
                    ParsedClass(
                        name=class_name,
                        file=file_path,
                        line_start=line_start,
                        line_end=line_end,
                        bases=bases,
                        methods=method_names,
                        language="java",
                    )
                )

            # 3. Method Calls
            elif node.type == "method_invocation":
                name_node = node.child_by_field_name("name")
                call_name = get_node_text(name_node)
                if call_name and call_name not in calls:
                    calls.append(call_name)

            # Recurse children (except class bodies which we processed above)
            if node.type not in {"class_declaration", "interface_declaration", "record_declaration"}:
                for child in node.children:
                    visit_node(child, current_class=current_class)

        visit_node(root_node)

        return ParsedFileResult(
            file_path=file_path,
            language="java",
            functions=functions,
            classes=classes,
            imports=imports,
            calls=calls,
        )
