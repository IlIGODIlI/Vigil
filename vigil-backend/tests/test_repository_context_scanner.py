"""Tests for Phase 1 & 2: Repository Scanner, File Metadata, and Language Detection."""

import os
import tempfile
import pytest

from app.services.repository_context.languages import (
    detect_language,
    is_supported_language,
)
from app.services.repository_context.metadata import (
    FileMetadata,
    create_file_metadata,
    normalize_repo_path,
    compute_file_sha256,
)
from app.services.repository_context.scanner import (
    RepositoryScanner,
    RepositoryTree,
)


class TestLanguageDetection:
    def test_detect_python(self):
        assert detect_language("app/main.py") == "python"
        assert detect_language("types.pyi") == "python"
        assert is_supported_language("python") is True

    def test_detect_javascript_typescript(self):
        assert detect_language("src/index.js") == "javascript"
        assert detect_language("src/App.jsx") == "javascript"
        assert detect_language("src/main.ts") == "typescript"
        assert detect_language("src/Component.tsx") == "typescript"
        assert is_supported_language("javascript") is True
        assert is_supported_language("typescript") is True

    def test_detect_java(self):
        assert detect_language("com/example/PaymentService.java") == "java"
        assert is_supported_language("java") is True

    def test_detect_config_and_docs(self):
        assert detect_language("package.json") == "json"
        assert detect_language("docker-compose.yml") == "yaml"
        assert detect_language("README.md") == "markdown"
        assert detect_language("pyproject.toml") == "toml"
        assert detect_language("Dockerfile") == "dockerfile"
        assert detect_language("Makefile") == "makefile"

    def test_detect_unknown_extension_does_not_crash(self):
        assert detect_language("data.xyz123") == "unknown"
        assert detect_language("binary.bin") == "unknown"
        assert detect_language("") == "unknown"
        assert is_supported_language("unknown") is False


class TestFileMetadata:
    def test_normalize_repo_path(self):
        assert normalize_repo_path("src\\utils\\helper.py") == "src/utils/helper.py"
        assert normalize_repo_path("/root/file.py") == "root/file.py"
        assert normalize_repo_path("///nested/path.ts") == "nested/path.ts"

    def test_metadata_source_file(self):
        meta = create_file_metadata("src/payment.py", size_bytes=1024)
        assert meta.path == "src/payment.py"
        assert meta.name == "payment.py"
        assert meta.extension == ".py"
        assert meta.language == "python"
        assert meta.size_bytes == 1024
        assert meta.is_source is True
        assert meta.is_test is False
        assert meta.is_config is False
        assert meta.is_documentation is False
        assert meta.is_generated is False

    def test_metadata_test_detection(self):
        test_py = create_file_metadata("tests/test_payment.py")
        assert test_py.is_test is True
        assert test_py.is_source is False

        test_js = create_file_metadata("src/auth.test.js")
        assert test_js.is_test is True
        assert test_js.is_source is False

        spec_ts = create_file_metadata("src/service.spec.ts")
        assert spec_ts.is_test is True

        test_java = create_file_metadata("src/test/PaymentTest.java")
        assert test_java.is_test is True

    def test_metadata_config_detection(self):
        req = create_file_metadata("requirements.txt")
        assert req.is_config is True
        assert req.is_source is False

        pkg = create_file_metadata("package.json")
        assert pkg.is_config is True

        docker = create_file_metadata("Dockerfile")
        assert docker.is_config is True

        ci = create_file_metadata(".github/workflows/ci.yml")
        assert ci.is_config is True

    def test_metadata_documentation_detection(self):
        readme = create_file_metadata("README.md")
        assert readme.is_documentation is True
        assert readme.is_source is False

        doc = create_file_metadata("docs/architecture.rst")
        assert doc.is_documentation is True

    def test_metadata_generated_detection(self):
        bundle = create_file_metadata("dist/bundle.min.js")
        assert bundle.is_generated is True

        lock = create_file_metadata("package-lock.json")
        assert lock.is_generated is True

    def test_compute_sha256(self):
        with tempfile.NamedTemporaryFile("w", delete=False) as f:
            f.write("test content for hashing")
            temp_path = f.name
        try:
            h = compute_file_sha256(temp_path)
            assert h is not None
            assert len(h) == 64
        finally:
            os.remove(temp_path)


class TestRepositoryScanner:
    @pytest.fixture
    def mock_repo_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create structure
            # tmpdir/
            #   src/
            #     payment.py
            #     auth.ts
            #     utils/
            #       math.js
            #   tests/
            #     test_payment.py
            #   node_modules/
            #     ignored.js
            #   .git/
            #     HEAD
            #   README.md
            #   requirements.txt
            os.makedirs(os.path.join(tmpdir, "src", "utils"))
            os.makedirs(os.path.join(tmpdir, "tests"))
            os.makedirs(os.path.join(tmpdir, "node_modules"))
            os.makedirs(os.path.join(tmpdir, ".git"))

            with open(os.path.join(tmpdir, "src", "payment.py"), "w") as f:
                f.write("def pay(): pass\n")
            with open(os.path.join(tmpdir, "src", "auth.ts"), "w") as f:
                f.write("export const auth = () => {};\n")
            with open(os.path.join(tmpdir, "src", "utils", "math.js"), "w") as f:
                f.write("function add(a, b) { return a + b; }\n")
            with open(os.path.join(tmpdir, "tests", "test_payment.py"), "w") as f:
                f.write("def test_pay(): pass\n")
            with open(os.path.join(tmpdir, "node_modules", "ignored.js"), "w") as f:
                f.write("console.log('ignored');\n")
            with open(os.path.join(tmpdir, ".git", "HEAD"), "w") as f:
                f.write("ref: refs/heads/main\n")
            with open(os.path.join(tmpdir, "README.md"), "w") as f:
                f.write("# Sample Repo\n")
            with open(os.path.join(tmpdir, "requirements.txt"), "w") as f:
                f.write("fastapi\n")

            yield tmpdir

    def test_scan_directory(self, mock_repo_dir):
        scanner = RepositoryScanner()
        tree = scanner.scan_directory(mock_repo_dir, compute_hashes=True)

        assert tree.total_files == 6
        file_paths = {f.path for f in tree.files}

        # Check included files
        assert "src/payment.py" in file_paths
        assert "src/auth.ts" in file_paths
        assert "src/utils/math.js" in file_paths
        assert "tests/test_payment.py" in file_paths
        assert "README.md" in file_paths
        assert "requirements.txt" in file_paths

        # Check ignored files
        assert "node_modules/ignored.js" not in file_paths
        assert ".git/HEAD" not in file_paths
        assert any("node_modules" in p for p in tree.ignored_paths)
        assert any(".git" in p for p in tree.ignored_paths)

        # Check language aggregation
        assert tree.languages.get("python") == 2
        assert tree.languages.get("typescript") == 1
        assert tree.languages.get("javascript") == 1
        assert tree.languages.get("markdown") == 1

        # Check helper methods
        source_files = tree.get_source_files()
        source_paths = {f.path for f in source_files}
        assert "src/payment.py" in source_paths
        assert "src/auth.ts" in source_paths
        assert "src/utils/math.js" in source_paths
        assert "tests/test_payment.py" not in source_paths

        test_files = tree.get_test_files()
        test_paths = {f.path for f in test_files}
        assert "tests/test_payment.py" in test_paths
        assert len(test_files) == 1

    def test_scan_nonexistent_directory_does_not_crash(self):
        scanner = RepositoryScanner()
        tree = scanner.scan_directory("/path/that/definitely/does/not/exist")
        assert tree.total_files == 0
        assert len(tree.errors) > 0

    def test_scan_from_file_list(self):
        scanner = RepositoryScanner()
        github_files = [
            {"path": "backend/app.py", "size": 500, "sha": "abc1234"},
            {"path": "node_modules/package/index.js", "size": 100},
            {"path": "frontend/App.tsx", "size": 800, "sha": "def5678"},
            {"path": "docs/guide.md", "size": 250},
        ]
        tree = scanner.scan_from_file_list(github_files, root_path="owner/repo")
        assert tree.total_files == 3
        paths = [f.path for f in tree.files]
        assert "backend/app.py" in paths
        assert "frontend/App.tsx" in paths
        assert "docs/guide.md" in paths
        assert "node_modules/package/index.js" not in paths
        assert tree.get_file("backend/app.py").hash == "abc1234"
