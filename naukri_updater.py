#!/usr/bin/env python3
"""Naukri Resume Update Automation Entrypoint.

Provides CLI command execution for automated resume updates and local
preview tests.
"""

import argparse
from pathlib import Path

from src.config import load_config
from src.constants import SUPPORTED_RENAME_MODES
from src.file_utils import cleanup_temp_file, create_renamed_resume
from src.naukri_client import NaukriClient

PROJECT_DIR = Path(__file__).resolve().parent


def test_rename(config) -> None:
    """Tests resume renaming logic locally without launching a browser."""
    print("\n--- Testing Resume Renaming Feature ---")
    resume_path = config.resume_path

    if not resume_path or not resume_path.is_file():
        # Create a mock resume file in temp_resumes for demonstration
        config.temp_dir.mkdir(parents=True, exist_ok=True)
        demo_file = config.temp_dir / "Sample_Resume.pdf"
        demo_file.touch()
        resume_path = demo_file
        print(
            f"[NOTE] Valid resume file not found. "
            f"Using mock file: {demo_file.name}"
        )

    print(f"Original File : {resume_path.name}")
    print(f"Selected Mode : {config.rename_mode}")

    for mode in SUPPORTED_RENAME_MODES:
        result = create_renamed_resume(
            original_path=resume_path,
            mode=mode,
            temp_dir=config.temp_dir,
        )
        is_active = mode == config.rename_mode
        marker = " <-- (ACTIVE MODE)" if is_active else ""
        print(f"  [{mode.ljust(10)}] -> {result.name}{marker}")

        if not config.keep_renamed_copy:
            cleanup_temp_file(result)

    print("---------------------------------------\n")


def main() -> None:
    """Main CLI entrypoint for argument parsing and runner dispatch."""
    parser = argparse.ArgumentParser(
        description="Automate Naukri Resume Updates with Date/Time Renaming"
    )
    parser.add_argument(
        "--test-rename",
        action="store_true",
        help="Test the resume renaming logic without logging into Naukri",
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

    # Load configuration (.env with CLI overrides)
    override_headless = True if args.headless else None
    config = load_config(
        project_dir=PROJECT_DIR,
        override_headless=override_headless,
        override_mode=args.mode,
    )

    if args.test_rename:
        test_rename(config)
        return

    client = NaukriClient(config)
    client.run()


if __name__ == "__main__":
    main()
