#!/usr/bin/env python3
"""
Test manual link scraping for a specific model
"""

import asyncio
import sys
import os
from playwright.async_api import async_playwright

async def test_manual_scraping():
    print("🔧 Testing manual link scraping for Henny Penny Model 500...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
        try:
            # Test URL for Henny Penny Model 500
            model_url = "https://www.partstown.com/henny-penny/500/parts"
            print(f"🌐 Navigating to: {model_url}")
            
            response = await page.goto(model_url, wait_until='domcontentloaded')
            print(f"📄 Status: {response.status}")
            
            # Wait for page to load
            await page.wait_for_timeout(2000)
            
            # Look for manual links - they might be in different formats:
            # 1. Direct links to PDFs
            # 2. Links containing "manual"
            # 3. Links with specific patterns
            
            print("\n🔍 Looking for manual links...")
            
            # Method 1: Look for direct PDF links
            pdf_links = await page.query_selector_all('a[href*=".pdf"]')
            if pdf_links:
                print(f"📄 Found {len(pdf_links)} PDF links:")
                for i, link in enumerate(pdf_links[:10]):  # Show first 10
                    href = await link.get_attribute('href')
                    text = await link.text_content()
                    print(f"   {i+1}. {text} → {href}")
            
            # Method 2: Look for links containing "manual"
            manual_links = await page.query_selector_all('a[href*="manual" i], a[href*="Manual" i]')
            if manual_links:
                print(f"\n📚 Found {len(manual_links)} manual-related links:")
                for i, link in enumerate(manual_links[:10]):
                    href = await link.get_attribute('href')
                    text = await link.text_content()
                    print(f"   {i+1}. {text} → {href}")
            
            # Method 3: Look for the specific modelManual pattern
            model_manual_links = await page.query_selector_all('a[href*="/modelManual/"]')
            if model_manual_links:
                print(f"\n🎯 Found {len(model_manual_links)} /modelManual/ links:")
                for i, link in enumerate(model_manual_links):
                    href = await link.get_attribute('href')
                    text = await link.text_content()
                    print(f"   {i+1}. {text} → {href}")
            
            # Method 4: Look for any download-related links
            download_links = await page.query_selector_all('a[href*="download" i], a[download], [class*="download" i]')
            if download_links:
                print(f"\n⬇️ Found {len(download_links)} download-related links:")
                for i, link in enumerate(download_links[:10]):
                    href = await link.get_attribute('href') or ''
                    text = await link.text_content() or ''
                    print(f"   {i+1}. {text.strip()} → {href}")
            
            # Method 5: Check page content for any indication of manuals
            page_content = await page.content()
            if 'manual' in page_content.lower():
                print(f"\n✅ Page contains 'manual' text - manuals likely available")
            else:
                print(f"\n❌ Page does not contain 'manual' text")
                
            # Method 6: Check for specific button or section that might reveal manuals
            manual_buttons = await page.query_selector_all('button:has-text("manual" i), [class*="manual" i]')
            if manual_buttons:
                print(f"\n🔘 Found {len(manual_buttons)} manual-related buttons/elements:")
                for i, button in enumerate(manual_buttons[:5]):
                    text = await button.text_content()
                    print(f"   {i+1}. {text}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_manual_scraping())