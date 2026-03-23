#!/usr/bin/env python3
"""Shared helpers used by WF1/WF2/WF3 scripts."""

import logging
import os
from pathlib import Path


logger = logging.getLogger(__name__)


class LLMQuotaExceededError(Exception):
    """Raised when the provider returns HTTP 429 / quota exhausted."""


def load_env_file(path: Path) -> None:
    """Load KEY=VALUE pairs from a .env file without overriding existing env vars."""
    if not path.exists() or not path.is_file():
        return

    try:
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
    except OSError as exc:
        logger.warning(f"Could not read env file {path}: {exc}")


def bootstrap_env(script_file: str) -> None:
    """Load .env from CWD and script directory (if different)."""
    cwd_env = Path.cwd() / ".env"
    script_env = Path(script_file).resolve().parent / ".env"
    load_env_file(cwd_env)
    if script_env != cwd_env:
        load_env_file(script_env)


def resolve_api_key() -> str:
    """Resolve API key from common environment variable names."""
    return os.getenv("MEGALLM_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
