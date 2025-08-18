#!/usr/bin/env python3
"""
Advanced testing with more sophisticated headers and methods
"""

import requests
import time
import re
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def create_advanced_session():
    """Create a session with retry strategy and advanced settings"""
    session = requests.Session()
    
    # Add retry strategy
    retry_strategy = Retry(
        total=3,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],  # Changed from method_whitelist
        backoff_factor=1
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session

def test_with_full_browser_headers(manufacturer_uri, model_code):
    """Test with complete browser-like headers"""
    print(f"\n🔍 Testing with full browser headers: {manufacturer_uri}/{model_code}")
    
    session = create_advanced_session()
    
    # Complete Chrome headers from real browser
    headers = {
        'Host': 'www.partstown.com',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"macOS"',
        'Cache-Control': 'max-age=0'
    }
    
    url = f"https://www.partstown.com/{manufacturer_uri}/{model_code}/parts"
    
    try:
        # First request to establish session
        response = session.get(url, headers=headers, timeout=15, allow_redirects=True)
        print(f"  Initial request: {response.status_code}")
        print(f"  Cookies received: {len(session.cookies)}")
        
        # Check for CloudFlare or other protection
        if 'cf-ray' in response.headers:
            print("  ⚠️ CloudFlare detected")
        
        if response.status_code == 200:
            # Look for manual links in the response
            manual_links = re.findall(r'/modelManual/[^"\']+\.pdf[^"\']*', response.text)
            manual_links = list(set(manual_links))
            print(f"  ✅ Found {len(manual_links)} manual links")
            
            # Also check for JavaScript data
            if 'window.__INITIAL_STATE__' in response.text:
                print("  📊 Found React/Vue initial state")
            
            # Check for API endpoints in the HTML
            api_patterns = re.findall(r'["\'](/api/[^"\']+)["\']', response.text)
            if api_patterns:
                print(f"  🔗 Found {len(api_patterns)} API endpoints in HTML")
                for api in api_patterns[:3]:
                    print(f"     - {api}")
            
            return {"success": True, "manuals": manual_links, "status": response.status_code}
        else:
            # Get more info about the failure
            print(f"  ❌ Status: {response.status_code}")
            print(f"  Response size: {len(response.content)} bytes")
            if response.status_code == 403:
                # Check what kind of 403 page it is
                if 'Access Denied' in response.text:
                    print("  📛 Access Denied page")
                if 'captcha' in response.text.lower():
                    print("  🤖 CAPTCHA detected")
            
            return {"success": False, "status": response.status_code}
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return {"success": False, "error": str(e)}

def test_with_cloudscraper():
    """Test using cloudscraper library to bypass CloudFlare"""
    try:
        import cloudscraper
        print("\n🔍 Testing with cloudscraper")
        
        scraper = cloudscraper.create_scraper()
        
        test_url = "https://www.partstown.com/henny-penny/500/parts"
        response = scraper.get(test_url, timeout=15)
        
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            manual_links = re.findall(r'/modelManual/[^"\']+\.pdf[^"\']*', response.text)
            print(f"  ✅ Found {len(manual_links)} manual links")
            return {"success": True, "manuals": manual_links}
        else:
            print(f"  ❌ Failed with status {response.status_code}")
            return {"success": False, "status": response.status_code}
            
    except ImportError:
        print("\n⚠️ cloudscraper not installed. Install with: pip install cloudscraper")
        return {"success": False, "error": "cloudscraper not installed"}
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return {"success": False, "error": str(e)}

def test_curl_command():
    """Test using curl command directly"""
    import subprocess
    
    print("\n🔍 Testing with curl command")
    
    curl_cmd = [
        'curl',
        '-H', 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        '-H', 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        '-H', 'Accept-Language: en-US,en;q=0.5',
        '-H', 'Accept-Encoding: gzip, deflate',
        '-H', 'Connection: keep-alive',
        '-H', 'Upgrade-Insecure-Requests: 1',
        '--compressed',
        '--location',
        '-s',
        '-w', '\\nHTTP_CODE:%{http_code}',
        'https://www.partstown.com/henny-penny/500/parts'
    ]
    
    try:
        result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=15)
        
        # Extract HTTP code
        if 'HTTP_CODE:' in result.stdout:
            parts = result.stdout.split('HTTP_CODE:')
            content = parts[0]
            http_code = parts[1].strip()
            print(f"  HTTP Status: {http_code}")
            
            if http_code == '200':
                manual_links = re.findall(r'/modelManual/[^"\']+\.pdf[^"\']*', content)
                manual_links = list(set(manual_links))
                print(f"  ✅ Found {len(manual_links)} manual links")
                return {"success": True, "manuals": manual_links}
            else:
                print(f"  ❌ Failed with status {http_code}")
                return {"success": False, "status": http_code}
        else:
            print(f"  ❌ Could not parse response")
            return {"success": False, "error": "Parse error"}
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return {"success": False, "error": str(e)}

def test_httpx():
    """Test using httpx library which has different behavior than requests"""
    try:
        import httpx
        print("\n🔍 Testing with httpx library")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }
        
        with httpx.Client(headers=headers, follow_redirects=True) as client:
            response = client.get("https://www.partstown.com/henny-penny/500/parts", timeout=15)
            
            print(f"  Status: {response.status_code}")
            if response.status_code == 200:
                manual_links = re.findall(r'/modelManual/[^"\']+\.pdf[^"\']*', response.text)
                print(f"  ✅ Found {len(manual_links)} manual links")
                return {"success": True, "manuals": manual_links}
            else:
                print(f"  ❌ Failed with status {response.status_code}")
                return {"success": False, "status": response.status_code}
                
    except ImportError:
        print("\n⚠️ httpx not installed. Install with: pip install httpx")
        return {"success": False, "error": "httpx not installed"}
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return {"success": False, "error": str(e)}

def main():
    print("="*60)
    print("ADVANCED TESTING FOR PARTSTTOWN ACCESS")
    print("="*60)
    
    # Test different manufacturers
    test_cases = [
        ("henny-penny", "500"),
        ("globe", "2500"),
        ("pizzamaster", "pm351ed")
    ]
    
    for manufacturer, model in test_cases[:1]:  # Test just one for now
        print(f"\n{'='*60}")
        print(f"Testing: {manufacturer}/{model}")
        print(f"{'='*60}")
        
        # Try different methods
        test_with_full_browser_headers(manufacturer, model)
        test_with_cloudscraper()
        test_curl_command()
        test_httpx()
    
    print("\n" + "="*60)
    print("CONCLUSION")
    print("="*60)
    print("""
    The site appears to have strong bot protection (likely CloudFlare).
    Direct HTTP requests are blocked with 403 Forbidden.
    
    Options:
    1. Continue using Playwright (current solution) - slower but reliable
    2. Try cloudscraper library - may work but needs maintenance
    3. Use a proxy service or scraping API
    4. Implement request signing if we can reverse engineer it
    
    Playwright remains the most reliable option for now.
    """)

if __name__ == "__main__":
    main()