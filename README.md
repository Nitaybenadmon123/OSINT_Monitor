# OSINT Monitor 🕵️‍♂️

OSINT Monitor is a Python-based automated monitoring and scraping tool designed to track specific keywords and threat intelligence (like phishing campaigns, zero-day mentions, etc.) on X (formerly Twitter). 

It utilizes Selenium WebDriver to navigate the platform, extract relevant posts, and store them locally in an SQLite database for further analysis.

## ✨ Features

- **Session Persistence**: Reuses session cookies (`twitter_cookies.json`) to safely bypass repetitive logins and 2FA.
- **Local Database**: Automatically saves deduplicated extracted data into a local SQLite database (`osint_data.db`).
- **Flexible CLI**: Control the scraper's behavior directly from the terminal with various flags.
- **Robust Debugging**: Built-in debug mode (`--debug`) that automatically dumps HTML and takes screenshots into a `debug_output/` folder if the scraper encounters an issue or timeout.
- **Anti-Bot Awareness**: Supports headed browser scraping (`--show-browser`) to bypass strict headless WAF detection mechanisms implemented by X.

## 📋 Prerequisites

- **Python 3.8+**
- **Google Chrome** installed on your machine.
- (Optional but recommended) A dedicated X/Twitter account for research.

## 🚀 Installation

1. Open a terminal and navigate to the project directory.
2. Create a virtual environment:
   ```bash
   python -m venv venv
   ```
3. Activate the virtual environment:
   - **Windows**: `venv\Scripts\activate`
   - **Mac/Linux**: `source venv/bin/activate`
4. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## 💻 Usage Flow

### Step 1: Initial Login (Cookie Generation)
Before running automated searches, you need to create an authenticated session file. Run the following command:

```bash
python scraper.py login
```
*This will open a Chrome window. Log in to your account manually. Once you are successfully logged in and the homepage loads, the script will automatically capture your session cookies and save them.*

### Step 2: Run a Search
Once authenticated, you can search for any keyword (e.g., "phishing"). 

***Note:** Due to aggressive anti-bot protections on X, purely headless execution may result in empty feeds. It is recommended to use the `--show-browser` flag to ensure tweets render correctly.*

```bash
python scraper.py phishing --show-browser --debug --max-tweets 20
```

## 🛠️ Command Line Interface (CLI) Reference

The `scraper.py` script acts as the main entry point:

| Command / Flag | Description |
| :--- | :--- |
| `login` | Dedicated mode to perform a manual login and generate session cookies. |
| `<keyword>` | The search term you want to monitor (e.g., `phishing`, `malware`). |
| `--show-browser` | Disables headless mode. Opens a visible Chrome window (Critical for bypassing Twitter's headless detection). |
| `--debug` | Enables verbose logging and saves screenshots + HTML dumps to `debug_output/` on failures. |
| `--max-tweets N` | Limits the number of tweets to scrape per run (default is usually unlimited or script-defined). |

## 🗄️ Database Structure

Data is saved to `osint_data.db` utilizing `database.py`. The database ensures that duplicate tweets (based on `post_link`) are not inserted twice, keeping your dataset clean and manageable.

## ⚠️ Disclaimer

This tool is created for educational and OSINT (Open Source Intelligence) research purposes only. Automated scraping may violate the Terms of Service of the target platforms. Use responsibly and at your own risk.
