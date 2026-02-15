"""Tests for skills directory configuration."""
from pathlib import Path

import pytest

from alfred.config import parse_skills_dirs
from alfred.pi_manager import PiManager, PiSubprocess


@pytest.mark.asyncio
async def test_parse_skills_dirs_single():
    """Test parsing single skills directory."""
    result = parse_skills_dirs("/workspace/skills")
    assert len(result) == 1
    assert result[0] == Path("/workspace/skills")


@pytest.mark.asyncio
async def test_parse_skills_dirs_multiple():
    """Test parsing multiple skills directories."""
    result = parse_skills_dirs("/workspace/skills,/home/user/skills,/opt/pi/skills")
    assert len(result) == 3
    assert result[0] == Path("/workspace/skills")
    assert result[1] == Path("/home/user/skills")
    assert result[2] == Path("/opt/pi/skills")


@pytest.mark.asyncio
async def test_parse_skills_dirs_empty():
    """Test parsing empty skills string."""
    result = parse_skills_dirs("")
    assert result == []


@pytest.mark.asyncio
async def test_parse_skills_dirs_none():
    """Test parsing None skills."""
    result = parse_skills_dirs(None)
    assert result == []


@pytest.mark.asyncio
async def test_parse_skills_dirs_with_whitespace():
    """Test parsing skills with whitespace."""
    result = parse_skills_dirs(" /workspace/skills , /home/user/skills ")
    assert len(result) == 2
    assert result[0] == Path("/workspace/skills")
    assert result[1] == Path("/home/user/skills")


@pytest.mark.asyncio
async def test_pi_subprocess_with_skills(tmp_path):
    """Test PiSubprocess includes skills in command."""
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()

    pi = PiSubprocess(
        "test_thread",
        tmp_path / "workspace",
        skills_dirs=[skills_dir]
    )

    assert len(pi.skills_dirs) == 1
    assert pi.skills_dirs[0] == skills_dir


@pytest.mark.asyncio
async def test_pi_manager_passes_skills():
    """Test PiManager passes skills to subprocess."""
    skills_dirs = [Path("/skills1"), Path("/skills2")]

    manager = PiManager(
        skills_dirs=skills_dirs
    )

    assert manager.skills_dirs == skills_dirs
