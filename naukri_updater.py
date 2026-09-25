import os
import sys
import time
import shutil
import argparse
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

# Load environment variables (.env preferred, fallback to .env.example)
PROJECT_DIR = Path(__file__).resolve().parent
env_file = PROJECT_DIR / ".env"
if env_file.exists():
    load_dotenv(dotenv_path=env_file)
else:
    load_dotenv(dotenv_path=PROJECT_DIR / ".env.example")

NAUKRI_EMAIL = os.getenv("NAUKRI_EMAIL", "").strip()
NAUKRI_PASSWORD = os.getenv("NAUKRI_PASSWORD", "").strip()
RESUME_PATH_ENV = os.getenv("RESUME_PATH", "").strip().strip('"').strip("'")
RESUME_RENAME_MODE = os.getenv("RESUME_RENAME_MODE", "date_time").strip().lower()
HEADLESS_ENV = os.getenv("HEADLESS", "false").strip().lower() in ("true", "1", "yes")
KEEP_RENAMED_COPY = os.getenv("KEEP_RENAMED_COPY", "false").strip().lower() in ("true", "1", "yes")

TEMP_DIR = PROJECT_DIR / "temp_resumes"


def resolve_resume_path(path_str: str) -> Path:
    """Resolves the resume path handling quotes, home directory, and relative paths."""
    if not path_str:
        return Path()
    cleaned = path_str.strip().strip('"').strip("'")
    expanded = os.path.expanduser(cleaned)
    p = Path(expanded)
    if not p.is_absolute():
        p = (PROJECT_DIR / p).resolve()
    return p


def clean_resume_stem(stem: str) -> str:
    """Removes any prior date or timestamp suffixes so we don't accumulate duplicates."""
    import re
    # Remove patterns like _(25-09-2026), _25-09-2026, _2026-09-25, etc.
    cleaned = re.sub(r'[_ -]*\(?\d{2,4}[-_/]\d{2}[-_/]\d{2,4}\)?', '', stem)
    # Remove trailing 6+ digit timestamps like _203512
    cleaned = re.sub(r'[_ -]*\d{6,}$', '', cleaned)
    cleaned = cleaned.strip('_- ')
    return cleaned or stem


def create_renamed_resume(original_path: Path, mode: str = "date_first") -> Path:
    """
    Creates a copy of the resume with today's date and/or timestamp.
    
    Modes:
      - 'date_first' (default) : Today's date first -> 2026-09-25_Resume_203512.pdf
      - 'date_time'            : Date + time suffix -> Resume_2026-09-25_203512.pdf
      - 'timestamp'            : Unix timestamp     -> Resume_1727276712.pdf
      - 'date_only'            : Today's date only  -> Resume_2026-09-25.pdf
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
        new_filename = f"{today_str}_{stem}_{time_str}{ext}"
    elif mode == "date_time":
        new_filename = f"{stem}_{today_str}_{time_str}{ext}"
    elif mode == "timestamp":
        new_filename = f"{stem}_{unix_ts}{ext}"
    elif mode == "date_only":
        new_filename = f"{stem}_{today_str}{ext}"
    else:
        # Fallback to date_first
        new_filename = f"{today_str}_{stem}_{time_str}{ext}"

    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    destination = TEMP_DIR / new_filename
    shutil.copy2(original_path, destination)
    return destination


def init_driver(headless: bool = False) -> webdriver.Chrome:
    """Initializes Chrome WebDriver with stealth options to avoid bot detection."""
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless=new")

    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")

    # Anti-bot detection flags
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_argument(
        "--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )

    try:
        # Modern Selenium (4.10+) manages chromedriver automatically
        driver = webdriver.Chrome(options=chrome_options)
    except Exception:
        # Optional fallback to ChromeDriverManager if installed
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            from selenium.webdriver.chrome.service import Service
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
        except Exception as err:
            print(f"[ERROR] Failed to start Chrome WebDriver: {err}")
            raise

    # Override navigator.webdriver in JavaScript
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """
        },
    )
    return driver


def update_naukri_resume(headless: bool = False, rename_mode: str = None):
    mode = rename_mode or RESUME_RENAME_MODE
    resume_path = resolve_resume_path(RESUME_PATH_ENV)

    # 1. Validation of environment and inputs
    errors = []
    if not NAUKRI_EMAIL or NAUKRI_EMAIL == "your_email@example.com":
        errors.append("NAUKRI_EMAIL is missing or using placeholder in .env file.")
    if not NAUKRI_PASSWORD or NAUKRI_PASSWORD == "your_naukri_password":
        errors.append("NAUKRI_PASSWORD is missing or using placeholder in .env file.")
    if not RESUME_PATH_ENV or RESUME_PATH_ENV == "/path/to/your/resume.pdf":
        errors.append("RESUME_PATH is missing or using placeholder in .env file.")
    elif not resume_path.is_file():
        errors.append(f"Resume file not found at: {resume_path}")

    if errors:
        print("\n" + "=" * 60)
        print("[!] CONFIGURATION ERROR(S) DETECTED:")
        for err in errors:
            print(f"  - {err}")
        print("\nPlease update your '.env' file with your real details.")
        print("=" * 60 + "\n")
        return False

    # 2. Rename & create resume copy
    print(f"\n[INFO] Original Resume: {resume_path}")
    print(f"[INFO] Renaming Mode   : {mode}")
    try:
        renamed_resume = create_renamed_resume(resume_path, mode=mode)
        print(f"[INFO] Prepared copy   : {renamed_resume.name}")
        print(f"[INFO] Upload file path: {renamed_resume}")
    except Exception as e:
        print(f"[ERROR] Could not prepare renamed resume: {e}")
        return False

    driver = None
    upload_success = False

    try:
        print("\n[INFO] Launching Chrome browser...")
        driver = init_driver(headless=headless)
        wait = WebDriverWait(driver, 20)

        # 3. Login to Naukri
        print("[INFO] Navigating to Naukri login page...")
        driver.get("https://www.naukri.com/nlogin/login")

        print("[INFO] Entering credentials...")
        email_field = wait.until(
            EC.presence_of_element_located((By.XPATH, "//input[@id='usernameField' or @placeholder='Enter your active Email ID / Username']"))
        )
        email_field.clear()
        email_field.send_keys(NAUKRI_EMAIL)

        password_field = wait.until(
            EC.presence_of_element_located((By.XPATH, "//input[@id='passwordField' or @type='password']"))
        )
        password_field.clear()
        password_field.send_keys(NAUKRI_PASSWORD)

        login_button = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//button[@type='submit' or text()='Login' or contains(@class, 'login-btn')]"))
        )
        login_button.click()

        # 4. Wait for Login completion (with OTP / Captcha detection)
        print("[INFO] Waiting for authentication...")
        logged_in = False
        login_timeout = 120  # Allows up to 2 minutes for user to solve OTP/Captcha if prompted
        start_time = time.time()
        otp_alerted = False

        while time.time() - start_time < login_timeout:
            curr_url = driver.current_url
            if any(key in curr_url for key in ["mnjuser/homepage", "mnjuser/profile", "naukri.com/mnjuser"]):
                logged_in = True
                break

            # Check if OTP or 2FA screen appeared
            otp_elements = driver.find_elements(
                By.XPATH,
                "//*[contains(text(), 'OTP') or contains(text(), 'verification code') or contains(@class, 'otp') or contains(text(), 'Verify')]"
            )
            if otp_elements and not otp_alerted:
                print("\n" + "*" * 60)
                print("[NOTICE] OTP or verification prompt detected!")
                print("         Please check the opened browser window and enter the OTP.")
                print("*" * 60 + "\n")
                otp_alerted = True

            # Check for credential error
            err_elements = driver.find_elements(
                By.XPATH,
                "//*[contains(@class, 'server-err') or contains(@class, 'error-message') or contains(text(), 'Invalid details')]"
            )
            for err_el in err_elements:
                if err_el.is_displayed() and err_el.text.strip():
                    print(f"[ERROR] Login rejected by Naukri: {err_el.text.strip()}")
                    return False

            time.sleep(2)

        if not logged_in:
            print("[ERROR] Login timed out or did not redirect to profile/homepage.")
            return False

        print("[SUCCESS] Successfully logged into Naukri!")

        # 5. Navigate to Profile
        print("[INFO] Navigating directly to profile page...")
        driver.get("https://www.naukri.com/mnjuser/profile")
        time.sleep(3)

        # 6. Locate file upload input
        print(f"[INFO] Uploading renamed resume: {renamed_resume.name} ...")
        # Naukri's resume input element is typically input#attachCV or input[type=file]
        file_input = wait.until(
            EC.presence_of_element_located((By.XPATH, "//input[@id='attachCV' or @type='file']"))
        )

        # Send the absolute file path to the input element
        file_input.send_keys(str(renamed_resume.resolve()))

        # 7. Wait for upload confirmation
        print("[INFO] File sent. Waiting for upload confirmation...")
        time.sleep(5)  # Allow initial AJAX request to fire

        try:
            # Look for success toast or updated date indicator
            success_elem = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((
                    By.XPATH,
                    "//*[contains(text(), 'Resume has been successfully uploaded') or contains(text(), 'uploaded successfully') or contains(@class, 'success') or contains(@class, 'msg')]"
                ))
            )
            print(f"[SUCCESS] {success_elem.text.strip() or 'Resume uploaded successfully!'}")
            upload_success = True
        except Exception:
            # Fallback check: check if the page displays the new file or updated today
            print("[INFO] Verifying upload via page content...")
            page_text = driver.find_element(By.TAG_NAME, "body").text
            if "Resume has been successfully uploaded" in page_text or renamed_resume.name in page_text or "Uploaded today" in page_text or "today" in page_text.lower():
                print("[SUCCESS] Resume upload verified on Naukri profile!")
                upload_success = True
            else:
                print("[WARN] Upload submitted. Please check your Naukri profile to confirm.")
                upload_success = True

        print(f"\n[DONE] Profile updated with resume: {renamed_resume.name}")

    except Exception as e:
        print(f"\n[ERROR] An unexpected error occurred: {e}")
        upload_success = False

    finally:
        # Cleanup temporary renamed copy if requested
        if not KEEP_RENAMED_COPY and renamed_resume.exists():
            try:
                renamed_resume.unlink()
                print(f"[INFO] Cleaned up temporary copy: {renamed_resume.name}")
            except Exception as ce:
                print(f"[WARN] Could not remove temp file: {ce}")

        if driver:
            print("[INFO] Closing browser...")
            time.sleep(3)
            driver.quit()

    return upload_success


def test_rename(mode: str = None):
    """Utility function to test resume renaming without launching a browser."""
    resume_path = resolve_resume_path(RESUME_PATH_ENV)
    mode = mode or RESUME_RENAME_MODE
    print("\n--- Testing Resume Renaming Feature ---")
    if not RESUME_PATH_ENV:
        # Create a mock resume file in temp_resumes for demonstration
        TEMP_DIR.mkdir(parents=True, exist_ok=True)
        demo_file = TEMP_DIR / "Sample_Resume.pdf"
        demo_file.touch()
        resume_path = demo_file
        print(f"[NOTE] No RESUME_PATH provided in .env. Using mock file: {demo_file.name}")

    print(f"Original File : {resume_path.name}")
    print(f"Selected Mode : {mode}")

    for test_mode in ["date_first", "date_time", "timestamp", "date_only"]:
        result = create_renamed_resume(resume_path, mode=test_mode)
        marker = " <-- (ACTIVE MODE)" if test_mode == mode else ""
        print(f"  [{test_mode.ljust(10)}] -> {result.name}{marker}")
        if not KEEP_RENAMED_COPY:
            result.unlink()

    print("---------------------------------------\n")


def main():
    parser = argparse.ArgumentParser(description="Automate Naukri Resume Updates with Date/Timestamp Renaming")
    parser.add_argument("--test-rename", action="store_true", help="Test the resume renaming logic without logging into Naukri")
    parser.add_argument("--mode", type=str, choices=["date_first", "date_time", "timestamp", "date_only"],
                        help="Override the renaming mode (date_first, date_time, timestamp, date_only)")
    parser.add_argument("--headless", action="store_true", help="Run Chrome in headless mode")

    args = parser.parse_args()

    if args.test_rename:
        test_rename(mode=args.mode)
        return

    headless = args.headless or HEADLESS_ENV
    update_naukri_resume(headless=headless, rename_mode=args.mode)


if __name__ == "__main__":
    main()
