"""WebDriver factory and anti-detection configuration.

Initializes Chrome WebDriver instances with stealth options to avoid
bot detection flags during automated navigation.
"""

import time
from typing import Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from src.constants import (
    BROWSER_CLOSE_DELAY,
    BROWSER_WINDOW_HEIGHT,
    BROWSER_WINDOW_WIDTH,
    CDP_HIDE_WEBDRIVER_SCRIPT,
    DEFAULT_USER_AGENT,
)


def init_driver(headless: bool = False) -> webdriver.Chrome:
    """Initializes Chrome WebDriver with stealth options."""
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless=new")

    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument(
        f"--window-size={BROWSER_WINDOW_WIDTH},{BROWSER_WINDOW_HEIGHT}"
    )

    # Anti-bot detection flags
    chrome_options.add_argument(
        "--disable-blink-features=AutomationControlled"
    )
    chrome_options.add_experimental_option(
        "excludeSwitches", ["enable-automation"]
    )
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_argument(f"--user-agent={DEFAULT_USER_AGENT}")

    try:
        # Modern Selenium 4 manages ChromeDriver automatically
        driver = webdriver.Chrome(options=chrome_options)
    except Exception:
        # Optional fallback to ChromeDriverManager if installed
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            from selenium.webdriver.chrome.service import Service

            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(
                service=service,
                options=chrome_options,
            )
        except Exception as err:
            print(f"[ERROR] Failed to initialize Chrome WebDriver: {err}")
            raise

    # Hide navigator.webdriver property via DevTools Protocol
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        CDP_HIDE_WEBDRIVER_SCRIPT,
    )
    return driver


def quit_driver(driver: Optional[webdriver.Chrome]) -> None:
    """Closes and quits the Chrome WebDriver safely."""
    if driver:
        print("[INFO] Closing browser...")
        try:
            time.sleep(BROWSER_CLOSE_DELAY)
            driver.quit()
        except Exception as err:
            print(f"[WARN] Error during browser shutdown: {err}")
