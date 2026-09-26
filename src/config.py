"""Configuration manager and environment parser.

Handles loading settings from .env (with fallback to .env.example),
validating required credentials, and path resolution.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

from src.constants import (
    DEFAULT_RENAME_MODE,
    ENV_EXAMPLE_NAME,
    ENV_FILE_NAME,
    LOGIN_TIMEOUT_DEFAULT,
    SUPPORTED_RENAME_MODES,
    TEMP_DIR_NAME,
)


@dataclass
class Config:
    """Dataclass holding all runtime application settings."""

    project_dir: Path
    temp_dir: Path
    email: str
    password: str
    resume_path: Path
    rename_mode: str
    headless: bool
    keep_renamed_copy: bool
    login_timeout: int

    def validate(self) -> List[str]:
        """Validates configuration parameters and returns error messages."""
        errors: List[str] = []

        if not self.email or self.email == "your_email@example.com":
            errors.append(
                "NAUKRI_EMAIL is missing or using placeholder in .env file."
            )
        if not self.password or self.password == "your_naukri_password":
            errors.append(
                "NAUKRI_PASSWORD is missing or using placeholder in .env file."
            )
        if not str(self.resume_path) or str(self.resume_path) == ".":
            errors.append(
                "RESUME_PATH is missing or using placeholder in .env file."
            )
        elif not self.resume_path.is_file():
            errors.append(f"Resume file not found at: {self.resume_path}")

        if self.rename_mode not in SUPPORTED_RENAME_MODES:
            errors.append(
                f"Unsupported RESUME_RENAME_MODE '{self.rename_mode}'. "
                f"Choose from: {', '.join(SUPPORTED_RENAME_MODES)}"
            )

        return errors


def resolve_resume_path(path_str: str, project_dir: Path) -> Path:
    """Resolves path string handling quotes, tilde, and relative paths."""
    if not path_str:
        return Path()
    cleaned = path_str.strip().strip('"').strip("'")
    expanded = os.path.expanduser(cleaned)
    resolved = Path(expanded)
    if not resolved.is_absolute():
        resolved = (project_dir / resolved).resolve()
    return resolved


def load_config(
    project_dir: Path,
    override_headless: Optional[bool] = None,
    override_mode: Optional[str] = None,
) -> Config:
    """Loads configuration from environment variables and CLI overrides."""
    env_file = project_dir / ENV_FILE_NAME
    if env_file.exists():
        load_dotenv(dotenv_path=env_file)
    else:
        load_dotenv(dotenv_path=project_dir / ENV_EXAMPLE_NAME)

    email = os.getenv("NAUKRI_EMAIL", "").strip()
    password = os.getenv("NAUKRI_PASSWORD", "").strip()
    raw_resume_path = os.getenv("RESUME_PATH", "")
    resume_path = resolve_resume_path(raw_resume_path, project_dir)

    # Rename mode with CLI override priority
    env_mode = os.getenv("RESUME_RENAME_MODE", DEFAULT_RENAME_MODE)
    rename_mode = (override_mode or env_mode).strip().lower()

    # Headless mode with CLI override priority
    env_headless_raw = os.getenv("HEADLESS", "false").strip().lower()
    env_headless = env_headless_raw in ("true", "1", "yes")
    headless = (
        override_headless
        if override_headless is not None
        else env_headless
    )

    keep_raw = os.getenv("KEEP_RENAMED_COPY", "false").strip().lower()
    keep_renamed_copy = keep_raw in ("true", "1", "yes")

    # Configurable login timeout from .env with fallback to constants
    timeout_raw = os.getenv("LOGIN_TIMEOUT", str(LOGIN_TIMEOUT_DEFAULT))
    try:
        login_timeout = int(timeout_raw.strip())
    except ValueError:
        login_timeout = LOGIN_TIMEOUT_DEFAULT

    temp_dir = project_dir / TEMP_DIR_NAME

    return Config(
        project_dir=project_dir,
        temp_dir=temp_dir,
        email=email,
        password=password,
        resume_path=resume_path,
        rename_mode=rename_mode,
        headless=headless,
        keep_renamed_copy=keep_renamed_copy,
        login_timeout=login_timeout,
    )
