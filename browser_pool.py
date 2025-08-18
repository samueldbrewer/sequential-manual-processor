#!/usr/bin/env python3
"""
Browser Pool Manager for Playwright
Manages a pool of browser instances to handle concurrent requests safely
"""

import asyncio
import time
from typing import Optional, Dict, Any
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
import uuid

class BrowserPool:
    """Manages a pool of browser instances for concurrent requests"""
    
    def __init__(self, max_browsers: int = 3):
        self.max_browsers = max_browsers
        self.browsers: Dict[str, Dict[str, Any]] = {}
        self.lock = asyncio.Lock()
        self.playwright = None
        
    async def initialize(self):
        """Initialize the playwright instance"""
        if not self.playwright:
            self.playwright = await async_playwright().start()
    
    async def get_browser(self) -> tuple[str, Browser, BrowserContext, Page]:
        """Get or create a browser instance"""
        async with self.lock:
            # Initialize playwright if needed
            await self.initialize()
            
            # Clean up closed browsers
            closed_ids = []
            for browser_id, browser_data in self.browsers.items():
                try:
                    if browser_data['browser'].is_connected():
                        # Check if browser is idle (not used for 30 seconds)
                        if time.time() - browser_data['last_used'] > 30:
                            await browser_data['browser'].close()
                            closed_ids.append(browser_id)
                    else:
                        closed_ids.append(browser_id)
                except:
                    closed_ids.append(browser_id)
            
            for browser_id in closed_ids:
                del self.browsers[browser_id]
            
            # Create new browser if under limit
            if len(self.browsers) < self.max_browsers:
                browser_id = str(uuid.uuid4())[:8]
                print(f"🌐 Creating new browser instance {browser_id}")
                
                browser = await self.playwright.chromium.launch(
                    headless=True,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-gpu',
                        '--no-first-run',
                        '--no-zygote',
                        '--single-process'  # Important for preventing zombie processes
                    ]
                )
                
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                    viewport={'width': 1920, 'height': 1080}
                )
                
                page = await context.new_page()
                await page.set_extra_http_headers({
                    "X-Requested-With": "XMLHttpRequest",
                    "Accept": "application/json, text/plain, */*"
                })
                
                self.browsers[browser_id] = {
                    'browser': browser,
                    'context': context,
                    'page': page,
                    'last_used': time.time(),
                    'in_use': True
                }
                
                return browser_id, browser, context, page
            
            # Reuse existing browser
            for browser_id, browser_data in self.browsers.items():
                if not browser_data.get('in_use', False):
                    browser_data['in_use'] = True
                    browser_data['last_used'] = time.time()
                    
                    # Create new page for this request
                    page = await browser_data['context'].new_page()
                    await page.set_extra_http_headers({
                        "X-Requested-With": "XMLHttpRequest",
                        "Accept": "application/json, text/plain, */*"
                    })
                    
                    print(f"♻️ Reusing browser instance {browser_id}")
                    return browser_id, browser_data['browser'], browser_data['context'], page
            
            # All browsers in use, wait and retry
            print("⏳ All browsers in use, waiting...")
            await asyncio.sleep(1)
            return await self.get_browser()
    
    async def release_browser(self, browser_id: str, page: Optional[Page] = None):
        """Release a browser back to the pool"""
        async with self.lock:
            if browser_id in self.browsers:
                # Close the page if provided
                if page:
                    try:
                        await page.close()
                    except:
                        pass
                
                # Mark browser as available
                self.browsers[browser_id]['in_use'] = False
                self.browsers[browser_id]['last_used'] = time.time()
                print(f"🔓 Released browser {browser_id}")
    
    async def cleanup(self):
        """Clean up all browser instances"""
        async with self.lock:
            for browser_id, browser_data in self.browsers.items():
                try:
                    await browser_data['browser'].close()
                    print(f"🧹 Closed browser {browser_id}")
                except:
                    pass
            
            self.browsers.clear()
            
            if self.playwright:
                await self.playwright.stop()
                self.playwright = None
                print("✅ Playwright stopped")

# Global browser pool instance
browser_pool = BrowserPool(max_browsers=2)