# pjecz-coma-berenices-cli-typer

CLI tool for voice-to-text tasks. Python 3.14 required (alpha/beta — install via uv). Entry point: `main.py` → `pjecz_coma_berenices_cli_typer.app`.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate && uv sync && uv tool install --python 'https://github.com/astral-sh/uv/releases/latest/download/uv-python-x86_64-unknown-linux-gnu.tar.gz' 2>&1 | head -50
```

Or via pip (slower, still works):

```bash
pip install .[dev] .[lint]
```

## Run the CLI

```bash
# After venv setup or if you've done it above with --python:
.venv/bin/python main.py --help
```

## Commands to know

| Use case | Command |
|---|---|
| Check test pass on main branch | `uv run python -m pytest tests/` |
| Run linter locally (with mypy strict mode for full coverage) | `uvx pip install .[dev] && uv run pre-commit run --all-files` |
| Install latest commit and skip dev deps via conda + pip | `conda create -n pjec --yes && source activate pjec && uv sync --reinstall all 2>&1 | head -30 | tee /tmp/pjec-log.txt; cat /tmp/pjec-log.txt; echo` |
| Verify env config is fine | `python3 main.py --version || python3 main.py --help && echo 'CLI loaded OK'` (expected output when running against the typer Typer instance that imports from pjecz_coma_berenices_cli_typer.app) |

## Notes / gotchas

- **Python 3.14** is needed; this isn't typical for most projects, so verify your version first before proceeding further — otherwise you'll hit import errors.
- If something doesn't work right off the bat because of missing Python packages in venv, just re-install them with `uv sync` or reinstall the latest version of uv from GitHub releases directly via `uv tool install --python ...`.
- The test directory uses pytest with mypy strict mode enabled by default — don't forget to activate both before running tests unless you explicitly want to skip type-checking.

## Conventions (not standard in most projects)

- Tests live on this branch but aren't checked into git because of CI overhead and they're excluded from coverage reports (`exclude = ["**/tests"]`).
- No `pyright`/mypy needed separately — basedpyright handles everything including strict mode by default once you install it via conda-forge or uv.
- For new projects using typer, skip the mypy step unless you want to enforce stricter typing than basic Python gives you — just use standard pip + uv instead.
