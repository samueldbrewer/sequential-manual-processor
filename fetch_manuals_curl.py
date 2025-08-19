#!/usr/bin/env python3
"""
Fast manual fetching using curl subprocess
Much faster and simpler than Playwright
"""

import subprocess
import json
import re
import time
import os
import tempfile

def fetch_manuals_via_curl(manufacturer_uri, model_code):
    """Fetch manuals using curl command - fast and reliable"""
    
    url = f"https://www.partstown.com/{manufacturer_uri}/{model_code}/parts"
    
    # Always use curl - it works locally and should work on Railway too
    # Removed Playwright fallback due to library issues on Railway
    print(f"🔍 Using fast curl method for all environments", flush=True)
    
    # Create a unique cookie file for this request
    cookie_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
    cookie_path = cookie_file.name
    cookie_file.close()
    
    # Simplified curl command that actually works
    curl_cmd = [
        'curl',
        '-s',  # Silent mode
        '-H', 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        '-H', 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        '-H', 'Accept-Language: en-US,en;q=0.5',
        '--max-time', '10',  # 10 second timeout
        '-L',  # Follow redirects
        url
    ]
    
    try:
        start_time = time.time()
        print(f"🔍 Executing curl command: {' '.join(curl_cmd)}", flush=True)
        
        # Execute curl
        result = subprocess.run(
            curl_cmd,
            capture_output=True,
            text=True,
            timeout=15
        )
        
        elapsed = time.time() - start_time
        print(f"📊 Curl returned code {result.returncode} in {elapsed:.2f}s", flush=True)
        
        if result.returncode == 0 and result.stdout:
            print(f"📄 Got {len(result.stdout)} bytes of HTML", flush=True)
            
            # Check if we got a CloudFlare challenge or error page
            if "cloudflare" in result.stdout.lower() or "cf-ray" in result.stdout.lower():
                print(f"⚠️ CloudFlare detected in response", flush=True)
            if "<title>404" in result.stdout or "404 Not Found" in result.stdout:
                print(f"⚠️ 404 error page detected", flush=True)
            if len(result.stdout) < 10000:
                # Small page might be an error or challenge
                print(f"⚠️ Suspiciously small HTML response: {len(result.stdout)} bytes", flush=True)
                # Print first 500 chars to debug
                print(f"📝 First 500 chars: {result.stdout[:500]}", flush=True)
            
            # Extract manual links from HTML
            manual_pattern = r'/modelManual/([^"\']+\.pdf[^"\']*)'
            matches = re.findall(manual_pattern, result.stdout)
            print(f"🔎 Found {len(matches)} manual links in HTML", flush=True)
            
            # Remove duplicates and parse
            seen = set()
            manuals = []
            
            for match in matches:
                if match not in seen:
                    seen.add(match)
                    
                    # Full path
                    full_path = f"/modelManual/{match}"
                    
                    # Determine manual type from filename
                    if '_spm.' in match:
                        manual_type = 'spm'
                        title = 'Service & Parts Manual'
                    elif '_iom.' in match:
                        manual_type = 'iom'
                        title = 'Installation & Operation Manual'
                    elif '_pm.' in match:
                        manual_type = 'pm'
                        title = 'Parts Manual'
                    elif '_wd.' in match:
                        manual_type = 'wd'
                        title = 'Wiring Diagrams'
                    elif '_sm.' in match:
                        manual_type = 'sm'
                        title = 'Service Manual'
                    elif '_qrg.' in match:
                        manual_type = 'qrg'
                        title = 'Quick Reference Guide'
                    elif '_ts.' in match:
                        manual_type = 'ts'
                        title = 'Tech Sheet'
                    else:
                        manual_type = 'manual'
                        title = 'Manual'
                    
                    manuals.append({
                        'type': manual_type,
                        'title': title,
                        'link': full_path,
                        'text': title
                    })
            
            print(f"✅ Found {len(manuals)} manuals in {elapsed:.2f}s via curl", flush=True)
            # Clean up cookie file
            try:
                os.unlink(cookie_path)
            except:
                pass
            return manuals
            
        else:
            print(f"❌ Curl failed with return code {result.returncode}", flush=True)
            if result.stderr:
                print(f"   Error: {result.stderr}", flush=True)
            # Clean up cookie file
            try:
                os.unlink(cookie_path)
            except:
                pass
            return []
            
    except subprocess.TimeoutExpired:
        print(f"❌ Curl timeout for {manufacturer_uri}/{model_code}", flush=True)
        # Clean up cookie file
        try:
            os.unlink(cookie_path)
        except:
            pass
        return []
    except Exception as e:
        print(f"❌ Error running curl: {e}", flush=True)
        import traceback
        traceback.print_exc()
        # Clean up cookie file
        try:
            os.unlink(cookie_path)
        except:
            pass
        return []

def fetch_manuals_via_playwright(manufacturer_uri, model_code):
    """Fallback to Playwright for environments where curl is blocked"""
    try:
        from playwright.sync_api import sync_playwright
        
        url = f"https://www.partstown.com/{manufacturer_uri}/{model_code}/parts"
        print(f"🎭 Using Playwright to fetch {url}", flush=True)
        
        manuals = []
        
        with sync_playwright() as p:
            # Launch browser
            browser = p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            
            # Create context with browser-like settings
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            page = context.new_page()
            
            # Navigate to the page with more lenient settings
            print(f"📍 Navigating to {url}", flush=True)
            page.goto(url, wait_until='domcontentloaded', timeout=30000)
            
            # Wait for either manual links or a sign the page loaded
            try:
                # Wait for manual links to appear (max 5 seconds)
                page.wait_for_selector('a[href*="/modelManual/"]', timeout=5000)
                print(f"✅ Found manual links on page", flush=True)
            except:
                # If no manuals, at least wait for the page to stabilize
                print(f"⏳ No manual links found immediately, waiting for page to stabilize", flush=True)
                page.wait_for_timeout(3000)
            
            # Get all manual links
            manual_links = page.locator('a[href*="/modelManual/"]').all()
            
            seen = set()
            for link in manual_links:
                href = link.get_attribute('href')
                if href and href not in seen:
                    seen.add(href)
                    
                    # Parse the manual type from URL (case insensitive)
                    href_lower = href.lower()
                    if '_spm.' in href_lower or '_sm.' in href_lower:
                        manual_type = 'sm'
                        title = 'Service & Parts Manual' if '_spm.' in href_lower else 'Service Manual'
                    elif '_pm.' in href_lower:
                        manual_type = 'pm'
                        title = 'Parts Manual'
                    elif '_om.' in href_lower or '_iom.' in href_lower:
                        manual_type = 'om'
                        title = 'Installation & Operation Manual' if '_iom.' in href_lower else 'Operation Manual'
                    elif '_im.' in href_lower:
                        manual_type = 'im'
                        title = 'Installation Manual'
                    elif '_qrg.' in href_lower:
                        manual_type = 'qrg'
                        title = 'Quick Reference Guide'
                    elif '_ts.' in href_lower:
                        manual_type = 'ts'
                        title = 'Tech Sheet'
                    else:
                        manual_type = 'manual'
                        title = 'Manual'
                    
                    manuals.append({
                        'type': manual_type,
                        'title': title,
                        'link': href,
                        'text': title
                    })
            
            browser.close()
            
        print(f"✅ Found {len(manuals)} manuals via Playwright", flush=True)
        return manuals
        
    except Exception as e:
        print(f"❌ Playwright fallback failed: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return []

def test_performance():
    """Compare performance with Playwright approach"""
    
    test_cases = [
        ("henny-penny", "500"),
        ("globe", "2500"),
        ("pitco", "14"),
        ("frosty-factory", "113a"),
        ("pizzamaster", "pm351ed")
    ]
    
    print("="*60)
    print("CURL-BASED MANUAL FETCHING TEST")
    print("="*60)
    
    total_time = 0
    success_count = 0
    
    for manufacturer, model in test_cases:
        print(f"\nTesting {manufacturer}/{model}:")
        start = time.time()
        
        manuals = fetch_manuals_via_curl(manufacturer, model)
        
        elapsed = time.time() - start
        total_time += elapsed
        
        if manuals:
            success_count += 1
            print(f"  Time: {elapsed:.2f}s")
            for manual in manuals:
                print(f"  - {manual['title']}: {manual['link']}")
        else:
            print(f"  No manuals found")
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Success rate: {success_count}/{len(test_cases)} ({success_count*100/len(test_cases):.0f}%)")
    print(f"Average time: {total_time/len(test_cases):.2f}s")
    print(f"Total time: {total_time:.2f}s")
    print("\nCompared to Playwright (~5s per request):")
    print(f"Speed improvement: {5/(total_time/len(test_cases)):.1f}x faster")

if __name__ == "__main__":
    # Test single fetch
    print("Testing single fetch:")
    manuals = fetch_manuals_via_curl("henny-penny", "500")
    print(json.dumps(manuals, indent=2))
    
    print("\n")
    
    # Run performance test
    test_performance()