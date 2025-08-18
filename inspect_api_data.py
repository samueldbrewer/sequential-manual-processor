#!/usr/bin/env python3
"""
Inspect the raw API responses to find manufacturer prefixes and proper model codes
"""

import asyncio
import sys
import os
import json

# Add the scraper to the path
sys.path.append('../API Scraper V2')
from interactive_scraper import PartsTownExplorer

class DataInspector(PartsTownExplorer):
    def __init__(self):
        super().__init__()
        self.captured_responses = []
    
    async def inspect_api_responses(self):
        """Modified version to capture and inspect all API responses"""
        
        playwright = None
        browser = None
        context = None
        page = None
        
        try:
            from playwright.async_api import async_playwright
            playwright = await async_playwright().start()
            
            browser = await playwright.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                viewport={'width': 1920, 'height': 1080}
            )
            page = await context.new_page()
            
            # Capture ALL network responses for inspection
            def capture_response(response):
                try:
                    if any(keyword in response.url for keyword in ['api', 'models', 'manufacturers', 'part-predictor']):
                        print(f"\n🔍 CAPTURED: {response.url}")
                        
                        if response.ok:
                            try:
                                data = response.json()
                                self.captured_responses.append({
                                    'url': response.url,
                                    'data': data
                                })
                                
                                # Show preview of data structure
                                if isinstance(data, list) and len(data) > 0:
                                    print(f"   📊 List with {len(data)} items")
                                    print(f"   📋 First item keys: {list(data[0].keys()) if isinstance(data[0], dict) else 'Not a dict'}")
                                    if isinstance(data[0], dict):
                                        print(f"   🔍 First item sample: {json.dumps(data[0], indent=2)[:300]}...")
                                elif isinstance(data, dict):
                                    print(f"   📊 Dict with keys: {list(data.keys())}")
                                    print(f"   🔍 Sample: {json.dumps(data, indent=2)[:300]}...")
                            except Exception as e:
                                print(f"   ❌ Error parsing JSON: {e}")
                except Exception as e:
                    print(f"❌ Error capturing response: {e}")
            
            page.on('response', capture_response)
            
            print("🔧 Fetching Henny Penny data to inspect API responses...")
            await self.get_models_for_manufacturer('henny-penny', 'PT_CAT1095')
            
            print(f"\n📊 Captured {len(self.captured_responses)} API responses")
            
            # Now let's examine each response for prefixes and model codes
            for i, response in enumerate(self.captured_responses):
                print(f"\n{'='*60}")
                print(f"Response {i+1}: {response['url']}")
                print(f"{'='*60}")
                
                data = response['data']
                
                # Look for manufacturer prefixes
                if 'manufacturers' in response['url']:
                    print("🏭 MANUFACTURER DATA FOUND!")
                    if isinstance(data, list):
                        for mfg in data[:3]:  # Show first 3
                            print(f"   {json.dumps(mfg, indent=2)}")
                            # Look for prefix fields
                            if isinstance(mfg, dict):
                                potential_prefix_keys = [k for k in mfg.keys() if 'prefix' in k.lower() or 'code' in k.lower() or 'abbr' in k.lower()]
                                if potential_prefix_keys:
                                    print(f"   🎯 Potential prefix keys: {potential_prefix_keys}")
                
                # Look for detailed model data
                elif 'models' in response['url'] or 'part-predictor' in response['url']:
                    print("🔧 MODEL DATA FOUND!")
                    if isinstance(data, list) and len(data) > 0:
                        model = data[0]
                        print(f"   📋 Full model structure: {json.dumps(model, indent=2)}")
                        
                        # Look for fields that might contain proper model codes
                        if isinstance(model, dict):
                            potential_code_keys = [k for k in model.keys() if any(keyword in k.lower() for keyword in ['code', 'id', 'part', 'model', 'sku'])]
                            print(f"   🎯 Potential model code keys: {potential_code_keys}")
                            for key in potential_code_keys:
                                print(f"      {key}: {model.get(key)}")
                
        finally:
            if page:
                await page.close()
            if context:
                await context.close()
            if browser:
                await browser.close()
            if playwright:
                await playwright.stop()

async def main():
    inspector = DataInspector()
    await inspector.inspect_api_responses()

if __name__ == "__main__":
    asyncio.run(main())