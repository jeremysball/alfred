"""Static analysis linter for cron job code.

Detects common foot guns in user-submitted job code before execution.
"""

import ast


class JobLinterError(Exception):
    """Lint error with details."""

    def __init__(self, message: str, line: int | None = None, suggestion: str | None = None):
        self.line = line
        self.suggestion = suggestion
        super().__init__(message)

    def __str__(self) -> str:
        parts = [self.args[0]]
        if self.line:
            parts.append(f" (line {self.line})")
        if self.suggestion:
            parts.append(f"\n  Suggestion: {self.suggestion}")
        return "".join(parts)


class BlockingCallVisitor(ast.NodeVisitor):
    """AST visitor to detect blocking calls in async functions."""

    BLOCKING_PATTERNS = {
        "subprocess.run": (
            "Use asyncio subprocess: 'asyncio.create_subprocess_exec' or "
            "'asyncio.create_subprocess_shell'"
        ),
        "subprocess.call": (
            "Use asyncio subprocess: 'asyncio.create_subprocess_exec' or "
            "'asyncio.create_subprocess_shell'"
        ),
        "subprocess.check_output": (
            "Use asyncio subprocess: 'asyncio.create_subprocess_exec' with asyncio streams"
        ),
        "subprocess.check_call": "Use asyncio subprocess: 'asyncio.create_subprocess_exec'",
        "os.system": "Use asyncio subprocess: 'asyncio.create_subprocess_shell'",
        "os.popen": "Use asyncio subprocess: 'asyncio.create_subprocess_exec'",
        "time.sleep": "Use asyncio.sleep for delays in async code",
        "requests.get": "Use aiohttp or httpx for async HTTP requests",
        "requests.post": "Use aiohttp or httpx for async HTTP requests",
        "urllib.request": "Use aiohttp or httpx for async HTTP requests",
        "open": "File I/O blocks - use aiofiles for async file operations",
        "input": "input() blocks forever - never use in cron jobs",
    }

    def __init__(self) -> None:
        self.errors: list[JobLinterError] = []
        self.in_async_function = False
        self.in_to_thread = False  # Track if we're inside asyncio.to_thread() call

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Enter async function scope."""
        if node.name == "run":
            self.in_async_function = True
            self.generic_visit(node)
            self.in_async_function = False
        else:
            # Visit other async functions but don't flag errors
            # (they might be utility functions)
            old = self.in_async_function
            self.in_async_function = False
            self.generic_visit(node)
            self.in_async_function = old

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Skip non-async functions - we don't analyze them."""
        # Only visit children, don't set in_async_function
        for child in ast.iter_child_nodes(node):
            self.visit(child)

    def visit_Call(self, node: ast.Call) -> None:
        """Check for blocking calls."""
        if not self.in_async_function:
            self.generic_visit(node)
            return

        # Get the full function name
        func_name = self._get_func_name(node.func)

        # Check if this is asyncio.to_thread() - which makes blocking calls safe
        if func_name in ("asyncio.to_thread", "to_thread"):
            old_in_to_thread = self.in_to_thread
            self.in_to_thread = True
            self.generic_visit(node)
            self.in_to_thread = old_in_to_thread
            return

        # Skip flagging if we're inside asyncio.to_thread() - the blocking call is wrapped
        if self.in_to_thread:
            self.generic_visit(node)
            return

        if func_name:
            # Check for blocking patterns
            for pattern, suggestion in self.BLOCKING_PATTERNS.items():
                # Match pattern against function name:
                # - Exact match: "time.sleep" matches "time.sleep"
                # - Prefix match: "urllib.request" matches "urllib.request.urlopen"
                # - Suffix match: "sleep" matches "time.sleep"
                # But NOT substring: "time.sleep" should NOT match "asyncio.sleep"
                func_parts = func_name.split(".")

                is_match = False
                if "." in pattern:
                    # Multi-part pattern: match as prefix or exact
                    # e.g., "time.sleep" matches "time.sleep" or starts with "time.sleep."
                    # e.g., "urllib.request" matches "urllib.request" or "urllib.request.urlopen"
                    if func_name == pattern or func_name.startswith(pattern + "."):
                        is_match = True
                else:
                    # Single-part pattern: match last component only
                    # e.g., "open" matches "open" or "os.open" but NOT "opener"
                    if func_parts[-1] == pattern:
                        is_match = True

                if is_match:
                    self.errors.append(
                        JobLinterError(
                            f"Blocking call detected: {func_name}()",
                            line=node.lineno,
                            suggestion=suggestion,
                        )
                    )
                    break

        self.generic_visit(node)

    def _get_func_name(self, node: ast.expr) -> str | None:
        """Extract full function name from AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            value = self._get_func_name(node.value)
            if value:
                return f"{value}.{node.attr}"
            return node.attr
        elif isinstance(node, ast.Subscript):
            return self._get_func_name(node.value)
        return None


class NotifyUsageVisitor(ast.NodeVisitor):
    """Check that jobs use the injected notify() function correctly."""

    def __init__(self) -> None:
        self.errors: list[JobLinterError] = []
        self.found_notify_call = False
        self.found_subprocess_notify = False
        self.in_async_function = False

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        if node.name == "run":
            self.in_async_function = True
            self.generic_visit(node)
            self.in_async_function = False

    def visit_Call(self, node: ast.Call) -> None:
        """Track notify usage patterns."""
        if not self.in_async_function:
            self.generic_visit(node)
            return

        func_name = self._get_func_name(node.func)
        if func_name:
            # Check for correct notify usage
            if func_name == "notify":
                self.found_notify_call = True

            # Check for subprocess notify (wrong way)
            if func_name in ("subprocess.run", "subprocess.call", "os.system") and node.args:
                first_arg = node.args[0]
                if isinstance(first_arg, ast.Constant) and "notify" in str(first_arg.value):
                    self.found_subprocess_notify = True
                    self.errors.append(
                        JobLinterError(
                            "Using subprocess to call 'notify' - use the injected "
                            "notify() function instead",
                            line=node.lineno,
                            suggestion="Use: await notify('your message')",
                        )
                    )

        self.generic_visit(node)

    def _get_func_name(self, node: ast.expr) -> str | None:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            value = self._get_func_name(node.value)
            if value:
                return f"{value}.{node.attr}"
            return node.attr
        return None


def lint_job_code(code: str) -> list[JobLinterError]:
    """Lint job code for common foot guns.

    Args:
        code: Python code string to lint

    Returns:
        List of lint errors (empty if code passes)
    """
    errors: list[JobLinterError] = []

    # Parse AST
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return [JobLinterError(f"Syntax error: {e}", line=e.lineno)]

    # Check for async run function
    has_async_run = False
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "run":
            has_async_run = True
            break

    if not has_async_run:
        errors.append(
            JobLinterError(
                "Job must define an async run() function",
                suggestion="Define: async def run():",
            )
        )

    # Run blocking call checks
    blocking_visitor = BlockingCallVisitor()
    blocking_visitor.visit(tree)
    errors.extend(blocking_visitor.errors)

    # Run notify usage checks
    notify_visitor = NotifyUsageVisitor()
    notify_visitor.visit(tree)
    errors.extend(notify_visitor.errors)

    return errors


def format_lint_errors(errors: list[JobLinterError]) -> str:
    """Format lint errors for display.

    Args:
        errors: List of JobLinterError objects

    Returns:
        Formatted error message
    """
    if not errors:
        return ""

    lines = ["Job code issues found:", ""]
    for i, error in enumerate(errors, 1):
        lines.append(f"{i}. {error}")
        lines.append("")

    lines.append("Please fix these issues before submitting the job.")
    return "\n".join(lines)
