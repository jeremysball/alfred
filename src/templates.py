"""Template management and auto-creation for Alfred context files."""

import logging
import re
from datetime import date, datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class TemplateManager:
    """Manages template discovery and auto-creation of context files."""

    # Templates that should be auto-created if missing
    AUTO_CREATE_TEMPLATES = {"SOUL.md", "USER.md", "TOOLS.md", "MEMORY.md"}

    def __init__(self, workspace_dir: Path) -> None:
        """Initialize template manager.

        Args:
            workspace_dir: Directory where context files will be created
        """
        self.workspace_dir = workspace_dir
        self._template_dir = self._resolve_template_dir()

    def _resolve_template_dir(self) -> Path | None:
        """Resolve template directory with priority order.

        Priority:
        1. /app/templates/ (Docker bundled)
        2. ./templates/ (development)
        """
        candidates = [
            Path("/app/templates"),
            self.workspace_dir / "templates",
            Path(__file__).parent.parent / "templates",
        ]

        for candidate in candidates:
            if candidate.exists() and candidate.is_dir():
                logger.debug(f"Using template directory: {candidate}")
                return candidate

        logger.warning("No template directory found")
        return None

    @property
    def template_dir(self) -> Path:
        """Get template directory, raising if not found."""
        if self._template_dir is None:
            raise FileNotFoundError("No template directory available")
        return self._template_dir

    def get_template_path(self, name: str) -> Path:
        """Get path to template file.

        Args:
            name: Template filename (e.g., "SOUL.md")

        Returns:
            Path to the template file
        """
        return self.template_dir / name

    def get_target_path(self, name: str) -> Path:
        """Get path where file should be created in workspace.

        Args:
            name: Template filename (e.g., "SOUL.md")

        Returns:
            Path to the target file in workspace
        """
        return self.workspace_dir / name

    def template_exists(self, name: str) -> bool:
        """Check if template exists.

        Args:
            name: Template filename

        Returns:
            True if template file exists
        """
        if self._template_dir is None:
            return False
        return self.get_template_path(name).exists()

    def target_exists(self, name: str) -> bool:
        """Check if target file already exists in workspace.

        Args:
            name: Template filename

        Returns:
            True if target file exists
        """
        return self.get_target_path(name).exists()

    def load_template(self, name: str) -> str | None:
        """Load template content.

        Args:
            name: Template filename

        Returns:
            Template content or None if not found
        """
        if not self.template_exists(name):
            logger.warning(f"Template not found: {name}")
            return None

        try:
            content = self.get_template_path(name).read_text(encoding="utf-8")
            logger.debug(f"Loaded template: {name}")
            return content
        except Exception as e:
            logger.warning(f"Failed to load template {name}: {e}")
            return None

    def substitute_variables(self, content: str, variables: dict[str, str] | None = None) -> str:
        """Substitute variables in template content.

        Uses Python's str.format() style: {variable_name}

        Default variables:
            - current_date: Today's date (YYYY-MM-DD)
            - current_year: Current year

        Args:
            content: Template content with {variable} placeholders
            variables: Optional additional variables to substitute

        Returns:
            Content with variables substituted
        """
        defaults = {
            "current_date": date.today().isoformat(),
            "current_year": str(date.today().year),
        }

        if variables:
            defaults.update(variables)

        try:
            return content.format(**defaults)
        except KeyError as e:
            # If a variable is missing, leave it as-is rather than crashing
            logger.warning(f"Missing template variable: {e}")
            return content

    def create_from_template(
        self, name: str, variables: dict[str, str] | None = None, overwrite: bool = False
    ) -> Path | None:
        """Create file from template, substituting variables.

        Args:
            name: Template filename
            variables: Optional variables to substitute
            overwrite: If True, overwrite existing file

        Returns:
            Path to created file, or None if creation failed
        """
        target_path = self.get_target_path(name)

        # Don't overwrite existing files unless explicitly requested
        if target_path.exists() and not overwrite:
            logger.debug(f"File already exists, skipping: {name}")
            return target_path

        # Load template
        content = self.load_template(name)
        if content is None:
            return None

        # Substitute variables
        content = self.substitute_variables(content, variables)

        # Ensure parent directory exists
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        try:
            target_path.write_text(content, encoding="utf-8")
            logger.info(f"Created file from template: {name}")
            return target_path
        except Exception as e:
            logger.error(f"Failed to create {name}: {e}")
            return None

    def ensure_exists(self, name: str, variables: dict[str, str] | None = None) -> Path | None:
        """Ensure file exists, create from template if missing.

        Args:
            name: Template filename
            variables: Optional variables to substitute

        Returns:
            Path to file (existing or newly created), or None if creation failed
        """
        target_path = self.get_target_path(name)

        if target_path.exists():
            return target_path

        # Only auto-create known templates
        if name not in self.AUTO_CREATE_TEMPLATES:
            logger.debug(f"Not auto-creating unknown template: {name}")
            return None

        logger.info(f"Auto-creating missing file: {name}")
        return self.create_from_template(name, variables, overwrite=False)

    def ensure_all_exist(self, variables: dict[str, str] | None = None) -> dict[str, Path]:
        """Ensure all auto-create templates exist in workspace.

        Args:
            variables: Optional variables to substitute

        Returns:
            Dict mapping template names to their paths
        """
        result = {}
        for name in self.AUTO_CREATE_TEMPLATES:
            path = self.ensure_exists(name, variables)
            if path:
                result[name] = path
        return result

    def list_templates(self) -> list[str]:
        """List available template names.

        Returns:
            List of template filenames
        """
        if self._template_dir is None:
            return []

        templates = []
        for path in self._template_dir.glob("*.md"):
            if path.is_file():
                templates.append(path.name)

        return sorted(templates)

    def list_missing(self) -> list[str]:
        """List templates that don't exist in workspace.

        Returns:
            List of template filenames not yet created
        """
        return [name for name in self.AUTO_CREATE_TEMPLATES if not self.target_exists(name)]
