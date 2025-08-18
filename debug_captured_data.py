#!/usr/bin/env python3
"""
Debug the captured data from part-predictor API to find manufacturer prefixes and model codes
"""

import asyncio
import sys
import os
import json

# Add the scraper to the path
sys.path.append('../API Scraper V2')

# Create a modified version of the scraper that exposes captured data
class DebuggingExplorer:
    def __init__(self):
        self.base_url = "https://www.partstown.com"
        import time
        self.timestamp = str(int(time.time() * 1000))
        self.captured_data = []
    
    async def debug_henny_penny_data(self):
        """Debug what data we're actually capturing"""
        from playwright.async_api import async_playwright
        
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
        try:
            # Capture network responses
            async def capture_api_calls(response):
                url = response.url
                if ('application/json' in response.headers.get('content-type', '')):
                    try:
                        if response.ok:
                            data = await response.json()
                            
                            # Capture ALL relevant data, not just models
                            if any(keyword in url for keyword in ['/part-predictor/', '/models', '/manufacturers', '/api/']):
                                print(f"\n🔍 CAPTURED: {url}")
                                print(f"   Data type: {type(data).__name__}, Length: {len(data) if isinstance(data, list) else 'N/A'}")
                                
                                self.captured_data.append({
                                    'url': url,
                                    'data': data
                                })
                                
                                # Show sample data structure
                                if isinstance(data, list) and len(data) > 0:
                                    print(f"   First item: {json.dumps(data[0], indent=2)}")
                                elif isinstance(data, dict):
                                    print(f"   Dict keys: {list(data.keys())}")
                                    if len(data) < 5:  # Small dict, show all
                                        print(f"   Full data: {json.dumps(data, indent=2)}")
                    except Exception as e:
                        print(f"   ❌ Error parsing: {e}")
            
            page.on('response', capture_api_calls)
            
            # Navigate to manufacturer endpoint first
            print("🏭 Fetching manufacturers data...")
            mfg_url = f"{self.base_url}/api/manufacturers/?v={self.timestamp}"
            await page.goto(mfg_url, timeout=30000)
            await asyncio.sleep(1)
            
            # Navigate to Henny Penny models page
            print("\n🔧 Fetching Henny Penny models...")
            models_url = f"{self.base_url}/henny-penny/parts?v={self.timestamp}&narrow=#id=mdptabmodels"
            await page.goto(models_url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(2)
            
            # Try part-predictor endpoint directly
            print("\n🎯 Trying part-predictor endpoint...")
            predictor_url = f"{self.base_url}/part-predictor/PT_CAT1095/models"
            await page.goto(predictor_url, timeout=30000)
            await asyncio.sleep(2)
            
            # Now analyze all captured data
            print(f"\n{'='*60}")
            print(f"ANALYSIS OF CAPTURED DATA")
            print(f"{'='*60}")
            
            for i, capture in enumerate(self.captured_data):
                print(f"\n--- Capture {i+1}: {capture['url']} ---")
                data = capture['data']
                
                if isinstance(data, list) and len(data) > 0:
                    item = data[0]
                    if isinstance(item, dict):
                        print(f"🔍 Sample item fields: {list(item.keys())}")
                        
                        # Look for manufacturer prefix clues
                        for key, value in item.items():
                            if isinstance(value, str) and len(value) < 10:
                                if any(keyword in key.lower() for keyword in ['prefix', 'abbr', 'short', 'code']):
                                    print(f"   🎯 POTENTIAL PREFIX: {key} = {value}")
                        
                        # Look for detailed model code clues
                        for key, value in item.items():
                            if isinstance(value, str):
                                if any(keyword in key.lower() for keyword in ['model', 'part', 'sku', 'product']):
                                    print(f"   🔧 POTENTIAL MODEL CODE: {key} = {value}")
        
        finally:
            await browser.close()
            await playwright.stop()

async def main():
    debugger = DebuggingExplorer()
    await debugger.debug_henny_penny_data()

if __name__ == "__main__":
    asyncio.run(main())