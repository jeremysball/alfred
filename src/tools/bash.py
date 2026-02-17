"""Bash command execution tool with streaming support."""

import asyncio
import subprocess
import os
from typing import Optional

from pydantic import Field

from src.tools.base import Tool


class BashTool(Tool):
    """Execute bash commands in the current working directory."""

    name = "bash"
    description = "Execute a bash command in the current working directory. Commands run with a 60 second timeout by default (max 300 seconds). Large outputs are truncated."

    def execute(
        self,
        command: str = Field(..., description="The bash command to execute"),
        timeout: Optional[int] = Field(default=60, description="Timeout in seconds (default: 60, max: 300)"),
    ) -> dict:
        """Execute a bash command with output truncation."""
        # Clamp timeout
        timeout = min(timeout or 60, 300)
        
        try:
            # Run command
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=os.getcwd(),
            )
            
            # Truncate output if needed
            stdout = result.stdout
            stderr = result.stderr
            max_bytes = 50000
            max_lines = 2000
            truncated = False
            
            # Truncate stdout
            if len(stdout) > max_bytes:
                stdout = stdout[:max_bytes]
                truncated = True
            
            lines = stdout.split('\n')
            if len(lines) > max_lines:
                stdout = '\n'.join(lines[:max_lines])
                truncated = True
            
            # Truncate stderr (smaller limit)
            if len(stderr) > 10000:
                stderr = stderr[:10000] + "\n[stderr truncated...]"
            
            if truncated:
                stdout += "\n\n[Output truncated: use file redirection or grep for large outputs]"
            
            return {
                "success": result.returncode == 0,
                "stdout": stdout,
                "stderr": stderr,
                "exit_code": result.returncode,
                "truncated": truncated,
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"Command timed out after {timeout} seconds",
                "stdout": "",
                "stderr": "",
                "exit_code": -1,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "stdout": "",
                "stderr": "",
                "exit_code": -1,
            }
    
    async def execute_stream(self, command: str, timeout: Optional[int] = None) -> str:
        """Execute a bash command with streaming output.
        
        Yields output chunks as they are produced by the command.
        """
        timeout = min(timeout or 60, 300)
        
        yield f"[Running: {command}]\n"
        
        try:
            # Start process with pipes
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=os.getcwd(),
            )
            
            # Read output with timeout
            stdout_data = []
            stderr_data = []
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
                
                # Decode output
                stdout_text = stdout.decode('utf-8', errors='replace')
                stderr_text = stderr.decode('utf-8', errors='replace')
                
                # Yield stdout
                if stdout_text:
                    # Chunk into lines for better streaming
                    lines = stdout_text.split('\n')
                    for i, line in enumerate(lines):
                        if i < len(lines) - 1:  # Not last line
                            yield line + '\n'
                        else:  # Last line (might not have newline)
                            if line:
                                yield line
                
                # Yield stderr if any
                if stderr_text:
                    yield f"\n[stderr]:\n{stderr_text[:5000]}"
                
                # Yield exit code if non-zero
                if process.returncode != 0:
                    yield f"\n[Exit code: {process.returncode}]"
                
                # Check truncation
                if len(stdout_text) > 50000:
                    yield "\n[Output truncated: too large]"
                    
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                yield "\n[Command timed out]\n"
                
        except Exception as e:
            yield f"\n[Error: {e}]\n"