from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import pandas as pd
import json
import random
import time

CSV_PATH_IN = "../data/iso_codes_and_titles.csv" 
JSON_PATH_OUT = "../data/iso_docs.jsonl" 

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

def check_for_captcha(page):
    # Look for text or elements commonly found on CAPTCHA pages
    if (
        page.locator('text="verify you are human"').count() or
        page.locator('text="are you human"').count() or
        page.locator('iframe[src*="captcha"]').count() or
        page.locator('div[class*="captcha"]').count()
    ):
        print("CAPTCHA detected. Pausing for manual solve...")
        page.pause()

def accept_cookies(page):
    try:
        btn = page.locator('text="Accept All"')
        if btn.count():
            btn.click()
    except Exception:
        pass

def code_list():
    df = pd.read_csv(CSV_PATH_IN)
    return df['ISO Codes'].tolist()

def mouse_move(page, width=1280, height=800, moves=None):
    """
    Move the mouse randomly around the page to simulate human activity.
    """
    if moves is None:
        moves = random.randint(3, 8)
    for _ in range(moves):
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)
        steps = random.randint(5, 20)
        page.mouse.move(x, y, steps=steps)
        time.sleep(random.uniform(0.2, 1.0))

def random_scroll(page, times=None):
    """
    Randomly scrolls the page to simulate reading.
    """
    if times is None:
        times = random.randint(2, 5)
    for _ in range(times):
        scroll_y = random.randint(100, 600)
        page.evaluate(f"window.scrollBy(0, {scroll_y})")
        time.sleep(random.uniform(0.5, 1.5))

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    codes = code_list()

    iterator = 0 #6401 

    for idx, code in enumerate(codes[iterator:]): 
        print(f"[{iterator}/{len(codes)}] Processing: {code}")
        iterator+=1
        ua = random.choice(USER_AGENTS)  
        context = browser.new_context(user_agent=ua)
        page = context.new_page()
        try:
            page.goto('https://www.iso.org/home.html')
            check_for_captcha(page)
            accept_cookies(page)
            time.sleep(random.uniform(2, 5)) 
            mouse_move(page)
            page.fill('input[type="search"]', code)
            page.keyboard.press('Enter')
            accept_cookies(page)
            page.wait_for_selector(f'a:has-text("{code}")', timeout=15000)

            mouse_move(page)
            random_scroll(page)
            accept_cookies(page)
            page.click(f'a:has-text("{code}")')
            page.wait_for_load_state('networkidle')
            accept_cookies(page)
            page.wait_for_selector('a:has-text("Read sample"), button:has-text("Read sample")', timeout=15000)
            random_scroll(page)
            accept_cookies(page)
            time.sleep(random.uniform(2, 4))
            page.click('a:has-text("Read sample"), button:has-text("Read sample")')
            accept_cookies(page)
            random_scroll(page)

            page.wait_for_selector('div.sts-standard', timeout=20000)
            accept_cookies(page)
            mouse_move(page)
            html = page.content()
            soup = BeautifulSoup(html, "html.parser")

            sample_div = soup.find('div', class_="sts-standard")
            if sample_div:
                text = sample_div.get_text(separator='\n', strip=True) 
            else: 
                text = soup.get_text(separator='\n', strip=True)
            result = {"code": code, "text": text}
            with open(JSON_PATH_OUT, "a", encoding="utf-8") as f:
                f.write(json.dumps(result, ensure_ascii=False) + "\n")
            print(f"Saved {code}")

        except Exception as e:
            print(f"Error scraping {code}: {e}")
        finally:
            mouse_move(page)
            time.sleep(2) 
            context.close()

        time.sleep(random.uniform(5, 11))

        if (idx + 1) % 25 == 0:
            print("Taking a long break...")
            time.sleep(random.uniform(300, 600)) 

    browser.close()
    print('Completed')

