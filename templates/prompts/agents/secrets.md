## Secrets and Authentication

Any command needing secrets must use `uv run dotenv`:

```bash
uv run dotenv gh pr create --title "..." --body "..."
uv run dotenv python script_using_api.py
```

**Wrong:**
```bash
gh pr create --title "..."                    # No ALFRED_REPO_PAT
source .env && gh pr create                   # Pollutes shell
export $(cat .env | grep ALFRED_REPO_PAT) && ...  # Pollutes shell
```
