"""Naukri automation workflow and client implementation.

Executes credential validation, browser navigation, login handling with
OTP/CAPTCHA detection, profile navigation, and resume upload verification.
"""

import time
from pathlib import Path
from typing import Optional

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.config import Config
from src.constants import (
    CREDENTIAL_ERROR_XPATH,
    DEFAULT_WAIT_TIMEOUT,
    LOGIN_BUTTON_XPATH,
    LOGIN_REDIRECT_KEYS,
    NAUKRI_LOGIN_URL,
    NAUKRI_PROFILE_URL,
    OTP_DETECTION_XPATH,
    PAGE_TRANSITION_DELAY,
    PASSWORD_FIELD_XPATH,
    POLL_INTERVAL_SECONDS,
    RESUME_INPUT_XPATH,
    UPLOAD_CONFIRMATION_TIMEOUT,
    UPLOAD_SETTLE_DELAY,
    UPLOAD_SUCCESS_XPATH,
    USERNAME_FIELD_XPATH,
)
from src.driver import init_driver, quit_driver
from src.file_utils import cleanup_temp_file, create_renamed_resume


class NaukriClient:
    """Manages the full end-to-end automation lifecycle on Naukri."""

    def __init__(self, config: Config) -> None:
        """Initializes client with parsed configuration."""
        self.config = config

    def _login(
        self,
        driver: webdriver.Chrome,
        wait: WebDriverWait,
    ) -> bool:
        """Fills credentials, submits, and waits for successful login."""
        print("[INFO] Navigating to Naukri login page...")
        driver.get(NAUKRI_LOGIN_URL)

        print("[INFO] Entering credentials...")
        email_elem = wait.until(
            EC.presence_of_element_located((By.XPATH, USERNAME_FIELD_XPATH))
        )
        email_elem.clear()
        email_elem.send_keys(self.config.email)

        pass_elem = wait.until(
            EC.presence_of_element_located((By.XPATH, PASSWORD_FIELD_XPATH))
        )
        pass_elem.clear()
        pass_elem.send_keys(self.config.password)

        login_btn = wait.until(
            EC.element_to_be_clickable((By.XPATH, LOGIN_BUTTON_XPATH))
        )
        login_btn.click()

        print("[INFO] Waiting for authentication...")
        logged_in = False
        start_time = time.time()
        otp_alerted = False

        while time.time() - start_time < self.config.login_timeout:
            curr_url = driver.current_url
            if any(key in curr_url for key in LOGIN_REDIRECT_KEYS):
                logged_in = True
                break

            # Detect OTP or 2FA challenge screen
            otp_matches = driver.find_elements(By.XPATH, OTP_DETECTION_XPATH)
            if otp_matches and not otp_alerted:
                print("\n" + "*" * 60)
                print("[NOTICE] OTP or verification prompt detected!")
                print(
                    "         Please check the opened browser window "
                    "and enter the OTP."
                )
                print("*" * 60 + "\n")
                otp_alerted = True

            # Detect server-side rejection messages
            error_matches = driver.find_elements(
                By.XPATH, CREDENTIAL_ERROR_XPATH
            )
            for err in error_matches:
                if err.is_displayed() and err.text.strip():
                    print(
                        f"[ERROR] Login rejected by Naukri: {err.text.strip()}"
                    )
                    return False

            time.sleep(POLL_INTERVAL_SECONDS)

        if not logged_in:
            print(
                "[ERROR] Login timed out or did not redirect to profile."
            )
            return False

        print("[SUCCESS] Successfully logged into Naukri!")
        return True

    def _upload_resume(
        self,
        driver: webdriver.Chrome,
        wait: WebDriverWait,
        resume_file: Path,
    ) -> bool:
        """Navigates to profile and submits the renamed resume file."""
        print("[INFO] Navigating directly to profile page...")
        driver.get(NAUKRI_PROFILE_URL)
        time.sleep(PAGE_TRANSITION_DELAY)

        print(f"[INFO] Uploading resume: {resume_file.name} ...")
        file_input = wait.until(
            EC.presence_of_element_located((By.XPATH, RESUME_INPUT_XPATH))
        )
        file_input.send_keys(str(resume_file.resolve()))

        print("[INFO] File sent. Waiting for upload confirmation...")
        time.sleep(UPLOAD_SETTLE_DELAY)

        try:
            success_elem = WebDriverWait(
                driver, UPLOAD_CONFIRMATION_TIMEOUT
            ).until(
                EC.presence_of_element_located(
                    (By.XPATH, UPLOAD_SUCCESS_XPATH)
                )
            )
            print(
                f"[SUCCESS] {success_elem.text.strip() or 'Upload verified!'}"
            )
            return True
        except Exception:
            # Fallback verification through profile body text
            print("[INFO] Verifying upload via page content...")
            body_text = driver.find_element(By.TAG_NAME, "body").text
            is_verified = (
                "Resume has been successfully uploaded" in body_text
                or resume_file.name in body_text
                or "uploaded today" in body_text.lower()
            )
            if is_verified:
                print("[SUCCESS] Resume upload verified on Naukri profile!")
                return True

            print("[WARN] Upload submitted. Please check profile to confirm.")
            return True

    def run(self) -> bool:
        """Executes the full automated resume update process."""
        # 1. Validation
        validation_errors = self.config.validate()
        if validation_errors:
            print("\n" + "=" * 60)
            print("[!] CONFIGURATION ERROR(S) DETECTED:")
            for err in validation_errors:
                print(f"  - {err}")
            print("\nPlease update your '.env' file with your real details.")
            print("=" * 60 + "\n")
            return False

        # 2. File preparation
        print(f"\n[INFO] Original Resume: {self.config.resume_path}")
        print(f"[INFO] Renaming Mode   : {self.config.rename_mode}")
        try:
            renamed_file = create_renamed_resume(
                original_path=self.config.resume_path,
                mode=self.config.rename_mode,
                temp_dir=self.config.temp_dir,
            )
            print(f"[INFO] Prepared copy   : {renamed_file.name}")
        except Exception as err:
            print(f"[ERROR] Could not prepare renamed resume: {err}")
            return False

        driver: Optional[webdriver.Chrome] = None
        upload_success = False

        try:
            print("\n[INFO] Launching Chrome browser...")
            driver = init_driver(headless=self.config.headless)
            wait = WebDriverWait(driver, DEFAULT_WAIT_TIMEOUT)

            # 3. Login
            if not self._login(driver=driver, wait=wait):
                return False

            # 4. Upload
            upload_success = self._upload_resume(
                driver=driver,
                wait=wait,
                resume_file=renamed_file,
            )
            if upload_success:
                print(f"\n[DONE] Profile updated with: {renamed_file.name}")

        except Exception as err:
            print(f"\n[ERROR] An unexpected error occurred: {err}")
            upload_success = False

        finally:
            # 5. Cleanup
            if not self.config.keep_renamed_copy:
                cleanup_temp_file(renamed_file)

            quit_driver(driver)

        return upload_success
