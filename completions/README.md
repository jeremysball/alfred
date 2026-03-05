# Alfred Shell Completions

Fast static shell completions for Alfred - **1ms** vs **200ms** for dynamic completion.

## Installation

### Bash

```bash
# User-local installation (recommended)
mkdir -p ~/.config/bash_completion
cp /path/to/alfred/completions/alfred.bash ~/.config/bash_completion/alfred

# Add to your ~/.bashrc:
[ -f ~/.config/bash_completion/alfred ] && source ~/.config/bash_completion/alfred
```

### Fish

```bash
# User-local installation
mkdir -p ~/.config/fish/completions
cp /path/to/alfred/completions/alfred.fish ~/.config/fish/completions/alfred.fish
```

### Zsh

```bash
# User-local installation
mkdir -p ~/.zsh/completions
cp /path/to/alfred/completions/_alfred ~/.zsh/completions/

# Add to your ~/.zshrc (if not already present):
fpath+=~/.zsh/completions
autoload -U compinit && compinit
```

## What's Included

These completions cover:
- **Top-level commands**: `cron`, `memory`
- **Cron subcommands**: `list`, `submit`, `review`, `approve`, `reject`, `history`, `start`, `stop`, `status`, `reload`
- **Memory subcommands**: `migrate`, `status`, `prune`

**Note**: Session names are not auto-completed statically. Use `/list` and `/resume <name>` inside the TUI, or type partial names - the TUI will fuzzy-match.

## Why Static?

The default Typer completions call Python on every TAB press:
- **Dynamic**: ~200ms per completion (imports typer, rich, builds app)
- **Static**: ~1ms per completion (pure shell, no Python startup)

The completions are hardcoded based on the current CLI structure. If commands change, update these files.

## Regenerating

If you add/modify CLI commands, update the completion files:

1. **alfred.bash**: Update the `case` statement with new commands
2. **alfred.fish**: Add `complete -c alfred` entries for new commands  
3. **_alfred**: Update the `_alfred_cron_cmds` and `_alfred_memory_cmds` functions

Or use the built-in Typer completions during development:
```bash
alfred --show-completion bash  # Dynamic completions (slow but auto-generated)
```
