# OSINT Monitor

OSINT Monitor is a Python-based continuous monitoring tool for collecting public X (Twitter) posts related to predefined threat-intelligence keywords such as `malware`, `phishing`, and `ransomware`.

The current project focuses on one platform, which satisfies the minimum assignment requirement, and stores deduplicated results in a local SQLite database for later analysis.

## Features

- Continuous keyword monitoring loop via `main.py`
- Manual one-time login flow that saves reusable session cookies
- Headless background scraping for the automated run
- Optional visible browser mode for troubleshooting
- Local SQLite storage with duplicate prevention
- Debug artifact capture on failures
- Automatic cleanup of stale ChromeDriver processes on Windows

## Current Project Status

The project currently works in this flow:

1. Run `python scraper.py login` once to generate `twitter_cookies.json`
2. Run `python main.py` to continuously monitor the configured keywords
3. New posts are saved into `osint_data.db`
4. Existing posts are skipped automatically based on `post_link`

## Requirements Coverage

This repository currently covers the assignment requirements as follows:

- Keyword input list: implemented in `main.py` through the `keywords` list
- Continuous monitoring: implemented with an infinite loop and periodic waits
- Platform monitoring: currently X/Twitter only
- Minimum data collected per post:
  - platform
  - username
  - post text
  - timestamp
  - post link
- Storage layer: SQLite via `database.py`
- Duplicate detection: enforced in code and in the database using a unique `post_link`
- Modular architecture: split across `main.py`, `scraper.py`, and `database.py`

## Project Structure

- `main.py` - continuous monitoring loop and scheduler
- `scraper.py` - login flow, browser setup, search navigation, tweet extraction
- `database.py` - SQLite connection, schema setup, insert logic, duplicate handling
- `requirements.txt` - Python dependencies
- `twitter_cookies.json` - saved authenticated session cookies
- `debug_output/` - screenshots and HTML dumps captured during debug failures

## Prerequisites

- Python 3.8+
- Google Chrome installed
- Windows is the primary tested environment in the current setup
- A valid X account for the initial login step

## Installation

1. Create a virtual environment:

```bash
python -m venv venv
```

2. Activate it:

```bash
venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### 1. Generate login cookies

Run this once when setting up the project or whenever the X session expires:

```bash
python scraper.py login
```

What happens:

- A visible Chrome window opens
- You log in manually to X
- The scraper waits until the authenticated session is detected
- Cookies are saved into `twitter_cookies.json`

### 2. Run one keyword manually

Default behavior is headless:

```bash
python scraper.py phishing
```

Run with a visible browser if you want to inspect the session interactively:

```bash
python scraper.py phishing --show-browser
```

Enable debug artifacts:

```bash
python scraper.py phishing --debug --max-tweets 20
```

### 3. Run the continuous monitor

```bash
python main.py
```

Current default behavior in `main.py`:

- monitors `malware`, `phishing`, and `ransomware`
- waits 60 seconds between keywords
- waits 15 minutes between full monitoring cycles
- runs in headless mode during the automated loop

To stop the monitor:

```bash
Ctrl+C
```

The program handles interruption gracefully.

## Command Reference

### `scraper.py`

```bash
python scraper.py login
python scraper.py <keyword>
python scraper.py <keyword> --show-browser
python scraper.py <keyword> --debug --max-tweets 20
```

Available options:

- `login` - open a visible browser and save fresh cookies
- `<keyword>` - search term to collect from X live results
- `--show-browser` - run visibly instead of headless
- `--debug` - save screenshot and HTML debug artifacts on failures
- `--max-tweets N` - cap the number of extracted tweets for that run
- `--login-timeout N` - control how long login mode waits for manual authentication

## Browser Behavior

The project currently uses two browser strategies:

- Headless collection: standard Selenium Chrome driver
- Visible login mode: `undetected_chromedriver`

This split exists because the login flow and the automated background flow have different stability requirements.

## Data Storage

Posts are stored in `osint_data.db` in a `posts` table with these fields:

- `platform`
- `username`
- `post_text`
- `timestamp`
- `post_link`

`post_link` is unique, so duplicate posts are ignored automatically.

## Debugging

If a run fails and `--debug` is enabled, the scraper saves:

- a screenshot
- the HTML page source

Files are written into `debug_output/` with a timestamped filename.

## Notes and Limitations

- The current implementation monitors X only
- Keyword configuration is currently hardcoded in `main.py`
- A valid cookie file is required for the unattended headless flow
- If cookies expire, rerun `python scraper.py login`
- X may change DOM structure or anti-bot behavior at any time, which can require selector or browser-setting updates

## Suggested Next Improvements

Possible future enhancements:

1. Move keywords into a config file such as `keywords.txt` or `config.json`
2. Export collected data to CSV or JSON in addition to SQLite
3. Add a second platform for the assignment bonus
4. Add alerting for new posts
5. Add configurable scheduling from the command line

## Disclaimer

This project is intended for educational and OSINT research use. Make sure your usage complies with the target platform's terms and with applicable law.
