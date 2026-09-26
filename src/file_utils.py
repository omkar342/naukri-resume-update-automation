"""File management utilities for resume processing.

Includes stem cleaning, date/timestamp formatting, and temporary
file lifecycle management.
"""

import re
import shutil
from datetime import datetime
from pathlib import Path


def clean_resume_stem(stem: str) -> str:
    """Removes prior dates or timestamp suffixes from the filename stem.

    Prevents accumulating multiple dates if the file was previously saved
    with date strings (e.g. 'Omkar_Resume_(25-09-2026)' -> 'Omkar_Resume').
    """
    # Remove patterns like _(25-09-2026), _25-09-2026, _2026-09-25
    cleaned = re.sub(
        r"[_ -]*\(?\d{2,4}[-_/]\d{2}[-_/]\d{2,4}\)?",
        "",
        stem,
    )
    # Remove trailing 6+ digit timestamps like _203512
    cleaned = re.sub(r"[_ -]*\d{6,}$", "", cleaned)
    cleaned = cleaned.strip("_- ")
    return cleaned or stem


def create_renamed_resume(
    original_path: Path,
    mode: str,
    temp_dir: Path,
) -> Path:
    """Creates a temporary copy of the resume formatted with date/timestamp.

    Leaves the original master resume file untouched.
    """
    if not original_path.is_file():
        raise FileNotFoundError(f"Resume file not found at: {original_path}")

    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H%M%S")
    unix_ts = int(now.timestamp())
    stem = clean_resume_stem(original_path.stem)
    ext = original_path.suffix

    if mode == "date_first":
        # Today's date first -> 2026-09-26_Resume_055012.pdf
        new_filename = f"{today_str}_{stem}_{time_str}{ext}"
    elif mode == "timestamp":
        # Unix timestamp -> Resume_1727276712.pdf
        new_filename = f"{stem}_{unix_ts}{ext}"
    elif mode == "date_only":
        # Today's date only -> Resume_2026-09-26.pdf
        new_filename = f"{stem}_{today_str}{ext}"
    else:
        # Default 'date_time': Name first -> Resume_2026-09-26_055012.pdf
        new_filename = f"{stem}_{today_str}_{time_str}{ext}"

    temp_dir.mkdir(parents=True, exist_ok=True)
    destination = temp_dir / new_filename
    shutil.copy2(original_path, destination)
    return destination


def cleanup_temp_file(file_path: Path) -> bool:
    """Safely deletes a temporary file if it exists."""
    if file_path and file_path.exists():
        try:
            file_path.unlink()
            print(f"[INFO] Cleaned up temporary copy: {file_path.name}")
            return True
        except OSError as err:
            print(f"[WARN] Could not remove temporary file: {err}")
    return False
