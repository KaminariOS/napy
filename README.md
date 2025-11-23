# napy

`napy` is a small command runner that executes shell commands, daemonizes them, logs executions to SQLite, and can notify you via Telegram or email when the command finishes. A minimal config file is created on first run so you can drop in credentials and start receiving alerts. This repo is intentionally a vibe coding project—keep it playful and ship scrappy utilities fast.

## Features

- Runs arbitrary shell commands (`napy <command>`) using your preferred shell.
- Daemonizes each run and writes a PID file under `$XDG_CONFIG_HOME/napy/` (or `~/.config/napy/`).
- Logs start/end timestamps and exit codes to a SQLite database at `~/.config/napy/commands.db`.
- Optional notifications: Telegram bot messages and/or HTML email summaries, including captured stdout/stderr.
- Ships with a ready-to-edit `config.toml` template and generates one automatically if missing.

## Install

Requirements: Python 3.13+ and [`uv`](https://docs.astral.sh/uv/) (for isolated installs).

```sh
# from the repo root
uv tool install .

# or run without installing
uv run napy --help
```

## Configure

On first run, `napy` will create `$XDG_CONFIG_HOME/napy/config.toml` (defaults to `~/.config/napy/config.toml`) and exit so you can fill in values. You can also copy the checked-in example:

```sh
mkdir -p ~/.config/napy
cp config.toml.example ~/.config/napy/config.toml
```

Key settings:
- `shell`: optional override for the shell used to execute commands (defaults to `$SHELL` or `/bin/sh`).
- `telegram.api_key` / `telegram.chat_id`: enable Telegram notifications when both are set.
- `email.smtp_host`, `smtp_user`, `smtp_pass`, `sender`, `recipient`: enable HTML email notifications when present.

## Usage

Run any command through `napy` (it will daemonize, log, and notify):

```sh
napy "python long_script.py --flag"
napy "rsync -av ~/src project.example.com:/var/backups"
napy "systemctl restart my-service"
```

Behavior at a glance:
- Stores execution history in `~/.config/napy/commands.db`.
- Sends Telegram/email summaries if configured; messages include duration, exit status, and captured output.
- Uses the shell specified in config (or `$SHELL` / `/bin/sh` fallback).

## Development

- Project metadata and script entry point live in `pyproject.toml` (`napy = "napy:main_entry_point"`).
- Core logic: command dispatch in `src/napy/__init__.py`, daemon + logging in `src/napy/run_in_shell.py`, notifications in `src/napy/notifications.py`, and SQLite storage in `src/napy/database.py`.
- Dependencies are pinned in `uv.lock`; use `uv sync` for a dev environment and `uv run` to execute locally.
