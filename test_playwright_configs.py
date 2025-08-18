#!/usr/bin/env python3
"""
Test different Playwright configurations and timing strategies to successfully load models.
"""

import asyncio
import json
import time
from playwright.async_api import async_playwright

async def test_configuration(config_name, page_func, manufacturer_uri="henny-penny"):
    """Test a specific configuration"""
    print(f"\n{'='*60}")
    print(f"Testing: {config_name}")
    print(f"Manufacturer: {manufacturer_uri}")
    
    start_time = time.time()
    playwright = None
    browser = None
    
    try:
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process'
            ]
        )
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080},
            java_script_enabled=True,
            ignore_https_errors=True
        )
        
        # Add some cookies/headers to appear more legitimate
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        page = await context.new_page()
        
        # Call the specific test function
        models = await page_func(page, manufacturer_uri)
        
        elapsed = time.time() - start_time
        
        if models:
            print(f"✅ SUCCESS! Found {len(models)} models in {elapsed:.2f}s")
            print(f"   First 3 models: {models[:3]}")
            return {"success": True, "count": len(models), "time": elapsed, "models": models[:5]}
        else:
            print(f"❌ No models found ({elapsed:.2f}s)")
            return {"success": False, "count": 0, "time": elapsed}
            
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"❌ Error: {e} ({elapsed:.2f}s)")
        return {"success": False, "error": str(e), "time": elapsed}
    
    finally:
        if browser:
            await browser.close()
        if playwright:
            await playwright.stop()

async def strategy_1_wait_for_network(page, manufacturer_uri):
    """Strategy 1: Wait for network idle"""
    url = f"https://www.partstown.com/{manufacturer_uri}/parts"
    
    # Go to page and wait for network to be idle
    await page.goto(url, wait_until='networkidle', timeout=30000)
    
    # Extract models
    models = await page.evaluate("""
        () => {
            const links = document.querySelectorAll('a[href*="/parts"]');
            const models = [];
            links.forEach(link => {
                const href = link.getAttribute('href');
                if (href && href.includes('/' + arguments[0] + '/') && !href.endsWith('/parts')) {
                    const parts = href.split('/');
                    if (parts.length >= 3) {
                        const modelCode = parts[2];
                        if (modelCode && modelCode !== 'parts') {
                            models.push(modelCode);
                        }
                    }
                }
            });
            return [...new Set(models)];
        }
    """, manufacturer_uri)
    
    return models

async def strategy_2_wait_for_selector(page, manufacturer_uri):
    """Strategy 2: Wait for specific selectors"""
    url = f"https://www.partstown.com/{manufacturer_uri}/parts?v={int(time.time()*1000)}&narrow=#id=mdptabmodels"
    
    await page.goto(url, wait_until='domcontentloaded')
    
    # Wait for models tab or model links
    try:
        await page.wait_for_selector('[id="mdptabmodels"]', timeout=5000)
    except:
        pass
    
    # Wait a bit for Vue to render
    await page.wait_for_timeout(3000)
    
    # Try multiple selectors
    models = await page.evaluate("""
        () => {
            // Try different ways to find models
            let models = [];
            
            // Method 1: Look for model links
            document.querySelectorAll('a[href*="/parts"]').forEach(a => {
                const href = a.href;
                const match = href.match(/\/([^\/]+)\/([^\/]+)\/parts$/);
                if (match && match[2] !== 'parts') {
                    models.push(match[2]);
                }
            });
            
            // Method 2: Look for Vue data
            if (window.Vue && window.Vue.models) {
                models = models.concat(window.Vue.models);
            }
            
            // Method 3: Look for data attributes
            document.querySelectorAll('[data-model-code]').forEach(el => {
                models.push(el.getAttribute('data-model-code'));
            });
            
            return [...new Set(models)];
        }
    """)
    
    return models

async def strategy_3_click_models_tab(page, manufacturer_uri):
    """Strategy 3: Navigate to page then click models tab"""
    url = f"https://www.partstown.com/{manufacturer_uri}/parts"
    
    await page.goto(url, wait_until='domcontentloaded')
    await page.wait_for_timeout(2000)
    
    # Try to click models tab
    try:
        # Look for models tab and click it
        models_tab = await page.query_selector('text=Models')
        if models_tab:
            await models_tab.click()
            await page.wait_for_timeout(2000)
    except:
        pass
    
    # Extract models after clicking
    models = await page.evaluate("""
        () => {
            const models = [];
            // Check for model list items
            document.querySelectorAll('.model-item, .model-link, [class*="model"]').forEach(el => {
                const text = el.textContent.trim();
                if (text && !text.includes('Model') && text.length < 50) {
                    models.push(text);
                }
            });
            return [...new Set(models)];
        }
    """)
    
    return models

async def strategy_4_wait_for_vue(page, manufacturer_uri):
    """Strategy 4: Wait for Vue.js to load and check Vue components"""
    url = f"https://www.partstown.com/{manufacturer_uri}/parts"
    
    await page.goto(url, wait_until='domcontentloaded')
    
    # Wait for Vue to be available
    await page.wait_for_function("() => window.Vue !== undefined", timeout=10000)
    await page.wait_for_timeout(3000)  # Give Vue time to render
    
    # Try to access Vue data
    models = await page.evaluate("""
        () => {
            // Try to find Vue instances and their data
            const models = [];
            
            // Check for Vue components
            if (window.Vue) {
                // Look for Vue instances
                const vueElements = document.querySelectorAll('[data-v-]');
                console.log('Found Vue elements:', vueElements.length);
            }
            
            // Check __vue__ property on elements
            document.querySelectorAll('*').forEach(el => {
                if (el.__vue__ && el.__vue__.$data) {
                    const data = el.__vue__.$data;
                    if (data.models) {
                        models.push(...data.models);
                    }
                    if (data.modelList) {
                        models.push(...data.modelList);
                    }
                }
            });
            
            return models;
        }
    """)
    
    return models

async def strategy_5_intercept_requests(page, manufacturer_uri):
    """Strategy 5: Intercept network requests to find model API calls"""
    models = []
    
    # Intercept responses
    async def handle_response(response):
        if 'model' in response.url.lower() or 'parts' in response.url.lower():
            try:
                data = await response.json()
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and ('code' in item or 'modelCode' in item):
                            models.append(item.get('code') or item.get('modelCode'))
                elif isinstance(data, dict) and 'models' in data:
                    for model in data['models']:
                        if 'code' in model:
                            models.append(model['code'])
            except:
                pass
    
    page.on('response', handle_response)
    
    url = f"https://www.partstown.com/{manufacturer_uri}/parts"
    await page.goto(url, wait_until='networkidle')
    await page.wait_for_timeout(3000)
    
    return list(set(models))

async def strategy_6_scroll_and_wait(page, manufacturer_uri):
    """Strategy 6: Scroll page to trigger lazy loading"""
    url = f"https://www.partstown.com/{manufacturer_uri}/parts"
    
    await page.goto(url, wait_until='domcontentloaded')
    await page.wait_for_timeout(2000)
    
    # Scroll to trigger lazy loading
    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    await page.wait_for_timeout(2000)
    await page.evaluate("window.scrollTo(0, 0)")
    await page.wait_for_timeout(1000)
    
    # Look for models after scrolling
    models = await page.evaluate("""
        () => {
            const models = [];
            
            // Check all links
            document.querySelectorAll('a').forEach(a => {
                const href = a.getAttribute('href') || '';
                // Match pattern like /manufacturer/model/parts
                if (href.includes('/parts') && href.split('/').length === 4) {
                    const parts = href.split('/');
                    const model = parts[2];
                    if (model && model !== 'parts') {
                        models.push(model);
                    }
                }
            });
            
            return [...new Set(models)];
        }
    """)
    
    return models

async def main():
    print("=" * 70)
    print("TESTING PLAYWRIGHT CONFIGURATIONS FOR MODEL SCRAPING")
    print("=" * 70)
    
    # Test manufacturers
    test_manufacturers = [
        "henny-penny",  # Known to have models
        "american-water-heaters"  # Failed to get models
    ]
    
    strategies = [
        ("Wait for Network Idle", strategy_1_wait_for_network),
        ("Wait for Specific Selectors", strategy_2_wait_for_selector),
        ("Click Models Tab", strategy_3_click_models_tab),
        ("Wait for Vue.js", strategy_4_wait_for_vue),
        ("Intercept Network Requests", strategy_5_intercept_requests),
        ("Scroll and Wait", strategy_6_scroll_and_wait),
    ]
    
    results = {}
    
    for manufacturer in test_manufacturers:
        print(f"\n{'='*70}")
        print(f"TESTING MANUFACTURER: {manufacturer}")
        print(f"{'='*70}")
        
        results[manufacturer] = {}
        
        for strategy_name, strategy_func in strategies:
            result = await test_configuration(strategy_name, strategy_func, manufacturer)
            results[manufacturer][strategy_name] = result
            
            # Small delay between tests
            await asyncio.sleep(2)
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY OF RESULTS")
    print("=" * 70)
    
    for manufacturer, strategies in results.items():
        print(f"\n{manufacturer.upper()}:")
        for strategy, result in strategies.items():
            if result["success"]:
                print(f"  ✅ {strategy}: {result['count']} models in {result['time']:.2f}s")
            else:
                error = result.get('error', 'No models found')
                print(f"  ❌ {strategy}: {error} ({result['time']:.2f}s)")
    
    # Save results
    with open('playwright_config_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Detailed results saved to playwright_config_results.json")
    
    # Find best strategy
    best_strategy = None
    best_count = 0
    
    for strategy_name, _ in strategies:
        total_models = sum(
            results[mfg].get(strategy_name, {}).get('count', 0) 
            for mfg in test_manufacturers
        )
        if total_models > best_count:
            best_count = total_models
            best_strategy = strategy_name
    
    if best_strategy:
        print(f"\n🏆 BEST STRATEGY: {best_strategy} (total {best_count} models found)")

if __name__ == "__main__":
    asyncio.run(main())