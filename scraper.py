import argparse
import os
import pickle
import json
import sys
import time
import subprocess
from datetime import datetime
from urllib.parse import quote_plus, urlparse
import undetected_chromedriver as uc
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.common.exceptions import SessionNotCreatedException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

import database

BASE_URL = "https://x.com"
COOKIES_FILE = "twitter_cookies.json"
LEGACY_COOKIES_FILE = "twitter_cookies.pkl"
DEFAULT_WAIT_SECONDS = 20
DEFAULT_MAX_TWEETS = 25
DEFAULT_SCROLL_ROUNDS = 4
DEFAULT_LOGIN_TIMEOUT_SECONDS = 120
DEBUG_OUTPUT_DIR = "debug_output"
CHROME_USER_DATA_DIR = os.getenv("CHROME_USER_DATA_DIR", "").strip()
CHROME_PROFILE_DIRECTORY = os.getenv("CHROME_PROFILE_DIRECTORY", "Default").strip() or "Default"
AUTH_COOKIE_NAMES = {"auth_token", "ct0"}


def has_chrome_profile_config():
    return bool(CHROME_USER_DATA_DIR)


def debug_log(debug_enabled, message):
    if debug_enabled:
        print(f"[DEBUG] {message}")


def save_debug_artifacts(driver, label, debug_enabled):
    if not debug_enabled:
        return

    os.makedirs(DEBUG_OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_path = os.path.join(DEBUG_OUTPUT_DIR, f"{timestamp}_{label}")
    screenshot_path = f"{base_path}.png"
    html_path = f"{base_path}.html"

    driver.save_screenshot(screenshot_path)
    with open(html_path, "w", encoding="utf-8") as file:
        file.write(driver.page_source)

    print(f"[DEBUG] Saved screenshot: {screenshot_path}")
    print(f"[DEBUG] Saved page source: {html_path}")


def get_working_chrome_path():
    """Finds a working Chrome executable. Bypasses corrupted ones."""
    paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Google\Chrome\Application\chrome.exe")
    ]
    for path in paths:
        if os.path.exists(path):
            try:
                # Test if the executable is corrupted (WinError 14001)
                subprocess.run([path, "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
                return path
            except Exception:
                continue
    return None

def create_driver(use_chrome_profile=True, headless=True):
    """
    Creates a Chrome WebDriver.
    Uses standard Selenium for true headless mode to prevent unwanted popups,
    and undetected-chromedriver for headed login mode.
    """
    if headless:
        options = webdriver.ChromeOptions()
    else:
        options = uc.ChromeOptions()
    
    # Setup configurations similar to the working Headless project example
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--lang=en-US")
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    options.add_argument("--disable-notifications")
    options.add_argument("--mute-audio")
    
    # Disable images to speed up loading and evade some detection rules
    prefs = {"profile.managed_default_content_settings.images": 2}
    options.add_experimental_option("prefs", prefs)
    
    if headless:
        options.add_argument("--headless=new")
        
    if use_chrome_profile and has_chrome_profile_config():
        options.add_argument(f"--user-data-dir={CHROME_USER_DATA_DIR}")
        options.add_argument(f"--profile-directory={CHROME_PROFILE_DIRECTORY}")
        
    try:
        if headless:
            # Use standard Selenium for true invisible headless operation
            driver = webdriver.Chrome(options=options)
            return driver
        else:
            # Use undetected-chromedriver for headed mode (e.g. initial login)
            chrome_path = get_working_chrome_path()
            if chrome_path:
                driver = uc.Chrome(options=options, browser_executable_path=chrome_path, suppress_welcome=True)
            else:
                driver = uc.Chrome(options=options, suppress_welcome=True)
            return driver
    except Exception as error:
        print(f"[-] Failed to start undetected-chromedriver: {error}")
        raise


def wait_for_any(driver, locators, timeout=DEFAULT_WAIT_SECONDS):
    """Waits until one of the provided locators is visible."""
    def _condition(inner_driver):
        for by, selector in locators:
            elements = inner_driver.find_elements(by, selector)
            if any(element.is_displayed() for element in elements):
                return True
        return False

    WebDriverWait(driver, timeout).until(_condition)


def is_logged_in(driver, timeout=10):
    """Returns True when the authenticated navigation elements are visible."""
    cookie_names = {cookie["name"] for cookie in driver.get_cookies()}
    if AUTH_COOKIE_NAMES.issubset(cookie_names):
        return True

    try:
        wait_for_any(
            driver,
            [
                (By.XPATH, '//a[@href="/home"]'),
                (By.XPATH, '//a[@data-testid="AppTabBar_Home_Link"]'),
                (By.XPATH, '//a[contains(@href, "/compose/post")]'),
            ],
            timeout=timeout,
        )
        return True
    except TimeoutException:
        return False


def wait_for_manual_login(driver, timeout=DEFAULT_LOGIN_TIMEOUT_SECONDS, poll_seconds=2):
    """Waits until the user completes login and the auth session becomes available."""
    deadline = time.time() + timeout

    while time.time() < deadline:
        if is_logged_in(driver, timeout=2):
            return True
        time.sleep(poll_seconds)

    return False


def parse_args(argv):
    mode = "run"
    remaining_argv = list(argv)
    if remaining_argv and remaining_argv[0].lower() == "login":
        mode = "login"
        remaining_argv = remaining_argv[1:]

    parser = argparse.ArgumentParser(description="Twitter/X scraper for OSINT monitoring")
    parser.add_argument("keyword", nargs="?", default="phishing")
    parser.add_argument("--debug", action="store_true", help="Enable verbose debug logging and save debug artifacts")
    parser.add_argument("--show-browser", action="store_true", help="Show the browser window during scraping")
    parser.add_argument("--max-tweets", type=int, default=DEFAULT_MAX_TWEETS, help="Maximum tweets to collect per run")
    parser.add_argument(
        "--login-timeout",
        type=int,
        default=DEFAULT_LOGIN_TIMEOUT_SECONDS,
        help="Seconds to wait for manual login in login mode",
    )
    args = parser.parse_args(remaining_argv)
    args.mode = mode
    return args


def normalize_cookie(cookie):
    """Drops unsupported cookie fields before loading them into Selenium."""
    normalized = {
        k: v
        for k, v in cookie.items()
        if k not in {"sameSite", "storeId", "hostOnly", "session", "expirationDate"}
    }
    expiry_value = cookie.get("expiry", cookie.get("expirationDate"))
    if expiry_value is not None:
        normalized["expiry"] = int(expiry_value)
    return normalized


def get_twitter_search_url(keyword):
    encoded_keyword = quote_plus(keyword)
    return f"{BASE_URL}/search?q={encoded_keyword}&src=typed_query&f=live"


def save_cookies(driver):
    with open(COOKIES_FILE, "w", encoding="utf-8") as file:
        json.dump(driver.get_cookies(), file, ensure_ascii=False, indent=2)


def load_cookies():
    if os.path.exists(COOKIES_FILE):
        with open(COOKIES_FILE, "r", encoding="utf-8") as file:
            return json.load(file)

    if os.path.exists(LEGACY_COOKIES_FILE):
        with open(LEGACY_COOKIES_FILE, "rb") as file:
            return pickle.load(file)

    return None


def scroll_results(driver, rounds=DEFAULT_SCROLL_ROUNDS, pause_seconds=2):
    """Scrolls the page gradually to load additional live search results."""
    last_height = driver.execute_script("return document.body.scrollHeight")

    for _ in range(rounds):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pause_seconds)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height


def wait_for_tweets(driver, timeout=DEFAULT_WAIT_SECONDS, debug_enabled=False):
    """Polls the search page until tweet cards are rendered."""
    deadline = time.time() + timeout
    attempts = 0

    while time.time() < deadline:
        attempts += 1
        tweets = driver.find_elements(By.XPATH, '//article[@data-testid="tweet"]')
        if tweets:
            debug_log(debug_enabled, f"Tweet cards rendered after {attempts} polling attempts")
            return tweets

        latest_tab_visible = bool(
            driver.find_elements(By.XPATH, '//a[contains(@href, "search?") and contains(@href, "f=live")]')
        )
        debug_log(debug_enabled, f"Polling for tweets. attempt={attempts}, latest_tab_visible={latest_tab_visible}")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

    raise TimeoutException("Tweet cards were not rendered before timeout")


def extract_username_from_link(post_link):
    path_parts = [part for part in urlparse(post_link).path.split("/") if part]
    if len(path_parts) >= 3 and path_parts[1] == "status":
        return f"@{path_parts[0]}"
    return "unknown"


def extract_tweet_data(tweet):
    """Extracts the required fields from a tweet article element."""
    try:
        time_element = tweet.find_element(By.XPATH, './/time')
        link_element = time_element.find_element(By.XPATH, './..')
        post_link = link_element.get_attribute("href")
    except NoSuchElementException:
        return None 

    try:
        post_text = tweet.find_element(By.XPATH, './/div[@data-testid="tweetText"]').text.strip()
    except NoSuchElementException:
        post_text = ""

    if not post_link or not post_text:
        return None

    return {
        "platform": "Twitter",
        "username": extract_username_from_link(post_link),
        "post_text": post_text,
        "timestamp": time_element.get_attribute("datetime"),
        "post_link": post_link,
    }


def handle_login(
    driver,
    allow_manual_login=True,
    manual_login_timeout=DEFAULT_LOGIN_TIMEOUT_SECONDS,
    use_chrome_profile=True,
    debug_enabled=False,
):
    """
    מטפל בהתחברות. אם אין עוגיות ואנחנו במצב מוסתר (Headless), הפונקציה תכשיל את ההרצה
    ותדרוש מהמשתמש להתחבר קודם בצורה גלויה.
    """
    driver.get(BASE_URL)

    cookies = load_cookies()
    if cookies:
        print(f"[*] Using cookies from {COOKIES_FILE}...")
        debug_log(debug_enabled, f"Loaded {len(cookies)} cookies from disk")
        for cookie in cookies:
            try:
                driver.add_cookie(normalize_cookie(cookie))
            except Exception:
                pass

        print("[*] Cookies loaded. Refreshing page...")
        driver.refresh()
        if is_logged_in(driver, timeout=DEFAULT_WAIT_SECONDS):
            debug_log(debug_enabled, "Authenticated session restored from cookies")
            return True

        print("[!] Saved cookies appear to be expired or invalid.")
        save_debug_artifacts(driver, "invalid_cookies", debug_enabled)

    if use_chrome_profile and has_chrome_profile_config():
        print(f"[*] Using Chrome profile session from: {CHROME_USER_DATA_DIR} ({CHROME_PROFILE_DIRECTORY})")
        if is_logged_in(driver, timeout=DEFAULT_WAIT_SECONDS):
            debug_log(debug_enabled, "Authenticated session restored from Chrome profile")
            return True

        print("[!] Chrome profile opened, but no active X session was found in that profile.")
        save_debug_artifacts(driver, "profile_without_session", debug_enabled)
        return False

    else:
        print(f"[!] Cookies file '{COOKIES_FILE}' not found or invalid.")

    if not allow_manual_login:
        print("[-] Cannot perform manual login in headless mode.")
        print("[!] Action Required: Please run 'python scraper.py login' first to generate cookies.")
        return False

    print(f"[!] Please log in manually. Waiting up to {manual_login_timeout} seconds...")
    driver.get(f"{BASE_URL}/login")
    save_debug_artifacts(driver, "login_page", debug_enabled)

    if not wait_for_manual_login(driver, timeout=manual_login_timeout):
        print("[-] Manual login was not completed successfully.")
        save_debug_artifacts(driver, "login_timeout", debug_enabled)
        return False
    
    print("[*] Saving cookies for next time...")
    save_cookies(driver)
    print(f"[+] Cookies saved successfully to {COOKIES_FILE}!")
    debug_log(debug_enabled, f"Fresh cookies stored in {COOKIES_FILE}")

    return True


def create_cookies_file(manual_login_timeout=DEFAULT_LOGIN_TIMEOUT_SECONDS, debug_enabled=False):
    """Opens X login visibly, waits for a real session, and saves fresh cookies to disk."""
    driver = create_driver(use_chrome_profile=False, headless=False)
    try:
        if not handle_login(
            driver,
            allow_manual_login=True,
            manual_login_timeout=manual_login_timeout,
            use_chrome_profile=False,
            debug_enabled=debug_enabled,
        ):
            return False
        return True
    finally:
        print("[*] Closing browser...")
        driver.quit()


def fetch_twitter_posts(
    keyword,
    max_tweets=DEFAULT_MAX_TWEETS,
    debug_enabled=False,
    headless=True,
):
    """
    מושך פוסטים מטוויטר. כברירת מחדל רץ באופן מוסתר (Headless).
    """
    print(f"[*] Starting Selenium to search Twitter for: '{keyword}'...")

    use_chrome_profile = not bool(load_cookies())
    driver = create_driver(use_chrome_profile=use_chrome_profile, headless=headless)
    posts_data = []
    seen_links = set()
    
    try:
        allow_manual_login = not headless

        if not handle_login(
            driver,
            allow_manual_login=allow_manual_login,
            use_chrome_profile=use_chrome_profile,
            debug_enabled=debug_enabled,
        ):
            print("[-] Unable to establish a logged-in Twitter session. Aborting scrape.")
            return posts_data
        
        search_url = get_twitter_search_url(keyword)
        print(f"[*] Navigating to search page: {search_url}")
        driver.get(search_url)
        debug_log(debug_enabled, f"Current URL after search navigation: {driver.current_url}")
        
        try:
            WebDriverWait(driver, DEFAULT_WAIT_SECONDS).until(
                EC.presence_of_element_located((By.XPATH, '//div[@data-testid="primaryColumn"]'))
            )
            tweets = wait_for_tweets(driver, timeout=DEFAULT_WAIT_SECONDS, debug_enabled=debug_enabled)
        except TimeoutException:
            print("[-] Timed out while waiting for Twitter search results. Twitter might be blocking headless browsers.")
            save_debug_artifacts(driver, "timeout_waiting_for_results", debug_enabled)
            return posts_data

        print("[*] Scrolling to load tweets...")
        scroll_results(driver)
        
        tweets = driver.find_elements(By.XPATH, '//article[@data-testid="tweet"]') or tweets
        print(f"[*] Found {len(tweets)} tweets on screen. Extracting data...")
        
        for tweet in tweets:
            try:
                tweet_data = extract_tweet_data(tweet)
                if not tweet_data:
                    continue

                if tweet_data["post_link"] in seen_links:
                    continue

                seen_links.add(tweet_data["post_link"])
                posts_data.append(tweet_data)

                if len(posts_data) >= max_tweets:
                    break
            except NoSuchElementException:
                continue

    except Exception as e:
        print(f"[-] Selenium Error encountered: {e}")
        save_debug_artifacts(driver, "selenium_error", debug_enabled)
    finally:
        print("[*] Closing headless browser...")
        try:
            driver.quit()
        except:
            pass
        try:
            driver.__class__.__del__ = lambda self: None
        except:
            pass
        
    return posts_data

def run_scraper(keyword, max_tweets=DEFAULT_MAX_TWEETS, debug_enabled=False, headless=True):
    """
    מפעילה את החיפוש ומעבירה את התוצאות לשמירה במסד הנתונים.
    """
    database.setup_database()
    posts = fetch_twitter_posts(
        keyword,
        max_tweets=max_tweets,
        debug_enabled=debug_enabled,
        headless=headless,
    )
    new_posts_count = 0

    for post in posts:
        success = database.insert_post(
            platform=post["platform"],
            username=post["username"],
            post_text=post["post_text"],
            timestamp=post["timestamp"],
            post_link=post["post_link"]
        )
        
        if success:
            new_posts_count += 1

    print(f"[*] Scraper cycle finished. Added {new_posts_count} new posts.\n")


if __name__ == "__main__":
    args = parse_args(sys.argv[1:])

    if args.mode == "login":
        print("[*] Login mode: Opening visible browser to generate fresh cookies...")
        create_cookies_file(manual_login_timeout=args.login_timeout, debug_enabled=args.debug)
        raise SystemExit(0)

    is_headless = not args.show_browser
    
    if has_chrome_profile_config():
        print("[*] Chrome profile auto-login is enabled.")
    
    if is_headless:
        print("[*] Running in HEADLESS mode (invisible browser).")
    else:
        print("[*] Running in VISIBLE mode.")

    run_scraper(
        args.keyword,
        max_tweets=args.max_tweets,
        debug_enabled=args.debug,
        headless=is_headless,
    )