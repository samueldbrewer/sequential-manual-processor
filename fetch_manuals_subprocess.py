#!/usr/bin/env python3
"""
Manual fetcher that runs in a subprocess to avoid event loop conflicts
"""

import subprocess
import json
import sys

def fetch_manuals_for_model(manufacturer_uri, model_code):
    """Fetch manuals by running the async scraper in a subprocess"""
    
    # Python code to run in subprocess
    script = f"""
import asyncio
from playwright.async_api import async_playwright
import json

async def fetch():
    model_url = "https://www.partstown.com/{manufacturer_uri}/{model_code}/parts"
    
    playwright = None
    browser = None
    
    try:
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            viewport={{'width': 1920, 'height': 1080}}
        )
        page = await context.new_page()
        
        await page.goto(model_url, wait_until='domcontentloaded', timeout=30000)
        await page.wait_for_timeout(2000)
        
        manual_links = await page.query_selector_all('a[href*="/modelManual/"]')
        
        manuals = []
        for link in manual_links:
            href = await link.get_attribute('href')
            text = await link.text_content()
            
            if href:
                if '_spm.' in href:
                    manual_type = 'spm'
                    title = 'Service & Parts Manual'
                elif '_iom.' in href:
                    manual_type = 'iom'
                    title = 'Installation & Operation Manual'
                elif '_pm.' in href:
                    manual_type = 'pm'
                    title = 'Parts Manual'
                elif '_wd.' in href:
                    manual_type = 'wd'
                    title = 'Wiring Diagrams'
                elif '_sm.' in href:
                    manual_type = 'sm'
                    title = 'Service Manual'
                else:
                    manual_type = 'unknown'
                    title = text.strip() if text else 'Manual'
                
                manuals.append({{
                    'type': manual_type,
                    'title': title,
                    'link': href,
                    'text': text.strip() if text else title
                }})
        
        print(json.dumps(manuals))
        return manuals
        
    except Exception as e:
        print(json.dumps([]))
        return []
    
    finally:
        if browser:
            await browser.close()
        if playwright:
            await playwright.stop()

asyncio.run(fetch())
"""
    
    try:
        # Run the script in a subprocess
        result = subprocess.run(
            [sys.executable, '-c', script],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.stdout:
            try:
                manuals = json.loads(result.stdout.strip())
                return manuals
            except json.JSONDecodeError:
                print(f"Failed to parse output: {result.stdout}")
                return []
        else:
            print(f"No output from subprocess. Error: {result.stderr}")
            return []
            
    except subprocess.TimeoutExpired:
        print("Subprocess timed out")
        return []
    except Exception as e:
        print(f"Subprocess error: {e}")
        return []

if __name__ == "__main__":
    # Test
    manuals = fetch_manuals_for_model("apw-wyott", "at-10")
    print(f"Found {len(manuals)} manuals")
    print(json.dumps(manuals, indent=2))