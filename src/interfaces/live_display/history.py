"""Command history for LiveDisplay."""

from pathlib import Path


class History:
    """Command history with file persistence."""

    def __init__(self, filepath: str | None = None) -> None:
        self.filepath: Path | None = Path(filepath).expanduser() if filepath else None
        self.entries: list[str] = []
        self.index: int = -1
        self._original_input: str = ""
        self._load()

    def _load(self) -> None:
        if self.filepath and self.filepath.exists():
            self.entries = self.filepath.read_text().splitlines()

    def _save(self) -> None:
        if self.filepath:
            self.filepath.write_text("\n".join(self.entries[-1000:]))

    def add(self, command: str) -> None:
        if command.strip():
            self.entries.append(command)
            self._save()
        self.index = -1
        self._original_input = ""

    def up(self, current: str) -> str:
        if not self.entries:
            return current
        if self.index == -1:
            self._original_input = current
            self.index = len(self.entries) - 1
        elif self.index > 0:
            self.index -= 1
        return self.entries[self.index]

    def down(self, current: str) -> str:
        if self.index == -1:
            return current
        if self.index < len(self.entries) - 1:
            self.index += 1
            return self.entries[self.index]
        else:
            self.index = -1
            result = self._original_input
            self._original_input = ""
            return result
