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
    
    # Check if we're running on Railway (has PORT env var set to non-8888 value)
    port = os.environ.get('PORT', '8888')
    is_railway = port != '8888'
    
    print(f"🔍 Environment check: PORT={port}, is_railway={is_railway}", flush=True)
    
    if is_railway:
        print(f"🌐 Running on Railway, using Playwright fallback", flush=True)
        return fetch_manuals_via_playwright(manufacturer_uri, model_code)
    
    # Create a unique cookie file for this request
    cookie_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
    cookie_path = cookie_file.name
    cookie_file.close()
    
    # Curl command with full browser headers to avoid detection
    curl_cmd = [
        'curl',
        '-s',  # Silent mode
        '-H', 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        '-H', 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        '-H', 'Accept-Language: en-US,en;q=0.9',
        '-H', 'Accept-Encoding: gzip, deflate, br',
        '-H', 'Cache-Control: no-cache',
        '-H', 'Pragma: no-cache',
        '-H', 'Sec-Ch-Ua: "Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        '-H', 'Sec-Ch-Ua-Mobile: ?0',
        '-H', 'Sec-Ch-Ua-Platform: "macOS"',
        '-H', 'Sec-Fetch-Dest: document',
        '-H', 'Sec-Fetch-Mode: navigate',
        '-H', 'Sec-Fetch-Site: none',
        '-H', 'Sec-Fetch-User: ?1',
        '-H', 'Upgrade-Insecure-Requests: 1',
        '-H', 'Connection: keep-alive',
        '--compressed',  # Handle gzip/deflate/br
        '--max-time', '10',  # 10 second timeout
        '-L',  # Follow redirects
        '--cookie-jar', cookie_path,  # Store cookies
        '--cookie', cookie_path,  # Send cookies
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
            
            # Navigate to the page
            page.goto(url, wait_until='networkidle', timeout=15000)
            
            # Wait a bit for any dynamic content
            page.wait_for_timeout(2000)
            
            # Get all manual links
            manual_links = page.locator('a[href*="/modelManual/"]').all()
            
            seen = set()
            for link in manual_links:
                href = link.get_attribute('href')
                if href and href not in seen:
                    seen.add(href)
                    
                    # Parse the manual type from URL
                    if '_sm.' in href:
                        manual_type = 'sm'
                        title = 'Service Manual'
                    elif '_pm.' in href:
                        manual_type = 'pm'
                        title = 'Parts Manual'
                    elif '_om.' in href:
                        manual_type = 'om'
                        title = 'Operation Manual'
                    elif '_im.' in href:
                        manual_type = 'im'
                        title = 'Installation Manual'
                    elif '_qrg.' in href:
                        manual_type = 'qrg'
                        title = 'Quick Reference Guide'
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