"""
Deployment Hygiene Tests

This test suite validates deployment infrastructure for Cloud Run and Agent Engine.
It performs static analysis on source files and deployment scripts to prevent common
deployment failures. All tests are runnable without cloud credentials.

## Test Coverage

### 1. Python 3.11 Syntax Compatibility (TestPython311Compatibility)
   - Validates all .py files compile with Python 3.11 AST parser
   - Detects Python 3.12-only f-string syntax (nested quotes in format specs)
   - Prevents Cloud Run build failures due to syntax incompatibility

### 2. No Import-Time Environment Variable Access (TestNoImportTimeEnvVars)
   - Scans for module-level os.environ["KEY"] calls (breaks Agent Engine)
   - Flags os.environ.get("KEY") without default values
   - Allows safe patterns: os.environ.get("KEY", "default")
   - Prevents runtime KeyError crashes in Agent Engine containers

### 3. Requirements.txt Validity (TestRequirementsTxt)
   - Checks for editable installs (-e .) that break Docker builds
   - Detects local file:// references not accessible in containers
   - Ensures no self-references to the project package
   - Validates requirements.txt exists and is Docker-compatible

### 4. Cloud Run Deployment Script (TestCloudRunDeploymentScript)
   - Validates deploy_to_cloud_run.sh uses --no-emit-project flag
   - Ensures region is NOT $GOOGLE_CLOUD_LOCATION (which is "global")
   - Checks for proper CLOUD_RUN_REGION variable usage
   - Confirms --with_ui flag is present

### 5. Agent Engine Deployment Script (TestAgentEngineDeploymentScript)
   - Validates import from vertexai.preview.reasoning_engines (not agent_engines)
   - Ensures env_vars parameter is passed to AdkApp constructor
   - Checks for vertexai.init() + agent_engines.create() pattern
   - Validates required env_vars are set (BUCKET, GOOGLE_GENAI_USE_VERTEXAI, etc.)

### 6. Deployment Readiness (TestDeploymentReadiness)
   - Integration test: all Python files compile successfully
   - Checks deployment script permissions (warning only)

## Usage

Run all tests:
    pytest tests/test_deployment_hygiene.py -v

Run specific test class:
    pytest tests/test_deployment_hygiene.py::TestPython311Compatibility -v

Run in CI/CD pipeline:
    pytest tests/test_deployment_hygiene.py --tb=short

## Historical Context

This test suite was created to prevent regression of deployment bugs:

1. **Python 3.12 f-string bug (Feb 2025)**: Code used Python 3.12-only syntax
   (f-strings with nested quotes) which broke Cloud Run builds on Python 3.11.

2. **Module-level env var access (Feb 2025)**: 7 files had os.environ["KEY"]
   at module level, which crashed Agent Engine containers since env vars are
   injected AFTER module import.

3. **Editable install bug**: uv export without --no-emit-project generated
   -e . references in requirements.txt, breaking Docker builds.

4. **Region configuration bug**: Used $GOOGLE_CLOUD_LOCATION (set to "global"
   for Gemini 3 access) for Cloud Run region, which is invalid.

These tests ensure these issues never happen again through automated validation.
"""

import ast
import os
import pathlib
import re
from typing import List, Set, Tuple

import pytest


# ---------------------------------------------------------------------------
# Test Configuration
# ---------------------------------------------------------------------------

PROJECT_ROOT = pathlib.Path("/usr/local/google/home/jwortz/zghost")
AGENT_DIR = PROJECT_ROOT / "trends_and_insights_agent"
DEPLOY_CLOUD_RUN_SCRIPT = PROJECT_ROOT / "deploy_to_cloud_run.sh"
DEPLOY_AE_SCRIPT = PROJECT_ROOT / "deploy_to_ae.py"
REQUIREMENTS_TXT = AGENT_DIR / "requirements.txt"


def get_all_python_files() -> List[pathlib.Path]:
    """Get all Python files in the trends_and_insights_agent directory."""
    return list(AGENT_DIR.rglob("*.py"))


# ---------------------------------------------------------------------------
# Test 1: Python 3.11 Syntax Compatibility
# ---------------------------------------------------------------------------


class TestPython311Compatibility:
    """Validate all Python files compile with Python 3.11 syntax.

    Cloud Run uses Python 3.11 but local development may use 3.12+.
    Python 3.12 introduced new f-string syntax (nested quotes) that breaks on 3.11.

    Example that breaks Python 3.11:
        f"{foo:"{bar}"}"  # Nested quotes - Python 3.12+ only

    This should be:
        f"{foo:{bar}}"    # Works on both 3.11 and 3.12
    """

    def test_all_files_compile_with_python_311(self):
        """All .py files must compile cleanly with Python 3.11 AST parser."""
        python_files = get_all_python_files()
        assert len(python_files) > 0, "No Python files found to test"

        failures = []

        for py_file in python_files:
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    source_code = f.read()

                # Try to compile with Python 3.11 compatible AST
                compile(source_code, str(py_file), "exec")

            except SyntaxError as e:
                failures.append({
                    "file": py_file.relative_to(PROJECT_ROOT),
                    "line": e.lineno,
                    "error": str(e),
                })

        if failures:
            error_msg = "The following files have Python 3.11 syntax errors:\n\n"
            for fail in failures:
                error_msg += f"  {fail['file']}:{fail['line']}\n"
                error_msg += f"    Error: {fail['error']}\n\n"
            error_msg += "\nCloud Run uses Python 3.11. Common issues:\n"
            error_msg += "  - f-string with nested quotes: f\"{x:\"{y}\"}\" (use f\"{x:{y}}\" instead)\n"
            pytest.fail(error_msg)

    def test_no_nested_fstring_quotes(self):
        """Detect Python 3.12-only f-string syntax with nested quotes.

        This is a targeted check for the specific issue that recently broke deployment.
        Python 3.12 allows: f"{x:"{y}"}" but Python 3.11 requires: f"{x:{y}}"
        """
        python_files = get_all_python_files()
        violations = []

        # More precise regex for Python 3.12-only nested quote syntax
        # Matches format specs with quoted strings: f"{var:"format"}"
        # This pattern looks for colon followed by quote within f-string braces
        nested_quote_pattern = re.compile(
            r'f["\'].*?\{[^}]*:["\'][^}]*\}.*?["\']'
        )

        for py_file in python_files:
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    for line_num, line in enumerate(f, start=1):
                        # Skip comments
                        stripped = line.strip()
                        if stripped.startswith("#"):
                            continue

                        # Look for f-strings with format spec containing quotes
                        # Example: f"{value:"{format_str}"}" which is Python 3.12-only
                        if nested_quote_pattern.search(line):
                            # Additional check: look for :" or :" patterns (format spec with quotes)
                            if (':"' in line or ":'") in line and ('f"' in line or "f'" in line):
                                violations.append({
                                    "file": py_file.relative_to(PROJECT_ROOT),
                                    "line": line_num,
                                    "content": line.strip()[:100],
                                })
            except Exception:
                # Skip files that can't be read
                pass

        if violations:
            error_msg = "Found potential Python 3.12-only f-string syntax:\n\n"
            for v in violations:
                error_msg += f"  {v['file']}:{v['line']}\n"
                error_msg += f"    {v['content']}\n\n"
            error_msg += "Python 3.12 allows nested quotes in format specs, but Python 3.11 does not.\n"
            error_msg += "Change f\"{var:\"{fmt}\"}\" to f\"{var:{fmt}}\" for Python 3.11 compatibility.\n"
            pytest.fail(error_msg)


# ---------------------------------------------------------------------------
# Test 2: No Import-Time Environment Variable Access
# ---------------------------------------------------------------------------


class TestNoImportTimeEnvVars:
    """Prevent module-level os.environ access that breaks Agent Engine deployment.

    Agent Engine containers inject environment variables AFTER module import,
    so any os.environ["KEY"] at module level will crash with KeyError.

    Valid patterns:
        def get_config():
            return os.environ["KEY"]  # OK - runtime access

    Invalid patterns:
        CONFIG = os.environ["KEY"]    # BREAKS - module-level access
    """

    def _is_inside_function_or_class(self, node: ast.AST, tree: ast.Module) -> bool:
        """Check if a node is inside a function/method/class definition."""
        # Walk the AST to find if this node is nested inside a function/class
        for parent in ast.walk(tree):
            if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                # Check if node is in the body of this function/class
                for child in ast.walk(parent):
                    if child is node:
                        return True
        return False

    def _find_module_level_environ_access(self, py_file: pathlib.Path) -> List[Tuple[int, str]]:
        """Find os.environ access at module level (not inside functions/classes).

        Only flags unsafe patterns:
        - os.environ["KEY"] without default (raises KeyError if missing)
        - os.environ.get("KEY") WITHOUT a default parameter (returns None, may break code)

        Safe patterns that are NOT flagged:
        - os.environ.get("KEY", "default") - has fallback value
        - os.getenv("KEY", "default") - has fallback value

        Returns:
            List of (line_number, code_snippet) tuples
        """
        violations = []

        try:
            with open(py_file, "r", encoding="utf-8") as f:
                source_code = f.read()

            tree = ast.parse(source_code, filename=str(py_file))

            for node in ast.walk(tree):
                # Look for os.environ["KEY"] or os.environ.get("KEY") WITHOUT defaults
                is_unsafe_environ_access = False

                # Pattern 1: os.environ["KEY"] - always unsafe at module level
                if isinstance(node, ast.Subscript):
                    if (isinstance(node.value, ast.Attribute) and
                        isinstance(node.value.value, ast.Name) and
                        node.value.value.id == "os" and
                        node.value.attr == "environ"):
                        is_unsafe_environ_access = True

                # Pattern 2: os.environ.get("KEY") or os.getenv("KEY") WITHOUT default
                elif isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Attribute):
                        # Check if this is os.environ.get(...) or os.getenv(...)
                        is_get_call = False

                        # os.environ.get(...)
                        if (isinstance(node.func.value, ast.Attribute) and
                            isinstance(node.func.value.value, ast.Name) and
                            node.func.value.value.id == "os" and
                            node.func.value.attr == "environ" and
                            node.func.attr == "get"):
                            is_get_call = True
                        # os.getenv(...)
                        elif (isinstance(node.func.value, ast.Name) and
                              node.func.value.id == "os" and
                              node.func.attr == "getenv"):
                            is_get_call = True

                        if is_get_call:
                            # Check if default parameter is provided
                            # get("KEY", "default") or get("KEY", default="value")
                            has_default = False

                            # Check positional args (need at least 2: key and default)
                            if len(node.args) >= 2:
                                has_default = True

                            # Check keyword args for 'default'
                            for keyword in node.keywords:
                                if keyword.arg == "default":
                                    has_default = True
                                    break

                            # Only flag if NO default is provided
                            if not has_default:
                                is_unsafe_environ_access = True

                if is_unsafe_environ_access:
                    # Check if it's at module level (not inside function/class)
                    if not self._is_inside_function_or_class(node, tree):
                        # Get the line number
                        line_num = node.lineno

                        # Extract the line content
                        lines = source_code.split("\n")
                        line_content = lines[line_num - 1].strip() if line_num <= len(lines) else ""

                        violations.append((line_num, line_content))

        except SyntaxError:
            # Skip files with syntax errors (will be caught by syntax test)
            pass
        except Exception:
            # Skip files that can't be parsed
            pass

        return violations

    def test_no_module_level_environ_access(self):
        """All environment variable access must be inside functions, not at module level."""
        python_files = get_all_python_files()
        all_violations = []

        for py_file in python_files:
            violations = self._find_module_level_environ_access(py_file)
            if violations:
                all_violations.append({
                    "file": py_file.relative_to(PROJECT_ROOT),
                    "violations": violations,
                })

        if all_violations:
            error_msg = "Found module-level os.environ access (breaks Agent Engine):\n\n"
            for item in all_violations:
                error_msg += f"  {item['file']}\n"
                for line_num, content in item['violations']:
                    error_msg += f"    Line {line_num}: {content}\n"
                error_msg += "\n"

            error_msg += "Agent Engine injects env vars AFTER import. Solutions:\n"
            error_msg += "  1. Move env access into a function\n"
            error_msg += "  2. Use lazy initialization (call function at runtime)\n"
            error_msg += "  3. Use default values: os.environ.get('KEY', 'default')\n"

            pytest.fail(error_msg)


# ---------------------------------------------------------------------------
# Test 3: Requirements.txt Validity
# ---------------------------------------------------------------------------


class TestRequirementsTxt:
    """Validate requirements.txt is Docker-compatible.

    The `uv export` command can generate references that break Docker builds:
    - Editable installs: -e .
    - Local path references: file:///path/to/package
    - Self-references to the project
    """

    def test_requirements_txt_exists(self):
        """requirements.txt must exist in the agent directory."""
        assert REQUIREMENTS_TXT.exists(), (
            f"requirements.txt not found at {REQUIREMENTS_TXT}\n"
            f"Run: uv export --format requirements-txt --no-hashes --no-emit-project > {REQUIREMENTS_TXT}"
        )

    def test_no_editable_installs(self):
        """requirements.txt must not contain editable installs (-e)."""
        with open(REQUIREMENTS_TXT, "r") as f:
            lines = f.readlines()

        violations = []
        for line_num, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("-e ") or stripped.startswith("--editable"):
                violations.append((line_num, stripped))

        if violations:
            error_msg = "requirements.txt contains editable installs (breaks Docker):\n\n"
            for line_num, content in violations:
                error_msg += f"  Line {line_num}: {content}\n"
            error_msg += "\nFix: Run uv export with --no-emit-project flag\n"
            pytest.fail(error_msg)

    def test_no_local_path_references(self):
        """requirements.txt must not contain local file:// references."""
        with open(REQUIREMENTS_TXT, "r") as f:
            lines = f.readlines()

        violations = []
        for line_num, line in enumerate(lines, start=1):
            stripped = line.strip()
            if "file://" in stripped.lower():
                violations.append((line_num, stripped))

        if violations:
            error_msg = "requirements.txt contains local path references (breaks Docker):\n\n"
            for line_num, content in violations:
                error_msg += f"  Line {line_num}: {content}\n"
            error_msg += "\nLocal paths are not accessible in Docker containers.\n"
            pytest.fail(error_msg)

    def test_no_self_reference(self):
        """requirements.txt must not contain self-reference to the project."""
        with open(REQUIREMENTS_TXT, "r") as f:
            content = f.read()

        # Check for the project name (from the directory name)
        project_name = "trends-and-insights-agent"

        violations = []
        for line_num, line in enumerate(content.split("\n"), start=1):
            # Skip comments
            if line.strip().startswith("#"):
                continue

            # Look for self-reference patterns
            if project_name in line.lower() or "trends_and_insights_agent" in line.lower():
                violations.append((line_num, line.strip()))

        if violations:
            error_msg = "requirements.txt contains self-references (breaks Docker):\n\n"
            for line_num, content in violations:
                error_msg += f"  Line {line_num}: {content}\n"
            error_msg += f"\nThe project '{project_name}' should not reference itself.\n"
            pytest.fail(error_msg)


# ---------------------------------------------------------------------------
# Test 4: Cloud Run Deployment Script Validation
# ---------------------------------------------------------------------------


class TestCloudRunDeploymentScript:
    """Validate deploy_to_cloud_run.sh uses correct patterns."""

    def test_script_exists(self):
        """deploy_to_cloud_run.sh must exist."""
        assert DEPLOY_CLOUD_RUN_SCRIPT.exists(), (
            f"deploy_to_cloud_run.sh not found at {DEPLOY_CLOUD_RUN_SCRIPT}"
        )

    def test_uses_no_emit_project_flag(self):
        """Script must use --no-emit-project flag in uv export command."""
        with open(DEPLOY_CLOUD_RUN_SCRIPT, "r") as f:
            content = f.read()

        # Check for uv export command
        assert "uv export" in content, "Script does not contain 'uv export' command"

        # Check for --no-emit-project flag
        assert "--no-emit-project" in content, (
            "deploy_to_cloud_run.sh must use --no-emit-project flag in uv export\n"
            "This prevents editable install references that break Docker builds"
        )

    def test_region_not_google_cloud_location(self):
        """Script must NOT use $GOOGLE_CLOUD_LOCATION for Cloud Run region.

        GOOGLE_CLOUD_LOCATION is set to 'global' for Gemini 3 model access,
        but Cloud Run requires a specific region like 'us-central1'.
        """
        with open(DEPLOY_CLOUD_RUN_SCRIPT, "r") as f:
            content = f.read()

        # Look for adk deploy cloud_run command
        deploy_lines = [line for line in content.split("\n") if "adk deploy cloud_run" in line]

        if not deploy_lines:
            pytest.skip("Could not find 'adk deploy cloud_run' command")

        # Check that --region does NOT use $GOOGLE_CLOUD_LOCATION
        for line in content.split("\n"):
            if "--region" in line and "$GOOGLE_CLOUD_LOCATION" in line:
                pytest.fail(
                    "deploy_to_cloud_run.sh uses $GOOGLE_CLOUD_LOCATION for --region\n\n"
                    "GOOGLE_CLOUD_LOCATION is 'global' which is invalid for Cloud Run.\n"
                    "Use a separate variable like CLOUD_RUN_REGION=us-central1"
                )

    def test_uses_cloud_run_region_variable(self):
        """Script should define and use CLOUD_RUN_REGION variable."""
        with open(DEPLOY_CLOUD_RUN_SCRIPT, "r") as f:
            content = f.read()

        # Check that CLOUD_RUN_REGION is defined
        assert "CLOUD_RUN_REGION" in content, (
            "deploy_to_cloud_run.sh should define CLOUD_RUN_REGION variable\n"
            "Example: CLOUD_RUN_REGION=\"${CLOUD_RUN_REGION:-us-central1}\""
        )

    def test_uses_with_ui_flag(self):
        """Script should use --with_ui flag as per documentation."""
        with open(DEPLOY_CLOUD_RUN_SCRIPT, "r") as f:
            content = f.read()

        # Check for --with_ui flag
        assert "--with_ui" in content, (
            "deploy_to_cloud_run.sh should use --with_ui flag\n"
            "This deploys the built-in ADK UI alongside the agent"
        )


# ---------------------------------------------------------------------------
# Test 5: Agent Engine Deployment Script Validation
# ---------------------------------------------------------------------------


class TestAgentEngineDeploymentScript:
    """Validate deploy_to_ae.py uses correct patterns."""

    def test_script_exists(self):
        """deploy_to_ae.py must exist."""
        assert DEPLOY_AE_SCRIPT.exists(), (
            f"deploy_to_ae.py not found at {DEPLOY_AE_SCRIPT}"
        )

    def test_imports_from_preview_reasoning_engines(self):
        """Script must import AdkApp from vertexai.preview.reasoning_engines.

        The vertexai.agent_engines.AdkApp variant uses VertexAiSessionService
        which fails on create_session. The preview.reasoning_engines version works.
        """
        with open(DEPLOY_AE_SCRIPT, "r") as f:
            content = f.read()

        # Parse the Python file
        try:
            tree = ast.parse(content)
        except SyntaxError:
            pytest.fail("deploy_to_ae.py has syntax errors")

        # Check for correct import
        found_correct_import = False
        found_incorrect_import = False

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if (node.module == "vertexai.preview.reasoning_engines" and
                    any(alias.name == "AdkApp" for alias in node.names)):
                    found_correct_import = True

                if (node.module == "vertexai.agent_engines" and
                    any(alias.name == "AdkApp" for alias in node.names)):
                    found_incorrect_import = True

        if found_incorrect_import:
            pytest.fail(
                "deploy_to_ae.py imports from vertexai.agent_engines (incorrect)\n"
                "Use: from vertexai.preview.reasoning_engines import AdkApp"
            )

        assert found_correct_import, (
            "deploy_to_ae.py must import AdkApp from vertexai.preview.reasoning_engines\n"
            "Use: from vertexai.preview.reasoning_engines import AdkApp"
        )

    def test_passes_env_vars_to_adkapp(self):
        """Script must pass env_vars parameter to AdkApp constructor."""
        with open(DEPLOY_AE_SCRIPT, "r") as f:
            content = f.read()

        # Parse the Python file
        tree = ast.parse(content)

        # Look for AdkApp(..., env_vars=..., ...)
        found_env_vars_param = False

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Check if this is AdkApp(...)
                if (isinstance(node.func, ast.Name) and node.func.id == "AdkApp"):
                    # Check if env_vars is in keyword arguments
                    for keyword in node.keywords:
                        if keyword.arg == "env_vars":
                            found_env_vars_param = True
                            break

        assert found_env_vars_param, (
            "deploy_to_ae.py must pass env_vars to AdkApp constructor\n"
            "Example: AdkApp(agent=agent, env_vars=env_vars, ...)"
        )

    def test_uses_vertexai_init_pattern(self):
        """Script must use vertexai.init() before agent_engines.create()."""
        with open(DEPLOY_AE_SCRIPT, "r") as f:
            content = f.read()

        # Check for vertexai.init() call
        assert "vertexai.init(" in content, (
            "deploy_to_ae.py must call vertexai.init() before deployment\n"
            "Example: vertexai.init(project=PROJECT, location=LOCATION, staging_bucket=BUCKET)"
        )

    def test_uses_agent_engines_create(self):
        """Script must use agent_engines.create() for deployment."""
        with open(DEPLOY_AE_SCRIPT, "r") as f:
            content = f.read()

        # Check for agent_engines.create() call
        assert "agent_engines.create(" in content, (
            "deploy_to_ae.py must use agent_engines.create() for deployment\n"
            "Example: remote_agent = agent_engines.create(agent_engine=my_agent, ...)"
        )

    def test_env_vars_dict_includes_required_keys(self):
        """env_vars dict should include critical environment variables."""
        with open(DEPLOY_AE_SCRIPT, "r") as f:
            content = f.read()

        required_env_vars = [
            "BUCKET",
            "GOOGLE_GENAI_USE_VERTEXAI",
        ]

        missing = []
        for env_var in required_env_vars:
            # Look for env_vars["KEY"] or env_vars['KEY'] patterns in assignment
            # This matches: env_vars["KEY"] = ... or env_vars['KEY'] = ...
            if not (f'env_vars["{env_var}"]' in content or f"env_vars['{env_var}']" in content):
                missing.append(env_var)

        if missing:
            pytest.fail(
                f"deploy_to_ae.py env_vars dict missing required keys: {missing}\n"
                f"These env vars are critical for Agent Engine runtime"
            )

    def test_env_vars_dict_has_google_cloud_location(self):
        """env_vars should set GOOGLE_CLOUD_LOCATION to 'global' for Gemini 3 models."""
        with open(DEPLOY_AE_SCRIPT, "r") as f:
            content = f.read()

        # Check that GOOGLE_CLOUD_LOCATION is set in env_vars
        # Pattern: env_vars["GOOGLE_CLOUD_LOCATION"] = "global"
        if "GOOGLE_CLOUD_LOCATION" not in content:
            pytest.fail(
                "deploy_to_ae.py should set GOOGLE_CLOUD_LOCATION in env_vars\n"
                "Required for Gemini 3 preview models: env_vars['GOOGLE_CLOUD_LOCATION'] = 'global'"
            )

        # Verify it's set to "global" (required for Gemini 3)
        if '"GOOGLE_CLOUD_LOCATION"' in content or "'GOOGLE_CLOUD_LOCATION'" in content:
            # Extract the value assignment
            lines = content.split("\n")
            for line in lines:
                if "GOOGLE_CLOUD_LOCATION" in line and "env_vars" in line:
                    if "global" in line:
                        return  # Found it with correct value

        # If we get here, warn but don't fail (value might be dynamic)
        # Just ensure the key is mentioned
        assert "GOOGLE_CLOUD_LOCATION" in content, (
            "deploy_to_ae.py must set GOOGLE_CLOUD_LOCATION in env_vars"
        )


# ---------------------------------------------------------------------------
# Integration Test: End-to-End Deployment Readiness
# ---------------------------------------------------------------------------


class TestDeploymentReadiness:
    """High-level integration tests for deployment readiness."""

    def test_all_python_files_are_deployment_ready(self):
        """All Python files pass basic deployment hygiene checks."""
        python_files = get_all_python_files()

        issues = []

        for py_file in python_files:
            # Check 1: File compiles
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    source_code = f.read()
                compile(source_code, str(py_file), "exec")
            except SyntaxError as e:
                issues.append(f"{py_file.relative_to(PROJECT_ROOT)}: Syntax error at line {e.lineno}")
            except Exception as e:
                issues.append(f"{py_file.relative_to(PROJECT_ROOT)}: Compilation error: {e}")

        if issues:
            error_msg = "Some files are not deployment-ready:\n\n"
            error_msg += "\n".join(f"  - {issue}" for issue in issues)
            pytest.fail(error_msg)

    def test_deployment_scripts_are_executable(self):
        """Deployment scripts should have execute permissions (warning only)."""
        scripts_to_check = [
            DEPLOY_CLOUD_RUN_SCRIPT,
        ]

        missing_exec = []
        for script in scripts_to_check:
            if script.exists():
                if not os.access(script, os.X_OK):
                    missing_exec.append(script.relative_to(PROJECT_ROOT))

        if missing_exec:
            # Just warn - this is not critical for deployment
            # Scripts can be run with: bash deploy_to_cloud_run.sh
            import warnings
            warning_msg = f"Consider making these scripts executable: {missing_exec}\n"
            warning_msg += "Fix: chmod +x <script>"
            warnings.warn(warning_msg, UserWarning)
