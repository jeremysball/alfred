"""Template management and auto-creation for Alfred context files."""

import hashlib
import logging
import shutil
from datetime import date
from pathlib import Path

from alfred.data_manager import get_cache_dir
from alfred.placeholders import CURRENT_TIME_PLACEHOLDER, SINGLE_BRACE_VOLATILE_PLACEHOLDER_PATTERN
from alfred.template_sync import TemplateBaseSnapshot, TemplateSyncRecord, TemplateSyncState, TemplateSyncStore

logger = logging.getLogger(__name__)


class TemplateManager:
    """Manages template discovery and auto-creation of context files."""

    # Templates that should be auto-created if missing
    AUTO_CREATE_TEMPLATES = {"SYSTEM.md", "AGENTS.md", "SOUL.md", "USER.md"}

    def __init__(self, workspace_dir: Path, cache_dir: Path | None = None) -> None:
        """Initialize template manager.

        Args:
            workspace_dir: Directory where context files will be created
            cache_dir: Directory where sync metadata will be stored
        """
        self.workspace_dir = workspace_dir
        self._cache_dir = cache_dir
        self._template_dir = self._resolve_template_dir()
        self._sync_store: TemplateSyncStore | None = None

    def _resolve_template_dir(self) -> Path | None:
        """Resolve template directory with priority order.

        Priority:
        1. Workspace templates (for tests/local override)
        2. /app/templates/ (Docker bundled)
        3. Development: git repo root /templates
        4. Bundled templates with package (pip installed)
        """
        # Check workspace first (user override)
        workspace_templates = self.workspace_dir / "templates"
        if workspace_templates.exists() and workspace_templates.is_dir():
            logger.debug(f"Using template directory: {workspace_templates}")
            return workspace_templates

        # Docker bundled
        docker_templates = Path("/app/templates")
        if docker_templates.exists() and docker_templates.is_dir():
            logger.debug(f"Using template directory: {docker_templates}")
            return docker_templates

        # Development: check if we're in a git repo with templates at root
        # Walk up from package location looking for .git/templates
        pkg_dir = Path(__file__).parent.parent  # src/alfred -> src/
        for parent in [pkg_dir, pkg_dir.parent]:  # src/, repo root
            git_dir = parent / ".git"
            templates_dir = parent / "templates"
            if git_dir.exists() and templates_dir.exists():
                logger.debug(f"Using template directory: {templates_dir}")
                return templates_dir

        # Pip installed: templates next to package
        pkg_templates = pkg_dir / "templates"
        if pkg_templates.exists() and pkg_templates.is_dir():
            logger.debug(f"Using template directory: {pkg_templates}")
            return pkg_templates

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
        Preserves {{file}} placeholders for later resolution.

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

        # Temporarily protect {{placeholders}} from str.format()
        # by replacing them with sentinel values
        import re

        placeholders: list[str] = re.findall(r"\{\{[^}]+\}\}", content)
        sentinel_map: dict[str, str] = {}
        for i, ph in enumerate(placeholders):
            sentinel = f"___PLACEHOLDER_{i}___"
            sentinel_map[sentinel] = ph
            content = content.replace(ph, sentinel, 1)

        # Keep runtime placeholders intact for later resolution in the prompt loader.
        runtime_placeholders = [match.group(0) for match in re.finditer(re.escape(CURRENT_TIME_PLACEHOLDER), content)]
        runtime_placeholders.extend(match.group(0) for match in SINGLE_BRACE_VOLATILE_PLACEHOLDER_PATTERN.finditer(content))
        for i, ph in enumerate(runtime_placeholders, start=len(sentinel_map)):
            sentinel = f"___RUNTIME_PLACEHOLDER_{i}___"
            sentinel_map[sentinel] = ph
            content = content.replace(ph, sentinel, 1)

        try:
            content = content.format(**defaults)
        except KeyError as e:
            # If a variable is missing, leave it as-is rather than crashing
            logger.warning(f"Missing template variable: {e}")

        # Restore {{placeholders}} and runtime placeholders
        for sentinel, ph in sentinel_map.items():
            content = content.replace(sentinel, ph)

        return content

    def _get_sync_store(self) -> TemplateSyncStore:
        """Get or create the template sync store."""
        if self._sync_store is None:
            cache_dir = self._cache_dir or get_cache_dir()
            self._sync_store = TemplateSyncStore(cache_dir / "template-sync.json")
        return self._sync_store

    def _hash_content(self, content: str) -> str:
        """Hash template content for sync tracking."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _persist_sync_record(
        self,
        name: str,
        template_content: str,
        workspace_content: str,
        workspace_path: Path,
        state: TemplateSyncState,
        base_snapshot: TemplateBaseSnapshot | None,
    ) -> None:
        """Persist template sync metadata, best-effort."""
        template_hash = self._hash_content(template_content)
        workspace_hash = self._hash_content(workspace_content)
        base_hash = base_snapshot.hash if base_snapshot is not None else template_hash
        record = TemplateSyncRecord(
            name=name,
            template_path=self.get_template_path(name),
            workspace_path=workspace_path,
            template_hash=template_hash,
            workspace_hash=workspace_hash,
            base_hash=base_hash,
            base_snapshot=base_snapshot,
            state=state,
        )
        try:
            self._get_sync_store().save(record)
        except Exception as exc:
            logger.warning(f"Failed to save template sync snapshot for {name}: {exc}")

    def _ensure_trailing_newline(self, text: str) -> str:
        """Ensure marker sections stay on their own lines."""
        return text if text.endswith("\n") else f"{text}\n"

    def _build_conflict_markers(self, workspace_content: str, template_content: str) -> str:
        """Wrap diverging content in standard git conflict markers."""
        return (
            "<<<<<<< ours\n"
            f"{self._ensure_trailing_newline(workspace_content)}"
            "=======\n"
            f"{self._ensure_trailing_newline(template_content)}"
            ">>>>>>> theirs\n"
        )

    def _record_base_snapshot(self, name: str, content: str, workspace_path: Path) -> None:
        """Persist the clean template content as the merge base."""
        snapshot = TemplateBaseSnapshot(content=content, hash=self._hash_content(content))
        self._persist_sync_record(
            name=name,
            template_content=content,
            workspace_content=content,
            workspace_path=workspace_path,
            state=TemplateSyncState.CLEAN,
            base_snapshot=snapshot,
        )

    def _record_conflicted_snapshot(
        self,
        name: str,
        template_content: str,
        workspace_content: str,
        workspace_path: Path,
        base_snapshot: TemplateBaseSnapshot,
    ) -> None:
        """Persist a conflicted sync record without changing file content."""
        self._persist_sync_record(
            name=name,
            template_content=template_content,
            workspace_content=workspace_content,
            workspace_path=workspace_path,
            state=TemplateSyncState.CONFLICTED,
            base_snapshot=base_snapshot,
        )

    def _record_merged_snapshot(
        self,
        name: str,
        template_content: str,
        workspace_content: str,
        workspace_path: Path,
    ) -> None:
        """Persist a resolved merge result as the new clean base."""
        snapshot = TemplateBaseSnapshot(content=workspace_content, hash=self._hash_content(workspace_content))
        self._persist_sync_record(
            name=name,
            template_content=template_content,
            workspace_content=workspace_content,
            workspace_path=workspace_path,
            state=TemplateSyncState.MERGED,
            base_snapshot=snapshot,
        )

    def _has_conflict_markers(self, content: str) -> bool:
        """Return True when content contains standard git conflict markers."""
        return content.startswith("<<<<<<< ours\n") and "\n=======\n" in content and content.rstrip().endswith(">>>>>>> theirs")

    def _write_conflicted_template_content(
        self,
        name: str,
        workspace_content: str,
        template_content: str,
        target_path: Path,
        base_snapshot: TemplateBaseSnapshot,
    ) -> None:
        """Write standard conflict markers and persist a conflicted snapshot."""
        conflicted_content = self._build_conflict_markers(workspace_content, template_content)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(conflicted_content, encoding="utf-8")
        self._record_conflicted_snapshot(
            name=name,
            template_content=template_content,
            workspace_content=conflicted_content,
            workspace_path=target_path,
            base_snapshot=base_snapshot,
        )

    def _write_template_content(self, name: str, content: str, target_path: Path) -> None:
        """Write final template content and record its clean snapshot."""
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(content, encoding="utf-8")
        self._record_base_snapshot(name, content, target_path)

    def get_sync_record(self, name: str) -> TemplateSyncRecord | None:
        """Return the persisted sync record for a template, if it belongs to this workspace."""
        record = self._get_sync_store().get(name)
        if record is None:
            return None
        if record.workspace_path != self.get_target_path(name):
            return None
        return record

    def get_base_snapshot(self, name: str) -> TemplateBaseSnapshot | None:
        """Return the last known clean snapshot for this workspace, if available."""
        record = self.get_sync_record(name)
        if record is None:
            return None
        return record.base_snapshot

    def create_from_template(self, name: str, variables: dict[str, str] | None = None, overwrite: bool = False) -> Path | None:
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

        # Write file
        try:
            self._write_template_content(name, content, target_path)
            logger.info(f"Created file from template: {name}")
            return target_path
        except Exception as e:
            try:
                target_path.unlink(missing_ok=True)
            except Exception as cleanup_error:
                logger.warning(f"Failed to clean up {target_path}: {cleanup_error}")
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

    def ensure_prompts_exist(self) -> Path | None:
        """Ensure prompts directory exists in workspace, copy from templates if missing.

        Copies all files from templates/prompts/ to workspace/prompts/.
        Does not overwrite existing files.

        Returns:
            Path to prompts directory, or None if creation failed
        """
        if self._template_dir is None:
            return None

        source_prompts = self._template_dir / "prompts"
        if not source_prompts.exists():
            logger.debug("No prompts directory in templates")
            return None

        target_prompts = self.workspace_dir / "prompts"

        # Copy prompts directory tree using shutil
        # Use dirs_exist_ok=True to not fail if directory exists
        # Use ignore callback to skip existing files
        def ignore_existing(src: str, names: list[str]) -> set[str]:
            """Ignore files that already exist in the destination."""
            ignored = set()
            src_path = Path(src)
            for name in names:
                rel_path = src_path.relative_to(source_prompts) / name
                target_file = target_prompts / rel_path
                if target_file.exists():
                    ignored.add(name)
            return ignored

        try:
            shutil.copytree(
                source_prompts,
                target_prompts,
                ignore=ignore_existing,
                dirs_exist_ok=True,
            )
            logger.info(f"Prompts directory synchronized: {target_prompts}")
        except Exception as e:
            logger.error(f"Failed to copy prompts directory: {e}")
            return None

        return target_prompts

    def _read_file_text(self, path: Path, name: str) -> str | None:
        """Read file content for reconciliation checks."""
        try:
            return path.read_text(encoding="utf-8")
        except Exception as exc:
            logger.warning(f"Failed to read {name}: {exc}")
            return None

    def _should_skip_by_mtime(self, name: str, template_path: Path, target_path: Path) -> bool:
        """Return True when a template file is not newer than the workspace copy."""
        try:
            template_mtime = template_path.stat().st_mtime
            target_mtime = target_path.stat().st_mtime
            return template_mtime <= target_mtime
        except Exception as exc:
            logger.warning(f"Could not compare mtimes for {name}: {exc}")
            return False

    def reconcile_template(
        self,
        name: str,
        preserve: set[str] | None = None,
        dry_run: bool = False,
    ) -> dict[str, str]:
        """Reconcile one workspace file with its template."""
        if self._template_dir is None:
            return {
                "status": "error",
                "message": "No template directory available",
            }

        target_path = self.get_target_path(name)
        template_path = self.get_template_path(name)

        # Skip directories (like prompts/)
        if template_path.is_dir():
            return {
                "status": "skipped",
                "message": "Template is a directory",
            }

        if preserve is None:
            preserve = {"USER.md", "SOUL.md", "CUSTOM.md"}

        if name in preserve and target_path.exists():
            return {
                "status": "preserved",
                "message": "Preserved (in preserve list)",
            }

        if not self.template_exists(name):
            return {
                "status": "error",
                "message": "Template not found",
            }

        content = self.load_template(name)
        if content is None:
            return {
                "status": "error",
                "message": "Failed to load template",
            }

        content = self.substitute_variables(content)

        if target_path.exists():
            base_snapshot = self.get_base_snapshot(name)
            record = self.get_sync_record(name)
            workspace_content = self._read_file_text(target_path, name)

            if workspace_content is not None:
                if workspace_content == content:
                    if base_snapshot is not None and base_snapshot.content == content:
                        if record is not None and not record.is_clean():
                            if dry_run:
                                return {
                                    "status": "dry_run",
                                    "message": f"Would refresh {name}",
                                }
                            self._record_base_snapshot(name, content, target_path)
                            logger.info(f"Refreshed template snapshot: {name}")
                            return {
                                "status": "updated",
                                "message": "Updated from template",
                            }
                        return {
                            "status": "skipped",
                            "message": "Already up to date",
                        }
                    if dry_run:
                        return {
                            "status": "dry_run",
                            "message": f"Would update {name}",
                        }
                    self._record_base_snapshot(name, content, target_path)
                    logger.info(f"Refreshed template snapshot: {name}")
                    return {
                        "status": "updated",
                        "message": "Updated from template",
                    }

                if base_snapshot is not None:
                    if workspace_content == base_snapshot.content:
                        # Workspace still matches the last saved base, so we can
                        # fast-forward even if mtimes look stale.
                        # However, don't fast-forward if this was a merge - the user
                        # explicitly resolved to something different from template.
                        if record is not None and record.state is TemplateSyncState.MERGED:
                            return {
                                "status": "skipped",
                                "message": "Merged content preserved",
                            }
                        if dry_run:
                            return {
                                "status": "dry_run",
                                "message": f"Would update {name}",
                            }
                        try:
                            self._write_template_content(name, content, target_path)
                            logger.info(f"Updated template: {name}")
                            return {
                                "status": "updated",
                                "message": "Updated from template",
                            }
                        except Exception as e:
                            return {
                                "status": "error",
                                "message": f"Error: {e}",
                            }

                    if record is not None and record.is_conflicted() and not self._has_conflict_markers(workspace_content):
                        if dry_run:
                            return {
                                "status": "dry_run",
                                "message": f"Would record merged resolution for {name}",
                            }
                        self._record_merged_snapshot(name, content, workspace_content, target_path)
                        logger.info(f"Recorded merged template resolution: {name}")
                        return {
                            "status": "merged",
                            "message": "Recorded resolved merge",
                        }

                    if self._has_conflict_markers(workspace_content):
                        if dry_run:
                            return {
                                "status": "dry_run",
                                "message": f"Would record conflict markers for {name}",
                            }
                        self._record_conflicted_snapshot(name, content, workspace_content, target_path, base_snapshot)
                        logger.warning(f"Template conflict markers preserved: {name}")
                        return {
                            "status": "conflicted",
                            "message": "Conflict markers already present",
                        }

                    if content == base_snapshot.content:
                        return {
                            "status": "skipped",
                            "message": "Workspace diverged from saved base",
                        }

                    if dry_run:
                        return {
                            "status": "dry_run",
                            "message": f"Would write conflict markers for {name}",
                        }
                    try:
                        self._write_conflicted_template_content(name, workspace_content, content, target_path, base_snapshot)
                        logger.warning(f"Template conflict markers written: {name}")
                        return {
                            "status": "conflicted",
                            "message": "Wrote conflict markers",
                        }
                    except Exception as e:
                        return {
                            "status": "error",
                            "message": f"Error: {e}",
                        }
                elif self._should_skip_by_mtime(name, template_path, target_path):
                    return {
                        "status": "skipped",
                        "message": "Already up to date",
                    }
            elif self._should_skip_by_mtime(name, template_path, target_path):
                return {
                    "status": "skipped",
                    "message": "Already up to date",
                }

        if dry_run:
            return {
                "status": "dry_run",
                "message": f"Would update {name}",
            }

        try:
            self._write_template_content(name, content, target_path)
            logger.info(f"Updated template: {name}")
            return {
                "status": "updated",
                "message": "Updated from template",
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error: {e}",
            }

    def update_templates(
        self,
        preserve: set[str] | None = None,
        dry_run: bool = False,
    ) -> dict[str, dict[str, str]]:
        """Update config files from templates, preserving specified files.

        Args:
            preserve: Set of filenames to preserve (not overwrite).
                     Defaults to {"USER.md", "SOUL.md", "CUSTOM.md"}
            dry_run: If True, show what would be updated without making changes

        Returns:
            Dict mapping template names to their update status:
            {
                "filename": {
                    "status": "updated" | "merged" | "conflicted" | "preserved" | "skipped" | "dry_run" | "error",
                    "message": "..."
                }
            }
        """
        if preserve is None:
            preserve = {"USER.md", "SOUL.md", "CUSTOM.md"}

        results: dict[str, dict[str, str]] = {}
        for name in self.list_templates():
            result = self.reconcile_template(name, preserve=preserve, dry_run=dry_run)
            if result:
                results[name] = result

        # Also update prompts directory
        prompts_result = self._update_prompts(dry_run=dry_run)
        if prompts_result:
            results["prompts/"] = prompts_result

        return results

    def _update_prompts(self, dry_run: bool = False) -> dict[str, str] | None:
        """Update prompts directory from templates.

        Args:
            dry_run: If True, don't actually make changes

        Returns:
            Status dict or None if no prompts to update
        """
        if self._template_dir is None:
            return None

        source_prompts = self._template_dir / "prompts"
        if not source_prompts.exists():
            return None

        target_prompts = self.workspace_dir / "prompts"

        updated = 0
        preserved = 0
        errors = 0

        for source_file in source_prompts.rglob("*"):
            if source_file.is_dir():
                continue

            rel_path = source_file.relative_to(source_prompts)
            target_file = target_prompts / rel_path

            if target_file.exists():
                # Compare mtimes
                try:
                    if source_file.stat().st_mtime <= target_file.stat().st_mtime:
                        preserved += 1
                        continue
                except Exception:
                    pass

            if dry_run:
                updated += 1
            else:
                try:
                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source_file, target_file)
                    updated += 1
                except Exception as e:
                    logger.error(f"Failed to copy {rel_path}: {e}")
                    errors += 1

        if updated == 0 and preserved == 0 and errors == 0:
            return {"status": "skipped", "message": "No prompts to update"}

        status_parts = []
        if updated > 0:
            status_parts.append(f"{updated} updated")
        if preserved > 0:
            status_parts.append(f"{preserved} preserved")
        if errors > 0:
            status_parts.append(f"{errors} errors")

        return {
            "status": "updated" if updated > 0 else "skipped",
            "message": ", ".join(status_parts) if status_parts else "No changes",
        }
