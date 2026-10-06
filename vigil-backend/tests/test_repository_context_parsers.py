"""Tests for Phase 3 & 4: Python AST Parser and Tree-sitter Parsers (JS, TS, Java)."""

import pytest

from app.services.repository_context.parsers.dispatcher import parse_source_file
from app.services.repository_context.parsers.python_parser import PythonASTParser
from app.services.repository_context.parsers.treesitter_parser import TreeSitterParser


class TestPythonASTParser:
    def test_parse_functions_and_classes(self):
        code = """
import os
from typing import List, Optional
from .auth import verify_token
import httpx

class BaseService:
    pass

class PaymentService(BaseService):
    \"\"\"Service handling payment transactions.\"\"\"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def process_payment(self, user_id: str, amount: float, *tags, **metadata) -> bool:
        \"\"\"Process a user transaction safely.\"\"\"
        verify_token(user_id)
        return True

def standalone_helper(x, y=10):
    return x + y
"""
        result = PythonASTParser.parse("backend/payment.py", code)
        assert result.file_path == "backend/payment.py"
        assert result.language == "python"
        assert result.parse_error is None

        # Classes
        assert len(result.classes) == 2
        base_cls = next(c for c in result.classes if c.name == "BaseService")
        assert base_cls.bases == []

        pay_cls = next(c for c in result.classes if c.name == "PaymentService")
        assert pay_cls.bases == ["BaseService"]
        assert pay_cls.docstring == "Service handling payment transactions."
        assert "PaymentService" in pay_cls.name
        assert "__init__" in pay_cls.methods
        assert "process_payment" in pay_cls.methods

        # Functions & Methods
        assert len(result.functions) == 3
        init_m = next(f for f in result.functions if f.name == "__init__")
        assert init_m.kind == "method"
        assert init_m.containing_class == "PaymentService"
        assert "api_key" in init_m.parameters

        proc_m = next(f for f in result.functions if f.name == "process_payment")
        assert proc_m.kind == "method"
        assert proc_m.is_async is True
        assert proc_m.containing_class == "PaymentService"
        assert "user_id" in proc_m.parameters
        assert "amount" in proc_m.parameters
        assert "*tags" in proc_m.parameters
        assert "**metadata" in proc_m.parameters
        assert proc_m.docstring == "Process a user transaction safely."
        assert proc_m.line_start < proc_m.line_end

        helper_f = next(f for f in result.functions if f.name == "standalone_helper")
        assert helper_f.kind == "function"
        assert helper_f.containing_class is None
        assert helper_f.parameters == ["x", "y"]

        # Imports
        assert len(result.imports) == 4
        imp_os = next(i for i in result.imports if i.imported_module == "os")
        assert imp_os.import_type == "standard_lib"

        imp_typing = next(i for i in result.imports if i.imported_module == "typing")
        assert imp_typing.import_type == "standard_lib"
        assert "List" in imp_typing.symbols

        imp_auth = next(i for i in result.imports if i.imported_module == ".auth")
        assert imp_auth.import_type == "local"
        assert "verify_token" in imp_auth.symbols

        imp_httpx = next(i for i in result.imports if i.imported_module == "httpx")
        assert imp_httpx.import_type == "external"

        # Calls
        assert any("verify_token" in call for call in result.calls)

    def test_parse_syntax_error_resilience(self):
        malformed_code = "def broken_syntax(x: return { invalid"
        result = PythonASTParser.parse("broken.py", malformed_code)
        assert result.file_path == "broken.py"
        assert result.language == "python"
        assert result.parse_error is not None
        assert "SyntaxError" in result.parse_error
        assert result.functions == []
        assert result.classes == []


class TestJavaScriptParser:
    def test_parse_javascript_functions_classes_imports(self):
        code = """
import { auth } from "./auth.js";
import express from "express";
import * as fs from "fs";

class PaymentController extends BaseController {
    processPayment(req, res) {
        auth.verify(req);
        return res.json({ success: true });
    }
}

function calculateDiscount(price, percentage) {
    return price * (1 - percentage);
}

const formatCurrency = (amount) => {
    return "$" + amount;
};
"""
        parser = TreeSitterParser()
        result = parser.parse("src/payment.js", code, "javascript")
        assert result.file_path == "src/payment.js"
        assert result.language == "javascript"
        assert result.parse_error is None

        # Classes
        assert len(result.classes) == 1
        cls = result.classes[0]
        assert cls.name == "PaymentController"
        assert cls.bases == ["BaseController"]
        assert "processPayment" in cls.methods

        # Functions
        func_names = [f.name for f in result.functions]
        assert "processPayment" in func_names
        assert "calculateDiscount" in func_names
        assert "formatCurrency" in func_names

        calc_func = next(f for f in result.functions if f.name == "calculateDiscount")
        assert "price" in calc_func.parameters
        assert "percentage" in calc_func.parameters

        method_func = next(f for f in result.functions if f.name == "processPayment")
        assert method_func.kind == "method"
        assert method_func.containing_class == "PaymentController"

        # Imports
        assert len(result.imports) == 3
        local_imp = next(i for i in result.imports if i.imported_module == "./auth.js")
        assert local_imp.import_type == "local"
        assert "auth" in local_imp.symbols

        ext_imp = next(i for i in result.imports if i.imported_module == "express")
        assert ext_imp.import_type == "external"

        stdlib_imp = next(i for i in result.imports if i.imported_module == "fs")
        assert stdlib_imp.import_type == "standard_lib"

        # Calls
        assert any("auth.verify" in c or "verify" in c for c in result.calls)

    def test_javascript_class_inheritance_regression(self):
        code = """
class BaseService {}
class AuthService extends BaseService {}
class ApiClient extends network.Client {}
class Standalone {}
"""
        parser = TreeSitterParser()
        result = parser.parse("src/services.js", code, "javascript")
        assert result.parse_error is None
        assert len(result.classes) == 4

        cls_map = {c.name: c.bases for c in result.classes}
        assert cls_map["BaseService"] == []
        assert cls_map["AuthService"] == ["BaseService"]
        assert cls_map["ApiClient"] == ["network.Client"]
        assert cls_map["Standalone"] == []


class TestTypeScriptParser:
    def test_parse_typescript_components_and_types(self):
        code = """
import { Request, Response } from "express";
import { User } from "../models/User";

export class UserService extends BaseService {
    async getUserById(id: string): Promise<User> {
        return { id, name: "Alice" };
    }
}

export const validateUser = (user: User): boolean => {
    return Boolean(user.id);
};
"""
        parser = TreeSitterParser()
        result = parser.parse("src/services/userService.ts", code, "typescript")
        assert result.file_path == "src/services/userService.ts"
        assert result.language == "typescript"
        assert result.parse_error is None

        # Classes
        assert len(result.classes) == 1
        cls = result.classes[0]
        assert cls.name == "UserService"
        assert cls.bases == ["BaseService"]
        assert "getUserById" in cls.methods

        # Functions
        func_names = [f.name for f in result.functions]
        assert "getUserById" in func_names
        assert "validateUser" in func_names

        # Imports
        user_imp = next(i for i in result.imports if "../models/User" in i.imported_module)
        assert user_imp.import_type == "local"
        assert "User" in user_imp.symbols


class TestJavaParser:
    def test_parse_java_class_methods_imports(self):
        code = """
package com.example.service;

import java.util.List;
import javax.crypto.Cipher;
import com.example.database.Database;
import org.junit.jupiter.api.Test;

public class PaymentService extends BaseService implements IPayment, IAuditable {
    public PaymentService() {
    }

    public boolean processPayment(String transactionId, double amount) {
        validateTransaction(transactionId);
        return true;
    }
}
"""
        parser = TreeSitterParser()
        result = parser.parse("src/main/java/PaymentService.java", code, "java")
        assert result.file_path == "src/main/java/PaymentService.java"
        assert result.language == "java"
        assert result.parse_error is None

        # Classes
        assert len(result.classes) == 1
        cls = result.classes[0]
        assert cls.name == "PaymentService"
        assert "BaseService" in cls.bases
        assert "IPayment" in cls.bases
        assert "IAuditable" in cls.bases
        assert "processPayment" in cls.methods

        # Methods
        proc_m = next(f for f in result.functions if f.name == "processPayment")
        assert proc_m.kind == "method"
        assert proc_m.containing_class == "PaymentService"
        assert "transactionId" in proc_m.parameters
        assert "amount" in proc_m.parameters

        # Imports
        assert len(result.imports) == 4
        stdlib_imp = next(i for i in result.imports if "java.util.List" in i.imported_module)
        assert stdlib_imp.import_type == "standard_lib"

        local_imp = next(i for i in result.imports if "com.example.database.Database" in i.imported_module)
        assert local_imp.import_type == "local"

        ext_imp = next(i for i in result.imports if "org.junit" in i.imported_module)
        assert ext_imp.import_type == "external"


class TestDispatcher:
    def test_dispatcher_routing(self):
        py_res = parse_source_file("app/main.py", "def root(): pass")
        assert py_res.language == "python"
        assert len(py_res.functions) == 1
        assert py_res.functions[0].name == "root"

        js_res = parse_source_file("app/index.js", "function run() {}")
        assert js_res.language == "javascript"
        assert len(js_res.functions) == 1
        assert js_res.functions[0].name == "run"

        ts_res = parse_source_file("app/index.ts", "function start(): void {}")
        assert ts_res.language == "typescript"
        assert len(ts_res.functions) == 1

        java_res = parse_source_file("App.java", "class App { void main() {} }")
        assert java_res.language == "java"
        assert len(java_res.classes) == 1

    def test_dispatcher_unsupported_language_fails_gracefully(self):
        res = parse_source_file("image.png", "binarycontent")
        assert res.language == "unknown"
        assert res.functions == []
        assert res.classes == []
        assert "not currently configured" in res.parse_error
