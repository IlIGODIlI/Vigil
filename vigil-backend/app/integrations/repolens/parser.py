import ast
from app.integrations.repolens.schema import Symbol, FileContext

class PythonVisitor(ast.NodeVisitor):
    def __init__(self):
        self.symbols = []
        self.imports = []
        self.current_class = None

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.append(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            for alias in node.names:
                self.imports.append(f"{node.module}.{alias.name}")
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        self.symbols.append(Symbol(
            name=node.name,
            kind="class",
            line_number=node.lineno,
            docstring=ast.get_docstring(node)
        ))
        prev_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = prev_class

    def visit_FunctionDef(self, node):
        self._handle_function(node)

    def visit_AsyncFunctionDef(self, node):
        self._handle_function(node)

    def _handle_function(self, node):
        kind = "method" if self.current_class else "function"
        name = f"{self.current_class}.{node.name}" if self.current_class else node.name
        args = [arg.arg for arg in node.args.args]
        self.symbols.append(Symbol(
            name=name,
            kind=kind,
            line_number=node.lineno,
            docstring=ast.get_docstring(node),
            args=args
        ))
        self.generic_visit(node)

def parse_python_file(path: str, content: str) -> FileContext:
    visitor = PythonVisitor()
    try:
        tree = ast.parse(content)
        visitor.visit(tree)
    except SyntaxError:
        pass

    return FileContext(
        path=path,
        language="python",
        size=len(content.encode('utf-8')),
        symbols=visitor.symbols,
        imports=visitor.imports
    )
