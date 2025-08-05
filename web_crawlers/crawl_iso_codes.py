from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
import os

CSV_PATH = "..data/cleaned_ICS.csv" 

def accept_cookies(page):
    try:
        btn = page.locator('text="Accept All"')
        if btn.count():
            btn.click()
    except Exception:
        pass

def code_list():
    df = pd.read_csv(CSV_PATH)
    return df.identifier.tolist()

def extract_code_and_title(full_list):
    result = []
    for line in full_list:
        match = re.match(r'(ISO(?:/IEC)?\s?\d+(?:-\d+)?:\d{4})\s*(.*)', line)
        if match:
            code = match.group(1)
            title = match.group(2).strip()
            result.append({'code': code, 'title': title})
    return result

def already_scraped_codes(csv_path):
    if os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path)
            return set(df['code'].tolist())
        except Exception:
            return set()
    else:
        return set()

CSV_PATH = "iso_codes_and_titles.csv"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    # Go to the ISO homepage once
    page.goto('https://www.iso.org/home.html')
    accept_cookies(page)

    codes = code_list()
    scraped = already_scraped_codes(CSV_PATH)
    print(f"Already scraped {len(scraped)} codes.")

    for idx, code in enumerate(codes):
        if code in scraped:
            print(f"[{idx+1}/{len(codes)}] Skipping already scraped: {code}")
            continue

        print(f"[{idx+1}/{len(codes)}] Processing: {code}")
        try:
            page.fill('input[type="search"]', code)
            page.keyboard.press('Enter')
            accept_cookies(page)
            page.wait_for_selector(f'a:has-text("{code}")', timeout=15000)
            accept_cookies(page)
            page.click(f'a:has-text("{code}")')
            page.wait_for_load_state('networkidle')
            accept_cookies(page)

            # FILTERS
            if not page.locator('input#statusP').is_checked():
                page.locator('input#statusP').check()
            if page.locator('input#statusU').is_checked():
                page.locator('input#statusU').uncheck()
            if page.locator('input#statusW').count() > 0 and page.locator('input#statusW').is_checked():
                page.locator('input#statusW').uncheck()
            if page.locator('input#statusD').count() > 0 and page.locator('input#statusD').is_checked():
                page.locator('input#statusD').uncheck()

            page.wait_for_load_state('networkidle')
            page.wait_for_timeout(2000)

            html = page.content()
            soup = BeautifulSoup(html, "html.parser")

            iso_codes = []
            parent_div = soup.find('div', class_="d-xs-flex justify-content-between align-items-center col-12 dt-layout-full col-xs")
            if parent_div:
                table = parent_div.find('table', class_="table responsive-table searchable dataTable")
                if table:
                    rows = table.find_all('tr')
                    for row in rows[1:]:
                        cells = row.find_all(['th', 'td'])
                        if cells and len(cells) > 1:
                            stage = cells[1].get_text(strip=True)
                            if stage == "60.60": # Extracting only the Published ones
                                iso_codes.append(cells[0].get_text(strip=True))
                else:
                    print("Table not found in div.")
            else:
                print("Div not found.")

            code_title_list = extract_code_and_title(iso_codes)
            if code_title_list:
                df = pd.DataFrame(code_title_list)
                # Only write header if the file doesn't exist yet
                write_header = not os.path.exists(CSV_PATH)
                df.to_csv(CSV_PATH, mode='a', header=write_header, index=False, encoding="utf-8")
            else:
                print(f"No published standards found for {code}")

        except Exception as e:
            print(f"Error processing code {code}: {e}")

        time.sleep(2)  # Be nice to ISO's server!

    browser.close()
