# 🚀 Naukri Resume Update Automation

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![Selenium](https://img.shields.io/badge/selenium-4.10%2B-green.svg)](https://www.selenium.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An automated Python script that updates your resume on **Naukri.com** periodically to keep your profile active and prominently ranked at the top of recruiter searches.

Naukri prioritizes candidate profiles that are updated frequently. By automating this process, your profile consistently displays an **"Active Today"** / **"Updated Recently"** status without requiring manual daily uploads.

---

## ✨ Features

- 🕒 **Smart Resume Renaming**: Automatically creates a temporary copy of your resume with today's date and a fresh timestamp (e.g., `Omkar_Jadhav_Resume_2026-09-25_205446.pdf`) before uploading, keeping your master resume intact.
- 🧹 **Automatic Stem Cleaning**: Strips out old dates or redundant timestamps from the original filename to keep the uploaded filename clean and professional.
- 🛡️ **Anti-Bot & Stealth Mode**: Configured with Chrome anti-automation flags (`disable-blink-features=AutomationControlled`, realistic User-Agent, CDP overrides) to minimize bot detection.
- 🔐 **OTP / 2FA Tolerant**: Detects verification screens and pauses for up to 120 seconds so you can solve any OTP or CAPTCHA challenge manually.
- 🕶️ **Headless & Visible Modes**: Run visibly in a browser window during setup, or silently in the background (`--headless`) for cron scheduling.
- 🧪 **Preview Mode**: Test and preview how your resume will be renamed using `--test-rename` without logging in.
- ⚡ **Modern Selenium 4 Support**: Uses Selenium Manager directly—no manual ChromeDriver downloads or third-party managers required.

---

## 📁 Repository Structure

```text
├── naukri_updater.py      # Core automation script
├── requirements.txt       # Python package dependencies
├── .env.example           # Example configuration template
├── .gitignore             # Ignores credentials (.env) and temp folders
└── README.md              # Project documentation
```

---

## 📋 Prerequisites

1. **Python 3.8+** installed on your system.
2. **Google Chrome** browser installed:
   ```bash
   google-chrome --version
   ```

---

## 🛠️ Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/omkar342/naukri-resume-update-automation.git
cd naukri-resume-update-automation
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Create your `.env` File
Copy the example template to `.env`:
```bash
cp .env.example .env
```

Open `.env` and fill in your details:
```env
# Naukri Account Credentials
NAUKRI_EMAIL=your_email@example.com
NAUKRI_PASSWORD=your_naukri_password

# Path to your master resume file (PDF or DOCX)
RESUME_PATH="/home/username/Documents/My_Resume.pdf"

# Resume Renaming Mode
# Options:
#   - date_time  : (Default) Name first -> Resume_2026-09-25_203512.pdf
#   - date_first : Date first       -> 2026-09-25_Resume_203512.pdf
#   - timestamp  : Unix timestamp   -> Resume_1727276712.pdf
#   - date_only  : Date only        -> Resume_2026-09-25.pdf
RESUME_RENAME_MODE=date_time

# Run in headless mode (true/false)
HEADLESS=false

# Keep the temporary renamed copy after uploading? (true/false)
KEEP_RENAMED_COPY=false
```

> [!IMPORTANT]
> Never commit your real `.env` file to GitHub. It is already included in `.gitignore` to protect your login credentials.

---

## 🚀 Usage

### 1. Preview the Renaming Format (Dry Run)
Test how your resume file will be renamed without launching Chrome or logging in:
```bash
python3 naukri_updater.py --test-rename
```

### 2. Run the Automation
Run with a visible browser window (recommended for the first run to complete any OTP/CAPTCHA challenge if prompted):
```bash
python3 naukri_updater.py
```

### 3. Run in Headless Mode (Background)
Once verified, run silently without opening a browser window:
```bash
python3 naukri_updater.py --headless
```

---

## ⏰ Automating with Linux Cron

You can set up a cron job to update your resume automatically at regular intervals whenever your computer is powered on.

### Example: Run Every 30 Minutes
1. Open crontab in your terminal:
   ```bash
   crontab -e
   ```
2. Add the following line at the bottom (replace paths with your actual project and Python interpreter paths):
   ```cron
   */30 * * * * cd "/path/to/naukri-resume-update-automation" && /path/to/python3 naukri_updater.py --headless >> cron.log 2>&1
   ```
3. Save and exit.

### Helpful Cron Commands:
- **List active cron jobs**: `crontab -l`
- **View live execution logs**: `tail -f cron.log`
- **Remove/Pause cron job**: `crontab -e` (comment out with `#`)

---

## 🔒 Security & Privacy

- All credentials and sensitive paths are managed locally through `.env`.
- No credentials or personal data are logged or transmitted anywhere outside of the official Naukri login page.

---

## ⚖️ Disclaimer

This project is created for educational and personal workflow automation purposes only. Please use responsibly and adhere to Naukri's Terms of Service.
