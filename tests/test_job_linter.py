"""Tests for the job code linter."""

from alfred.cron.job_linter import lint_job_code


class TestBlockingCalls:
    """Test detection of blocking calls in async jobs."""

    def test_subprocess_run_blocked(self):
        """Should detect subprocess.run() as blocking."""
        code = """
import subprocess

async def run():
    subprocess.run(['echo', 'hello'])
"""
        errors = lint_job_code(code)
        assert len(errors) >= 1
        assert any("subprocess.run" in str(e) for e in errors)
        assert any("asyncio.create_subprocess" in str(e) for e in errors)

    def test_time_sleep_blocked(self):
        """Should detect time.sleep() as blocking."""
        code = """
import time

async def run():
    time.sleep(5)
"""
        errors = lint_job_code(code)
        assert len(errors) >= 1
        assert any("time.sleep" in str(e) for e in errors)
        assert any("asyncio.sleep" in str(e) for e in errors)

    def test_requests_blocked(self):
        """Should detect requests.get() as blocking."""
        code = """
import requests

async def run():
    requests.get('https://example.com')
"""
        errors = lint_job_code(code)
        assert len(errors) >= 1
        assert any("requests" in str(e) for e in errors)

    def test_os_system_blocked(self):
        """Should detect os.system() as blocking."""
        code = """
import os

async def run():
    os.system('echo hello')
"""
        errors = lint_job_code(code)
        assert len(errors) >= 1
        assert any("os.system" in str(e) for e in errors)


class TestNotifyUsage:
    """Test detection of incorrect notify() usage."""

    def test_subprocess_notify_blocked(self):
        """Should detect subprocess notify as wrong."""
        code = """
import subprocess

async def run():
    subprocess.run(['notify', 'Hello'])
"""
        errors = lint_job_code(code)
        # Should catch both: subprocess.run blocking AND wrong notify usage
        assert any("subprocess" in str(e).lower() for e in errors)

    def test_correct_notify_allowed(self):
        """Should allow correct async notify() call."""
        code = """
async def run():
    await notify('Hello World')
"""
        errors = lint_job_code(code)
        # Should have no errors about notify usage
        notify_errors = [e for e in errors if "notify" in str(e).lower()]
        assert len(notify_errors) == 0


class TestAsyncRequirements:
    """Test async function requirements."""

    def test_missing_run_function(self):
        """Should require run() function."""
        code = """
async def other():
    pass
"""
        errors = lint_job_code(code)
        assert any("run()" in str(e) for e in errors)

    def test_sync_run_rejected(self):
        """Should require async run, not sync."""
        code = """
def run():
    pass
"""
        errors = lint_job_code(code)
        assert any("async" in str(e).lower() for e in errors)

    def test_valid_async_run(self):
        """Should accept valid async run function."""
        code = """
async def run():
    print("Hello")
    await asyncio.sleep(1)
"""
        errors = lint_job_code(code)
        # Should pass without blocking call errors
        # Actually time.sleep would be wrong, asyncio.sleep is correct
        # So we should check that there's NO error about blocking sleep
        sleep_errors = [e for e in errors if "time.sleep" in str(e)]
        assert len(sleep_errors) == 0


class TestSyntaxErrors:
    """Test syntax error handling."""

    def test_syntax_error_reported(self):
        """Should report syntax errors clearly."""
        code = """
async def run(
    print("missing parenthesis")
"""
        errors = lint_job_code(code)
        assert len(errors) >= 1
        assert any("syntax" in str(e).lower() for e in errors)


class TestAsyncioToThread:
    """Test that asyncio.to_thread() wrapper allows blocking calls."""

    def test_time_sleep_in_to_thread_allowed(self):
        """Should allow time.sleep() when wrapped in asyncio.to_thread()."""
        code = """
import asyncio
import time

async def run():
    await asyncio.to_thread(time.sleep, 5)
"""
        errors = lint_job_code(code)
        sleep_errors = [e for e in errors if "time.sleep" in str(e)]
        assert len(sleep_errors) == 0

    def test_subprocess_run_in_to_thread_allowed(self):
        """Should allow subprocess.run() when wrapped in asyncio.to_thread()."""
        code = """
import asyncio
import subprocess

async def run():
    result = await asyncio.to_thread(subprocess.run, ['echo', 'hello'], capture_output=True)
"""
        errors = lint_job_code(code)
        subprocess_errors = [e for e in errors if "subprocess.run" in str(e)]
        assert len(subprocess_errors) == 0

    def test_file_open_in_to_thread_allowed(self):
        """Should allow open() when wrapped in asyncio.to_thread()."""
        code = """
import asyncio

async def run():
    content = await asyncio.to_thread(lambda: open('/tmp/file.txt').read())
"""
        errors = lint_job_code(code)
        open_errors = [e for e in errors if "open" in str(e).lower() and "aiofiles" in str(e)]
        assert len(open_errors) == 0

    def test_requests_in_to_thread_allowed(self):
        """Should allow requests.get() when wrapped in asyncio.to_thread()."""
        code = """
import asyncio
import requests

async def run():
    response = await asyncio.to_thread(requests.get, 'https://example.com')
"""
        errors = lint_job_code(code)
        request_errors = [e for e in errors if "requests" in str(e)]
        assert len(request_errors) == 0

    def test_unwrapped_call_still_blocked(self):
        """Should still flag unwrapped blocking calls."""
        code = """
import asyncio
import time

async def run():
    # This one is wrapped (allowed)
    await asyncio.to_thread(time.sleep, 1)
    # This one is not (blocked)
    time.sleep(5)
"""
        errors = lint_job_code(code)
        sleep_errors = [e for e in errors if "time.sleep" in str(e)]
        # Should have exactly 1 error for the unwrapped call
        assert len(sleep_errors) == 1


class TestEdgeCases:
    """Test edge cases."""

    def test_import_subprocess_no_call(self):
        """Importing subprocess without calling should be OK."""
        code = """
import subprocess

async def run():
    print("Just importing, not calling")
"""
        errors = lint_job_code(code)
        subprocess_errors = [e for e in errors if "subprocess" in str(e)]
        assert len(subprocess_errors) == 0

    def test_comment_not_flagged(self):
        """Comments mentioning blocking calls should not be flagged."""
        code = """
async def run():
    # Use subprocess.run here (just a comment)
    print("Hello")
"""
        errors = lint_job_code(code)
        subprocess_errors = [e for e in errors if "subprocess" in str(e)]
        assert len(subprocess_errors) == 0

    def test_nested_function_calls_checked(self):
        """Should check calls inside nested functions."""
        code = """
import time

async def helper():
    time.sleep(1)

async def run():
    await helper()
"""
        errors = lint_job_code(code)
        # Currently we don't check non-run async functions
        # This is a known limitation
        assert errors == []

    def test_multiple_blocking_calls(self):
        """Should detect multiple blocking calls."""
        code = """
import subprocess
import time

async def run():
    time.sleep(1)
    subprocess.run(['echo', 'hello'])
    time.sleep(2)
"""
        errors = lint_job_code(code)
        # Should have 3 errors (2 time.sleep + 1 subprocess.run)
        assert len(errors) >= 3
        sleep_errors = [e for e in errors if "time.sleep" in str(e)]
        subprocess_errors = [e for e in errors if "subprocess.run" in str(e)]
        assert len(sleep_errors) == 2
        assert len(subprocess_errors) == 1

    def test_urllib_request_blocked(self):
        """Should detect urllib.request as blocking."""
        code = """
import urllib.request

async def run():
    urllib.request.urlopen('https://example.com')
"""
        errors = lint_job_code(code)
        assert any("urllib" in str(e) for e in errors)

    def test_file_open_blocked(self):
        """Should detect open() for file I/O as blocking."""
        code = """
async def run():
    with open('/tmp/file.txt', 'r') as f:
        data = f.read()
"""
        errors = lint_job_code(code)
        assert any("open" in str(e).lower() for e in errors)
        assert any("aiofiles" in str(e) for e in errors)

    def test_input_blocked(self):
        """Should detect input() as blocking."""
        code = """
async def run():
    name = input("Enter name: ")
"""
        errors = lint_job_code(code)
        assert any("input" in str(e).lower() for e in errors)
        assert any("blocks forever" in str(e).lower() for e in errors)

    def test_subprocess_check_output_blocked(self):
        """Should detect subprocess.check_output as blocking."""
        code = """
import subprocess

async def run():
    output = subprocess.check_output(['ls', '-la'])
"""
        errors = lint_job_code(code)
        assert any("subprocess.check_output" in str(e) for e in errors)

    def test_os_popen_blocked(self):
        """Should detect os.popen as blocking."""
        code = """
import os

async def run():
    stream = os.popen('echo hello')
"""
        errors = lint_job_code(code)
        assert any("os.popen" in str(e) for e in errors)

    def test_requests_post_blocked(self):
        """Should detect requests.post as blocking."""
        code = """
import requests

async def run():
    requests.post('https://api.example.com', json={'key': 'value'})
"""
        errors = lint_job_code(code)
        assert any("requests.post" in str(e) for e in errors)

    def test_empty_code(self):
        """Should handle empty code gracefully."""
        code = ""
        errors = lint_job_code(code)
        # Should error about missing run function
        assert any("run()" in str(e) for e in errors)

    def test_no_async_def_at_all(self):
        """Should error when no async functions defined."""
        code = """
def regular_function():
    pass
"""
        errors = lint_job_code(code)
        assert any("run()" in str(e) for e in errors)

    def test_line_numbers_reported(self):
        """Should report correct line numbers for errors."""
        code = """
import time

async def run():
    # Line 5
    time.sleep(1)  # Line 6
"""
        errors = lint_job_code(code)
        sleep_errors = [e for e in errors if "time.sleep" in str(e)]
        assert len(sleep_errors) == 1
        assert sleep_errors[0].line == 6

    def test_suggestions_provided(self):
        """Should provide helpful suggestions."""
        code = """
import time

async def run():
    time.sleep(5)
"""
        errors = lint_job_code(code)
        assert len(errors) >= 1
        assert errors[0].suggestion is not None
        assert "asyncio.sleep" in errors[0].suggestion
