#!/usr/bin/env python3
"""Naukri Resume Update Automation Entrypoint.

Provides CLI command execution for automated resume updates and local
preview tests across single or multiple Naukri accounts.
"""

import argparse
from pathlib import Path
from typing import Optional

from src.config import Config, load_config
from src.constants import SUPPORTED_RENAME_MODES
from src.file_utils import cleanup_temp_file, create_renamed_resume
from src.naukri_client import NaukriClient

PROJECT_DIR = Path(__file__).resolve().parent


def test_rename(config: Config, target_account: Optional[str] = None) -> None:
    """Tests resume renaming logic locally for configured accounts without launching a browser."""
    client = NaukriClient(config)
    accounts = client.filter_accounts(target_account)

    if not accounts:
        print(f"\n[ERROR] No matching account found for '{target_account}'.")
        return

    print("\n" + "=" * 65)
    print("           TESTING RESUME RENAMING FOR ACCOUNTS")
    print("=" * 65)

    for idx, account in enumerate(accounts, start=1):
        print(f"\nAccount [{idx}/{len(accounts)}]: {account.name} ({account.email})")
        print("-" * 55)
        resume_path = account.resume_path
        active_mode = account.rename_mode or config.rename_mode

        if not resume_path or not resume_path.is_file():
            config.temp_dir.mkdir(parents=True, exist_ok=True)
            demo_file = config.temp_dir / f"Sample_Resume_{idx}.pdf"
            demo_file.touch()
            resume_path = demo_file
            print(
                f"[NOTE] Valid resume file not found. "
                f"Using mock file: {demo_file.name}"
            )

        print(f"Original File : {resume_path.name}")
        print(f"Active Mode   : {active_mode}")

        for mode in SUPPORTED_RENAME_MODES:
            result = create_renamed_resume(
                original_path=resume_path,
                mode=mode,
                temp_dir=config.temp_dir,
            )
            is_active = mode == active_mode
            marker = " <-- (ACTIVE MODE)" if is_active else ""
            print(f"  [{mode.ljust(10)}] -> {result.name}{marker}")

            if not config.keep_renamed_copy:
                cleanup_temp_file(result)

    print("\n" + "=" * 65 + "\n")


def main() -> None:
    """Main CLI entrypoint for argument parsing and runner dispatch."""
    parser = argparse.ArgumentParser(
        description="Automate Naukri Resume Updates for Multiple Accounts"
    )
    parser.add_argument(
        "--test-rename",
        action="store_true",
        help="Test resume renaming logic without logging into Naukri",
    )
    parser.add_argument(
        "--account",
        type=str,
        default=None,
        help="Target a specific account by 1-based index (e.g. 1, 2) or name/email substring",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=SUPPORTED_RENAME_MODES,
        help="Override the renaming mode (e.g. date_time, date_first)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run Chrome in headless mode",
    )

    args = parser.parse_args()

    # Load configuration (.env / accounts.json with CLI overrides)
    override_headless = True if args.headless else None
    config = load_config(
        project_dir=PROJECT_DIR,
        override_headless=override_headless,
        override_mode=args.mode,
    )

    if args.test_rename:
        test_rename(config, target_account=args.account)
        return

    client = NaukriClient(config)
    client.run(target_account=args.account)


if __name__ == "__main__":
    main()
