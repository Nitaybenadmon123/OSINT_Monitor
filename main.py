import time
import os
import platform
import scraper
from datetime import datetime
import shutil
def clean_zombie_processes():
    """
    מנקה תהליכי דרייבר שנתקעו בזיכרון ומוחק את המטמון הפגום של הכרום הנסתר.
    """
    print("[*] Performing system cleanup (killing processes & clearing cache)...")
    if platform.system() == "Windows":
        # 1. הריגת תהליכים תקועים בזיכרון
        os.system("taskkill /f /im chromedriver.exe /t >nul 2>&1")
        
        # 2. מחיקת תיקיית המטמון הפגומה מ-AppData!
        appdata_path = os.environ.get('APPDATA')
        if appdata_path:
            uc_cache_dir = os.path.join(appdata_path, "undetected_chromedriver")
            if os.path.exists(uc_cache_dir):
                print("[*] Found corrupted Chrome cache. Deleting it...")
                try:
                    # מוחק את התיקייה וכל מה שבתוכה
                    shutil.rmtree(uc_cache_dir)
                    print("[+] Cache cleared successfully.")
                except Exception as e:
                    print(f"[-] Could not delete cache folder: {e}")

def main():
    print("="*60)
    print("🚀 RSecurity OSINT Continuous Monitor - Started")
    print("="*60)

    # מפעילים את הניקוי ממש בתחילת הריצה!
    clean_zombie_processes()

    keywords = ["malware", "phishing", "ransomware"]
    WAIT_MINUTES = 15

    while True:
        for keyword in keywords:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n[{current_time}] Starting automated scan for keyword: '{keyword}'")
            
            try:
                scraper.run_scraper(keyword=keyword, max_tweets=15, debug_enabled=False, headless=True)
            except Exception as e:
                print(f"[-] Error during automated scan for '{keyword}': {e}")
                # אם הייתה קריסה חמורה, ננקה שוב כדי שהמילה הבאה לא תיתקע!
                clean_zombie_processes()
            
            print("[*] Waiting 60 seconds before checking the next keyword...")
            time.sleep(60)
        
        print("\n" + "="*60)
        print(f"[*] Cycle complete. Waiting {WAIT_MINUTES} minutes before next run...")
        print("="*60)
        time.sleep(WAIT_MINUTES * 60)

if __name__ == "__main__":
    if not os.path.exists("twitter_cookies.json"):
        print("[!] ERROR: Cookies file not found.")
        print("    Please run 'python scraper.py login' first to authenticate.")
    else:
        main()