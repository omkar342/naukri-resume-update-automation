"""Application constants and default configurations.

Contains all timeout thresholds, URLs, XPaths, and selector strings
used by the automation.
"""

# Timeouts & Delays (in seconds)
DEFAULT_WAIT_TIMEOUT = 20
LOGIN_TIMEOUT_DEFAULT = 120
POLL_INTERVAL_SECONDS = 2
PAGE_TRANSITION_DELAY = 3
UPLOAD_SETTLE_DELAY = 5
UPLOAD_CONFIRMATION_TIMEOUT = 15
BROWSER_CLOSE_DELAY = 3

# Target URLs
NAUKRI_LOGIN_URL = "https://www.naukri.com/nlogin/login"
NAUKRI_PROFILE_URL = "https://www.naukri.com/mnjuser/profile"

# URL fragments indicating successful authentication
LOGIN_REDIRECT_KEYS = (
    "mnjuser/homepage",
    "mnjuser/profile",
    "naukri.com/mnjuser",
)

# Selectors (XPaths)
USERNAME_FIELD_XPATH = (
    "//input[@id='usernameField' or "
    "@placeholder='Enter your active Email ID / Username']"
)
PASSWORD_FIELD_XPATH = (
    "//input[@id='passwordField' or @type='password']"
)
LOGIN_BUTTON_XPATH = (
    "//button[@type='submit' or text()='Login' or "
    "contains(@class, 'login-btn')]"
)
RESUME_INPUT_XPATH = "//input[@id='attachCV' or @type='file']"
OTP_DETECTION_XPATH = (
    "//*[contains(text(), 'OTP') or "
    "contains(text(), 'verification code') or "
    "contains(@class, 'otp') or "
    "contains(text(), 'Verify')]"
)
CREDENTIAL_ERROR_XPATH = (
    "//*[contains(@class, 'server-err') or "
    "contains(@class, 'error-message') or "
    "contains(text(), 'Invalid details')]"
)
UPLOAD_SUCCESS_XPATH = (
    "//*[contains(text(), 'Resume has been successfully uploaded') or "
    "contains(text(), 'uploaded successfully') or "
    "contains(@class, 'success') or "
    "contains(@class, 'msg')]"
)

# Supported resume renaming modes
DEFAULT_RENAME_MODE = "date_time"
SUPPORTED_RENAME_MODES = ("date_first", "date_time", "timestamp", "date_only")

# Browser Configuration
BROWSER_WINDOW_WIDTH = 1920
BROWSER_WINDOW_HEIGHT = 1080
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

# CDP script to hide navigator.webdriver
CDP_HIDE_WEBDRIVER_SCRIPT = {
    "source": """
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
    """
}

# Directories & Files
TEMP_DIR_NAME = "temp_resumes"
ENV_FILE_NAME = ".env"
ENV_EXAMPLE_NAME = ".env.example"
