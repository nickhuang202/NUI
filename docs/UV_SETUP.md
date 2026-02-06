# UV Project Setup

This document describes how to manage this project with uv.

## Prerequisites

- Install uv (see https://docs.astral.sh/uv/ for the latest install steps).
- Ensure uv is on your PATH (restart your shell or `source ~/.local/bin/env`).

## Initialize the project

Run these commands from the repo root:

```bash
uv init
```

This will create a `pyproject.toml` and uv metadata files in the project root.

## Create a virtual environment

```bash
uv venv
```

If `.venv` already exists, either keep it or recreate it:

```bash
uv venv --clear
```

## Install dependencies

This project already has a `requirements.txt`. Use uv to install them:

```bash
uv pip install -r requirements.txt
```

## Lock dependencies

Generate a lockfile from `requirements.txt`:

```bash
uv pip compile requirements.txt -o requirements.lock
```

Sync the environment to the lockfile:

```bash
uv pip sync requirements.lock
```

## Run tests

```bash
uv run pytest -m "not hardware"
```

## Run the app

```bash
uv run python app.py
```

## Notes

- If you add new dependencies, prefer uv commands so the project stays uv-managed.
- Keep `requirements.lock` committed so CI runs the same versions.
