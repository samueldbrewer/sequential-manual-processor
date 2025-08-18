#!/usr/bin/env python3
"""
Fetch manuals by navigating to the Manuals tab specifically
More reliable approach that clicks on the manuals tab
"""

import subprocess
import json
import sys

def fetch_manuals_from_tab(manufacturer_uri, model_code):
    """Fetch manuals by navigating to the manuals tab"""
    
    import sys
    print(f"[fetch_manuals_from_tab] Called with: manufacturer_uri={manufacturer_uri}, model_code={model_code}", file=sys.stderr)
    
    # Python code to run in subprocess
    script = f"""
import asyncio
from playwright.async_api import async_playwright
import json
import sys

async def fetch():
    # URL with manuals tab hash
    model_url = "https://www.partstown.com/{manufacturer_uri}/{model_code}/parts#id=mdptabmanuals"
    
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
        
        # Navigate directly to manuals tab
        print(f"DEBUG: Navigating to {{model_url}}", file=sys.stderr)
        await page.goto(model_url, wait_until='networkidle', timeout=45000)
        
        # Wait a bit for tab content to load
        await page.wait_for_timeout(2000)  # Reduced for faster testing
        
        # Debug: Check page title
        title = await page.title()
        print(f"DEBUG: Page title: {{title}}", file=sys.stderr)
        
        # Try multiple selectors for manual links
        manuals = []
        
        # Method 1: Look for links in the manuals tab content area
        manual_selectors = [
            'div#mdptabmanuals a[href*="/modelManual/"]',
            'div.manuals-tab a[href*="/modelManual/"]',
            'div.tab-content a[href*="/modelManual/"]',
            'a.manual-link',
            'a[href*=".pdf"]'
        ]
        
        for selector in manual_selectors:
            try:
                links = await page.query_selector_all(selector)
                print(f"DEBUG: Selector '{{selector}}' found {{len(links)}} links", file=sys.stderr)
                if links:
                    for link in links:
                        href = await link.get_attribute('href')
                        text = await link.text_content()
                        
                        if href and '/modelManual/' in href:
                            # Extract manual type from filename
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
                            
                            # Check if not already added
                            if not any(m['link'] == href for m in manuals):
                                manuals.append({{
                                    'type': manual_type,
                                    'title': title,
                                    'link': href,
                                    'text': text.strip() if text else title
                                }})
                    
                    if manuals:
                        break
            except:
                pass
        
        # Method 2: If no manuals found, try clicking the manuals tab first
        if not manuals:
            # Try to click the manuals tab
            tab_selectors = [
                'a[href="#id=mdptabmanuals"]',
                'button:has-text("Manuals")',
                'li:has-text("Manuals")',
                'div.tab:has-text("Manuals")'
            ]
            
            for selector in tab_selectors:
                try:
                    tab = await page.query_selector(selector)
                    if tab:
                        await tab.click()
                        await page.wait_for_timeout(2000)
                        break
                except:
                    pass
            
            # Now look for manual links again
            manual_links = await page.query_selector_all('a[href*="/modelManual/"]')
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
                    
                    if not any(m['link'] == href for m in manuals):
                        manuals.append({{
                            'type': manual_type,
                            'title': title,
                            'link': href,
                            'text': text.strip() if text else title
                        }})
        
        print(json.dumps(manuals))
        return manuals
        
    except Exception as e:
        import traceback
        print(f"ERROR: {{str(e)}}", file=sys.stderr)
        print(f"TRACEBACK: {{traceback.format_exc()}}", file=sys.stderr)
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
        print(f"[fetch_manuals_from_tab] Starting subprocess for {manufacturer_uri}/{model_code}", file=sys.stderr)
        # Run the script in a subprocess with increased timeout
        result = subprocess.run(
            [sys.executable, '-c', script],
            capture_output=True,
            text=True,
            timeout=60  # Increased from 30 to 60 seconds
        )
        
        print(f"[fetch_manuals_from_tab] Subprocess completed. stdout={bool(result.stdout)}, stderr={bool(result.stderr)}", file=sys.stderr)
        
        if result.stderr:
            print(f"[fetch_manuals_from_tab] Subprocess stderr:\n{result.stderr}", file=sys.stderr)
        
        if result.stdout:
            try:
                manuals = json.loads(result.stdout.strip())
                print(f"[fetch_manuals_from_tab] Successfully parsed {len(manuals)} manuals", file=sys.stderr)
                return manuals
            except json.JSONDecodeError as e:
                print(f"[fetch_manuals_from_tab] Failed to parse output: {result.stdout[:200]}", file=sys.stderr)
                print(f"[fetch_manuals_from_tab] JSON error: {e}", file=sys.stderr)
                return []
        else:
            print(f"[fetch_manuals_from_tab] No output from subprocess. stderr: {result.stderr}", file=sys.stderr)
            return []
            
    except subprocess.TimeoutExpired:
        print(f"[fetch_manuals_from_tab] ERROR: Subprocess timed out for {manufacturer_uri}/{model_code}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"[fetch_manuals_from_tab] ERROR: Subprocess error for {manufacturer_uri}/{model_code}: {e}", file=sys.stderr)
        return []

if __name__ == "__main__":
    # Test with Henny Penny 500
    manuals = fetch_manuals_from_tab("henny-penny", "500")
    print(f"Found {len(manuals)} manuals")
    print(json.dumps(manuals, indent=2))