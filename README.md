# 🚀 Naukri Resume Update Automation

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![Selenium](https://img.shields.io/badge/selenium-4.10%2B-green.svg)](https://www.selenium.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An automated Python script that updates your resume on **Naukri.com** periodically to keep your profile active and prominently ranked at the top of recruiter searches.

Naukri prioritizes candidate profiles that are updated frequently. By automating this process, your profile consistently displays an **"Active Today"** / **"Updated Recently"** status without requiring manual daily uploads.

---

## ✨ Features

- 👥 **Multi-Account Support**: Update multiple Naukri accounts sequentially in a single run. Configure accounts in `.env` (e.g. `NAUKRI_EMAIL_1`, `NAUKRI_EMAIL_2`) or via an optional `accounts.json` file. Each account can have its own dedicated resume or share a default master resume!
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
├── src/
│   ├── config.py          # Configuration loading, validation & path resolution
│   ├── constants.py       # Selectors, timeouts, and URLs
│   ├── driver.py          # Chrome WebDriver initialization & anti-bot flags
│   ├── file_utils.py      # Resume copying, stem cleaning & renaming
│   └── naukri_client.py   # Selenium workflow & upload automation
├── naukri_updater.py      # Main CLI entrypoint
├── requirements.txt       # Python package dependencies
├── accounts.example.json  # Multi-account JSON template
├── .env.example           # Example configuration template
├── .gitignore             # Ignores credentials (.env, accounts.json) and temp folders
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

### 3. Configure Your Credentials

You can configure single or multiple accounts using either **`.env`** (recommended) or an **`accounts.json`** file.

#### Option A: Via `.env` (Numbered Variables)
Copy the example template to `.env`:
```bash
cp .env.example .env
```

Open `.env` and configure your account(s):
```env
# Default / Fallback resume
RESUME_PATH="/home/username/Documents/My_Resume.pdf"

# --- Account 1 ---
NAUKRI_NAME_1="Primary Profile"
NAUKRI_EMAIL_1=first_email@example.com
NAUKRI_PASSWORD_1=first_password
RESUME_PATH_1="/home/username/Documents/Resume_Dev.pdf"

# --- Account 2 ---
NAUKRI_NAME_2="Second Profile"
NAUKRI_EMAIL_2=second_email@example.com
NAUKRI_PASSWORD_2=second_password
RESUME_PATH_2="/home/username/Documents/Resume_Ops.pdf"

# Delay in seconds between processing consecutive accounts
DELAY_BETWEEN_ACCOUNTS=5

# Global Settings
RESUME_RENAME_MODE=date_time
HEADLESS=false
KEEP_RENAMED_COPY=false
LOGIN_TIMEOUT=120
```

> [!TIP]
> If `RESUME_PATH_<N>` is omitted for an account, it automatically falls back to the default `RESUME_PATH`.
> Single account setups (`NAUKRI_EMAIL`, `NAUKRI_PASSWORD`) remain 100% backward-compatible.

#### Option B: Via `accounts.json`
Alternatively, you can copy `accounts.example.json` to `accounts.json`:
```bash
cp accounts.example.json accounts.json
```
```json
[
  {
    "name": "Primary Profile",
    "email": "first_email@example.com",
    "password": "first_password",
    "resume_path": "/home/username/Documents/Resume_1.pdf"
  },
  {
    "name": "Second Profile",
    "email": "second_email@example.com",
    "password": "second_password",
    "resume_path": "/home/username/Documents/Resume_2.pdf"
  }
]
```

> [!IMPORTANT]
> Never commit your real `.env` or `accounts.json` files to Git. Both are included in `.gitignore` to protect your login credentials.

---

## 🚀 Usage

### 1. Preview the Renaming Format (Dry Run)
Preview how resumes will be formatted for all configured accounts without opening Chrome:
```bash
python3 naukri_updater.py --test-rename
```

Or test a specific account only:
```bash
python3 naukri_updater.py --test-rename --account 1
python3 naukri_updater.py --test-rename --account "second_email@example.com"
```

### 2. Run the Automation
Run with a visible browser window (recommended for the first run to complete any OTP/CAPTCHA challenge if prompted):
```bash
python3 naukri_updater.py
```

### 3. Run for a Specific Account
Target an individual account using its 1-based index, name, or email:
```bash
python3 naukri_updater.py --account 1
python3 naukri_updater.py --account "Second Profile"
```

### 4. Run in Headless Mode (Background / Cron)
Run all configured accounts silently in the background:
```bash
python3 naukri_updater.py --headless
```


---

## ⏰ Scheduling & Background Automation

### 🐧 Linux (Cron & Startup)

You can set up a cron job to update your resume automatically at regular intervals whenever your computer is powered on.

#### Periodic (Every 30 Minutes):
1. Open crontab in your terminal:
   ```bash
   crontab -e
   ```
2. Add the following line at the bottom (replace paths with your actual project and Python interpreter paths):
   ```cron
   */30 * * * * cd "/path/to/naukri-resume-update-automation" && /path/to/python3 naukri_updater.py --headless >> cron.log 2>&1
   ```

#### Run on System Startup:
Add `@reboot` with a short delay so Wi-Fi connects first:
```cron
@reboot sleep 45 && cd "/path/to/naukri-resume-update-automation" && /path/to/python3 naukri_updater.py --headless >> cron.log 2>&1
```

#### Helpful Cron Commands:
- **List active cron jobs**: `crontab -l`
- **View live execution logs**: `tail -f cron.log`
- **Remove/Pause cron job**: `crontab -e` (comment out with `#`)

---

### 🪟 Windows (Task Scheduler)

On Windows, use **Windows Task Scheduler** (`taskschd.msc`) to run the automation periodically, on startup, and when opening your laptop.

> [!TIP]
> Use `pythonw.exe` instead of `python.exe` so the script runs completely in the background without popping up a black command prompt window.

#### Option A: Quick Setup via PowerShell (Recommended)
Open PowerShell and run the following command (adjust paths to match your system):

```powershell
$action = New-ScheduledTaskAction `
    -Execute "pythonw.exe" `
    -Argument "naukri_updater.py --headless" `
    -WorkingDirectory "C:\path\to\naukri-resume-update-automation"

# Trigger 1: Run every time you log in / startup
$triggerLogon = New-ScheduledTaskTrigger -AtLogon

# Trigger 2: Run every 30 minutes
$triggerRepeat = New-ScheduledTaskTrigger -Once -At (Get-Date) `
    -RepetitionInterval (New-TimeSpan -Minutes 30) `
    -RepetitionDuration ([TimeSpan]::MaxValue)

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable

Register-ScheduledTask `
    -TaskName "NaukriResumeUpdate" `
    -Action $action `
    -Trigger @($triggerLogon, $triggerRepeat) `
    -Settings $settings `
    -Description "Automated Naukri Resume Updates"
```

#### Option B: Setup via Graphical Interface (Task Scheduler GUI)
1. Press `Win + R`, type `taskschd.msc`, and press **Enter**.
2. In the right panel, click **Create Task...** (do not choose "Create Basic Task"):
   - **General Tab**:
     - Name: `Naukri Resume Updater`
     - Select: **Run only when user is logged on**
   - **Triggers Tab**:
     - *To run on startup*: Click **New...** -> Select **At log on** -> Click **OK**.
     - *To run periodically*: Click **New...** -> Select **On a schedule** (Daily) -> Check **Repeat task every**: `30 minutes` for a duration of: `Indefinitely` -> Click **OK**.
     - *(Optional: Run on laptop lid open)*: Click **New...** -> Select **On an event** -> Log: `System`, Source: `Power-Troubleshooter`, Event ID: `1`.
   - **Actions Tab**:
     - Click **New...** -> Action: **Start a program**.
     - Program/script: `pythonw.exe` (or full path, e.g. `C:\Users\<User>\AppData\Local\Programs\Python\Python311\pythonw.exe`).
     - Add arguments: `naukri_updater.py --headless`
     - Start in: `C:\path\to\naukri-resume-update-automation`
   - **Conditions Tab** (Crucial for Laptops!):
     - **Uncheck**: *"Start the task only if the computer is on AC power"* (so it works on battery).
     - **Uncheck**: *"Stop if the computer switches to battery power"*.
     - **Check**: *"Start only if the following network connection is available: Any connection"*.
3. Click **OK** to save.

#### Option D: Real Linux Cron via WSL (Windows Subsystem for Linux)
If you have WSL installed, you can use the exact same Linux `crontab -e`:
1. Open your Ubuntu WSL terminal.
2. Run `crontab -e` and add:
   ```cron
   */30 * * * * cd "/mnt/c/path/to/naukri-resume-update-automation" && python3 naukri_updater.py --headless >> cron.log 2>&1
   ```
3. Ensure the cron service is active: `sudo service cron start`

---

## 🔒 Security & Privacy

- All credentials and sensitive paths are managed locally through `.env`.
- No credentials or personal data are logged or transmitted anywhere outside of the official Naukri login page.

---

## ⚖️ Disclaimer

This project is created for educational and personal workflow automation purposes only. Please use responsibly and adhere to Naukri's Terms of Service.
