"""Configuration manager and environment parser.

Handles loading settings from .env (with fallback to .env.example) and accounts.json,
validating required credentials across multiple accounts, and path resolution.
"""

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

from src.constants import (
    ACCOUNTS_FILE_NAME,
    DEFAULT_RENAME_MODE,
    DELAY_BETWEEN_ACCOUNTS_DEFAULT,
    ENV_EXAMPLE_NAME,
    ENV_FILE_NAME,
    LOGIN_TIMEOUT_DEFAULT,
    SUPPORTED_RENAME_MODES,
    TEMP_DIR_NAME,
)


@dataclass
class AccountConfig:
    """Dataclass holding settings and credentials for a single Naukri account."""

    name: str
    email: str
    password: str
    resume_path: Path
    rename_mode: Optional[str] = None

    def is_placeholder(self) -> bool:
        """Checks if account uses template placeholders."""
        low_email = (self.email or "").strip().lower()
        low_pass = (self.password or "").strip().lower()
        if (
            not low_email
            or "example.com" in low_email
            or "placeholder" in low_email
            or low_email.startswith("your_")
            or "your_second_email" in low_email
        ):
            return True
        if (
            not low_pass
            or low_pass in (
                "your_naukri_password",
                "your_second_password",
                "enter_second_password_here",
            )
            or "placeholder" in low_pass
            or low_pass.startswith("your_")
        ):
            return True
        return False

    def validate(self) -> List[str]:
        """Validates individual account credentials and resume path."""
        errors: List[str] = []

        if not self.email or self.is_placeholder():
            errors.append(
                f"Account '{self.name}': NAUKRI_EMAIL is missing or using placeholder ({self.email})."
            )
        elif not self.password:
            errors.append(
                f"Account '{self.name}': NAUKRI_PASSWORD is missing."
            )
        if not str(self.resume_path) or str(self.resume_path) == ".":
            errors.append(
                f"Account '{self.name}': RESUME_PATH is missing or not configured."
            )
        elif self.resume_path.is_dir():
            errors.append(
                f"Account '{self.name}': No PDF resume files found in directory: {self.resume_path}"
            )
        elif not self.resume_path.is_file():
            errors.append(
                f"Account '{self.name}': Resume file not found at: {self.resume_path}"
            )

        if self.rename_mode and self.rename_mode not in SUPPORTED_RENAME_MODES:
            errors.append(
                f"Account '{self.name}': Unsupported rename mode '{self.rename_mode}'. "
                f"Choose from: {', '.join(SUPPORTED_RENAME_MODES)}"
            )

        return errors


@dataclass
class Config:
    """Dataclass holding all runtime application settings."""

    project_dir: Path
    temp_dir: Path
    accounts: List[AccountConfig]
    rename_mode: str
    headless: bool
    keep_renamed_copy: bool
    login_timeout: int
    delay_between_accounts: int = DELAY_BETWEEN_ACCOUNTS_DEFAULT

    @property
    def email(self) -> str:
        """Backward-compatible access to primary account email."""
        return self.accounts[0].email if self.accounts else ""

    @property
    def password(self) -> str:
        """Backward-compatible access to primary account password."""
        return self.accounts[0].password if self.accounts else ""

    @property
    def resume_path(self) -> Path:
        """Backward-compatible access to primary account resume path."""
        return self.accounts[0].resume_path if self.accounts else Path()

    def validate(self) -> List[str]:
        """Validates configuration parameters and ensures at least one valid account."""
        errors: List[str] = []

        if not self.accounts:
            errors.append(
                "No accounts configured. Please provide account credentials in .env or accounts.json."
            )
        else:
            # Check if all accounts have errors
            all_errors = [acc.validate() for acc in self.accounts]
            if all(bool(errs) for errs in all_errors):
                # Every single account is invalid - cannot proceed
                for errs in all_errors:
                    errors.extend(errs)

        if self.rename_mode not in SUPPORTED_RENAME_MODES:
            errors.append(
                f"Unsupported global RESUME_RENAME_MODE '{self.rename_mode}'. "
                f"Choose from: {', '.join(SUPPORTED_RENAME_MODES)}"
            )

        return errors



def get_latest_pdf(directory: Path) -> Optional[Path]:
    """Finds the most recently modified PDF file in the given directory."""
    if not directory.is_dir():
        return None
    pdf_files = [f for f in directory.glob("*.pdf") if f.is_file()]
    if not pdf_files:
        return None
    return max(pdf_files, key=lambda f: f.stat().st_mtime)


def resolve_resume_path(path_str: str, project_dir: Path) -> Path:
    """Resolves path string handling quotes, tilde, and relative paths.

    Supports direct file paths, directory paths (picks the newest PDF),
    and falls back to the newest PDF in the folder if an explicitly
    configured dated filename is missing.
    """
    if not path_str:
        return Path()
    cleaned = path_str.strip().strip('"').strip("'")
    expanded = os.path.expanduser(cleaned)
    resolved = Path(expanded)
    if not resolved.is_absolute():
        resolved = (project_dir / resolved).resolve()

    # Direct existing file
    if resolved.is_file():
        return resolved

    # Directory specified: pick the latest modified PDF
    if resolved.is_dir():
        latest = get_latest_pdf(resolved)
        if latest:
            return latest

    # If the configured file no longer exists, but the parent directory contains PDFs,
    # fallback to the latest modified PDF in that directory
    if not resolved.exists() and resolved.parent.is_dir():
        latest = get_latest_pdf(resolved.parent)
        if latest:
            print(
                f"[INFO] Configured resume '{resolved.name}' not found. "
                f"Auto-selected latest PDF: '{latest.name}'"
            )
            return latest

    return resolved


def load_accounts(
    project_dir: Path,
    default_resume_path: Path,
) -> List[AccountConfig]:
    """Loads accounts from accounts.json and/or .env with multi-account support."""
    accounts: List[AccountConfig] = []
    seen_emails = set()

    # 1. Attempt loading from accounts.json (or custom path from ACCOUNTS_FILE)
    accounts_file_env = os.getenv("ACCOUNTS_FILE", "").strip()
    accounts_file = (
        Path(os.path.expanduser(accounts_file_env))
        if accounts_file_env
        else project_dir / ACCOUNTS_FILE_NAME
    )
    if not accounts_file.is_absolute():
        accounts_file = (project_dir / accounts_file).resolve()

    if accounts_file.is_file():
        try:
            with open(accounts_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                for idx, item in enumerate(data, start=1):
                    if not isinstance(item, dict):
                        continue
                    email = str(item.get("email", "")).strip()
                    password = str(item.get("password", "")).strip()
                    raw_resume = str(item.get("resume_path", "")).strip()
                    name = str(item.get("name", "")).strip() or f"Account {idx}"
                    account_rename_mode = item.get("rename_mode")
                    if account_rename_mode:
                        account_rename_mode = str(account_rename_mode).strip().lower()

                    if raw_resume:
                        resume_path = resolve_resume_path(raw_resume, project_dir)
                    else:
                        resume_path = default_resume_path

                    if email and email.lower() not in seen_emails:
                        accounts.append(
                            AccountConfig(
                                name=name,
                                email=email,
                                password=password,
                                resume_path=resume_path,
                                rename_mode=account_rename_mode,
                            )
                        )
                        seen_emails.add(email.lower())
        except Exception as err:
            print(f"[WARN] Failed to parse accounts file '{accounts_file}': {err}")

    # 2. Parse indexed environment variables: NAUKRI_EMAIL_1, ACCOUNT_1_EMAIL, etc.
    found_indices = set()
    for key in os.environ:
        m = re.match(r"^(?:NAUKRI_EMAIL_|ACCOUNT_)(\d+)(?:_EMAIL)?$", key, re.IGNORECASE)
        if m:
            try:
                found_indices.add(int(m.group(1)))
            except ValueError:
                pass

    for idx in sorted(found_indices):
        email = (
            os.getenv(f"NAUKRI_EMAIL_{idx}")
            or os.getenv(f"ACCOUNT_{idx}_EMAIL")
            or ""
        ).strip()
        password = (
            os.getenv(f"NAUKRI_PASSWORD_{idx}")
            or os.getenv(f"ACCOUNT_{idx}_PASSWORD")
            or ""
        ).strip()
        raw_resume = (
            os.getenv(f"RESUME_PATH_{idx}")
            or os.getenv(f"ACCOUNT_{idx}_RESUME_PATH")
            or ""
        ).strip()
        name = (
            os.getenv(f"NAUKRI_NAME_{idx}")
            or os.getenv(f"ACCOUNT_{idx}_NAME")
            or f"Account {idx}"
        ).strip()
        acc_rename_mode = (
            os.getenv(f"RESUME_RENAME_MODE_{idx}")
            or os.getenv(f"ACCOUNT_{idx}_RENAME_MODE")
            or None
        )
        if acc_rename_mode:
            acc_rename_mode = acc_rename_mode.strip().lower()

        if raw_resume:
            resume_path = resolve_resume_path(raw_resume, project_dir)
        else:
            resume_path = default_resume_path

        if email and email.lower() not in seen_emails:
            accounts.append(
                AccountConfig(
                    name=name,
                    email=email,
                    password=password,
                    resume_path=resume_path,
                    rename_mode=acc_rename_mode,
                )
            )
            seen_emails.add(email.lower())

    # 3. Check legacy/primary NAUKRI_EMAIL if Account 1 was not already defined
    has_account_1 = (1 in found_indices) or (bool(accounts) and accounts_file.is_file())
    if not has_account_1:
        legacy_email = os.getenv("NAUKRI_EMAIL", "").strip()
        if legacy_email and legacy_email.lower() not in seen_emails:
            legacy_password = os.getenv("NAUKRI_PASSWORD", "").strip()
            legacy_name = os.getenv("NAUKRI_NAME", "Primary Account").strip()
            accounts.insert(
                0,
                AccountConfig(
                    name=legacy_name,
                    email=legacy_email,
                    password=legacy_password,
                    resume_path=default_resume_path,
                    rename_mode=None,
                ),
            )
            seen_emails.add(legacy_email.lower())

    # Filter out placeholder accounts if at least one real configured account exists
    real_accounts = [acc for acc in accounts if not acc.is_placeholder()]
    if real_accounts:
        for placeholder_acc in [acc for acc in accounts if acc.is_placeholder()]:
            print(
                f"[INFO] Skipping placeholder account '{placeholder_acc.name}' "
                f"({placeholder_acc.email}) until real credentials are provided in .env."
            )
        return real_accounts

    return accounts




def load_config(
    project_dir: Path,
    override_headless: Optional[bool] = None,
    override_mode: Optional[str] = None,
) -> Config:
    """Loads configuration from environment variables, accounts.json, and CLI overrides."""
    env_file = project_dir / ENV_FILE_NAME
    if env_file.exists():
        load_dotenv(dotenv_path=env_file)
    else:
        load_dotenv(dotenv_path=project_dir / ENV_EXAMPLE_NAME)

    raw_resume_path = os.getenv("RESUME_PATH", "")
    default_resume_path = resolve_resume_path(raw_resume_path, project_dir)

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

    # Delay between consecutive accounts
    delay_raw = os.getenv("DELAY_BETWEEN_ACCOUNTS", str(DELAY_BETWEEN_ACCOUNTS_DEFAULT))
    try:
        delay_between_accounts = int(delay_raw.strip())
    except ValueError:
        delay_between_accounts = DELAY_BETWEEN_ACCOUNTS_DEFAULT

    temp_dir = project_dir / TEMP_DIR_NAME

    # Load all accounts
    accounts = load_accounts(project_dir, default_resume_path)

    return Config(
        project_dir=project_dir,
        temp_dir=temp_dir,
        accounts=accounts,
        rename_mode=rename_mode,
        headless=headless,
        keep_renamed_copy=keep_renamed_copy,
        login_timeout=login_timeout,
        delay_between_accounts=delay_between_accounts,
    )
