#!/usr/bin/env python3
"""
Live manual fetcher for models
Since manuals weren't cached, this fetches them on-demand
"""

import asyncio
import sys
import os
import json

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'API Scraper V2'))
from interactive_scraper import PartsTownExplorer

async def fetch_manuals_for_model(manufacturer_uri, model_code):
    """Fetch manuals for a specific model by scraping its page"""
    from playwright.async_api import async_playwright
    
    # Create URL for the model's parts page
    model_url = f"https://www.partstown.com/{manufacturer_uri}/{model_code}/parts"
    print(f"🔍 Fetching manuals from: {model_url}")
    
    playwright = None
    browser = None
    
    try:
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
        # Navigate to model page
        response = await page.goto(model_url, wait_until='domcontentloaded', timeout=30000)
        
        # Wait for page to load
        await page.wait_for_timeout(2000)
        
        # Look for manual links
        manual_links = await page.query_selector_all('a[href*="/modelManual/"]')
        
        manuals = []
        for link in manual_links:
            href = await link.get_attribute('href')
            text = await link.text_content()
            
            if href:
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
                
                manuals.append({
                    'type': manual_type,
                    'title': title,
                    'link': href,
                    'text': text.strip() if text else title
                })
        
        print(f"✅ Found {len(manuals)} manuals")
        return manuals
        
    except Exception as e:
        print(f"❌ Error fetching manuals: {e}")
        return []
    
    finally:
        if browser:
            await browser.close()
        if playwright:
            await playwright.stop()

async def main():
    # Test with APW Wyott AT-10
    manufacturer_uri = "apw-wyott"
    model_code = "at-10"
    
    manuals = await fetch_manuals_for_model(manufacturer_uri, model_code)
    print(json.dumps(manuals, indent=2))

if __name__ == "__main__":
    asyncio.run(main())