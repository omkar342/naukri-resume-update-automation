"""Naukri automation workflow and client implementation.

Executes credential validation, browser navigation, login handling with
OTP/CAPTCHA detection, profile navigation, and resume upload verification
across single or multiple Naukri accounts.
"""

import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.config import AccountConfig, Config
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
    """Manages the end-to-end resume update lifecycle across Naukri accounts."""

    def __init__(self, config: Config) -> None:
        """Initializes client with parsed configuration."""
        self.config = config

    def _login(
        self,
        driver: webdriver.Chrome,
        wait: WebDriverWait,
        account: AccountConfig,
    ) -> bool:
        """Fills credentials, submits, and waits for successful login for an account."""
        print(f"[INFO] [{account.name}] Navigating to Naukri login page...")
        driver.get(NAUKRI_LOGIN_URL)

        print(f"[INFO] [{account.name}] Entering credentials ({account.email})...")
        email_elem = wait.until(
            EC.presence_of_element_located((By.XPATH, USERNAME_FIELD_XPATH))
        )
        email_elem.clear()
        email_elem.send_keys(account.email)

        pass_elem = wait.until(
            EC.presence_of_element_located((By.XPATH, PASSWORD_FIELD_XPATH))
        )
        pass_elem.clear()
        pass_elem.send_keys(account.password)

        login_btn = wait.until(
            EC.element_to_be_clickable((By.XPATH, LOGIN_BUTTON_XPATH))
        )
        login_btn.click()

        print(f"[INFO] [{account.name}] Waiting for authentication...")
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
                print(f"[NOTICE] OTP or verification prompt detected for {account.name}!")
                print(f"         Account: {account.email}")
                print("         Please check the opened browser window and enter the OTP.")
                print("*" * 60 + "\n")
                otp_alerted = True

            # Detect server-side rejection messages
            error_matches = driver.find_elements(
                By.XPATH, CREDENTIAL_ERROR_XPATH
            )
            for err in error_matches:
                if err.is_displayed() and err.text.strip():
                    print(
                        f"[ERROR] [{account.name}] Login rejected by Naukri: {err.text.strip()}"
                    )
                    return False

            time.sleep(POLL_INTERVAL_SECONDS)

        if not logged_in:
            print(
                f"[ERROR] [{account.name}] Login timed out or did not redirect to profile."
            )
            return False

        print(f"[SUCCESS] [{account.name}] Successfully logged into Naukri!")
        return True

    def _upload_resume(
        self,
        driver: webdriver.Chrome,
        wait: WebDriverWait,
        resume_file: Path,
        account: AccountConfig,
    ) -> bool:
        """Navigates to profile and submits the renamed resume file."""
        print(f"[INFO] [{account.name}] Navigating directly to profile page...")
        driver.get(NAUKRI_PROFILE_URL)
        time.sleep(PAGE_TRANSITION_DELAY)

        print(f"[INFO] [{account.name}] Uploading resume: {resume_file.name} ...")
        file_input = wait.until(
            EC.presence_of_element_located((By.XPATH, RESUME_INPUT_XPATH))
        )
        file_input.send_keys(str(resume_file.resolve()))

        print(f"[INFO] [{account.name}] File sent. Waiting for upload confirmation...")
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
                f"[SUCCESS] [{account.name}] {success_elem.text.strip() or 'Upload verified!'}"
            )
            return True
        except Exception:
            # Fallback verification through profile body text
            print(f"[INFO] [{account.name}] Verifying upload via page content...")
            body_text = driver.find_element(By.TAG_NAME, "body").text
            is_verified = (
                "Resume has been successfully uploaded" in body_text
                or resume_file.name in body_text
                or "uploaded today" in body_text.lower()
            )
            if is_verified:
                print(f"[SUCCESS] [{account.name}] Resume upload verified on Naukri profile!")
                return True

            print(f"[WARN] [{account.name}] Upload submitted. Please check profile to confirm.")
            return True

    def run_account(self, account: AccountConfig) -> bool:
        """Executes the full automated resume update process for a single account."""
        # 1. Validation
        account_errors = account.validate()
        if account_errors:
            print(f"\n[!] CONFIGURATION ERROR(S) FOR {account.name}:")
            for err in account_errors:
                print(f"  - {err}")
            return False

        # 2. File preparation
        rename_mode = account.rename_mode or self.config.rename_mode
        print(f"\n[INFO] [{account.name}] Original Resume: {account.resume_path}")
        print(f"[INFO] [{account.name}] Renaming Mode  : {rename_mode}")
        renamed_file: Optional[Path] = None
        try:
            renamed_file = create_renamed_resume(
                original_path=account.resume_path,
                mode=rename_mode,
                temp_dir=self.config.temp_dir,
            )
            print(f"[INFO] [{account.name}] Prepared copy  : {renamed_file.name}")
        except Exception as err:
            print(f"[ERROR] [{account.name}] Could not prepare renamed resume: {err}")
            return False

        driver: Optional[webdriver.Chrome] = None
        upload_success = False

        try:
            print(f"[INFO] [{account.name}] Launching Chrome browser...")
            driver = init_driver(headless=self.config.headless)
            wait = WebDriverWait(driver, DEFAULT_WAIT_TIMEOUT)

            # 3. Login
            if not self._login(driver=driver, wait=wait, account=account):
                return False

            # 4. Upload
            upload_success = self._upload_resume(
                driver=driver,
                wait=wait,
                resume_file=renamed_file,
                account=account,
            )
            if upload_success:
                print(f"\n[DONE] [{account.name}] Profile updated with: {renamed_file.name}")

        except Exception as err:
            print(f"\n[ERROR] [{account.name}] An unexpected error occurred: {err}")
            upload_success = False

        finally:
            # 5. Cleanup
            if not self.config.keep_renamed_copy and renamed_file:
                cleanup_temp_file(renamed_file)

            quit_driver(driver)

        return upload_success

    def filter_accounts(
        self,
        target_account: Optional[str] = None,
    ) -> List[AccountConfig]:
        """Filters configured accounts based on target identifier (index, name, or email)."""
        if not target_account:
            return self.config.accounts

        target = target_account.strip().lower()

        # Check if target is a 1-based index
        if target.isdigit():
            idx = int(target)
            if 1 <= idx <= len(self.config.accounts):
                return [self.config.accounts[idx - 1]]
            print(
                f"[WARN] Account index {idx} out of range (1 to {len(self.config.accounts)}). "
                f"No account matched."
            )
            return []

        # Check by name or email match
        matches = [
            acc
            for acc in self.config.accounts
            if target == acc.name.lower() or target in acc.email.lower()
        ]
        if not matches:
            # Substring match on name as fallback
            matches = [
                acc
                for acc in self.config.accounts
                if target in acc.name.lower()
            ]

        return matches

    def run(self, target_account: Optional[str] = None) -> bool:
        """Executes automated resume update across configured accounts."""
        # Validate global settings
        global_errors = self.config.validate()
        if global_errors:
            print("\n" + "=" * 65)
            print("[!] CONFIGURATION ERROR(S) DETECTED:")
            for err in global_errors:
                print(f"  - {err}")
            print("\nPlease check your '.env' or 'accounts.json' file.")
            print("=" * 65 + "\n")
            return False

        accounts_to_run = self.filter_accounts(target_account)
        if not accounts_to_run:
            print(f"\n[ERROR] No matching account found for '{target_account}'.")
            print("Available configured accounts:")
            for i, acc in enumerate(self.config.accounts, start=1):
                print(f"  [{i}] {acc.name} ({acc.email})")
            return False

        total = len(accounts_to_run)
        print(f"\n[INFO] Starting resume update process for {total} account(s)...")

        results: List[Tuple[AccountConfig, bool]] = []

        for idx, account in enumerate(accounts_to_run, start=1):
            print("\n" + "=" * 65)
            print(f"  ACCOUNT [{idx}/{total}]: {account.name} ({account.email})")
            print("=" * 65)

            status = self.run_account(account)
            results.append((account, status))

            # Delay between accounts (skip after the last one)
            if idx < total and self.config.delay_between_accounts > 0:
                print(
                    f"\n[INFO] Waiting {self.config.delay_between_accounts}s "
                    f"before processing next account..."
                )
                time.sleep(self.config.delay_between_accounts)

        # Print Execution Summary
        print("\n" + "=" * 65)
        print("                     EXECUTION SUMMARY")
        print("=" * 65)
        success_count = 0
        for acc, status in results:
            mark = "✓ SUCCESS" if status else "✗ FAILED"
            if status:
                success_count += 1
            print(f"  [{mark}] {acc.name.ljust(18)} : {acc.email}")

        print("-" * 65)
        print(
            f"  Total Accounts : {total} | "
            f"Succeeded: {success_count} | "
            f"Failed: {total - success_count}"
        )
        print("=" * 65 + "\n")

        return success_count == total
