#!/usr/bin/env python3
"""
Test direct HTTP requests to PartsTown without Playwright
Compare different methods for speed and reliability
"""

import requests
import time
import json
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Test URLs
TEST_URLS = [
    {"manufacturer": "Henny Penny", "uri": "henny-penny", "model": "500"},
    {"manufacturer": "Frosty Factory", "uri": "frosty-factory", "model": "113a"},
    {"manufacturer": "Globe", "uri": "globe", "model": "2500"},
    {"manufacturer": "PizzaMaster", "uri": "pizzamaster", "model": "pm351ed"},
    {"manufacturer": "Evo", "uri": "evo", "model": "10-0002"},
]

# Different user agents to test
USER_AGENTS = {
    "chrome": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "firefox": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
    "edge": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "safari": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15"
}

def method1_direct_html_request(manufacturer_uri, model_code):
    """Method 1: Direct HTML request with manuals tab in URL"""
    print(f"\n🔍 Method 1: Direct HTML request for {manufacturer_uri}/{model_code}")
    
    url = f"https://www.partstown.com/{manufacturer_uri}/{model_code}/parts#id=mdptabmanuals"
    
    headers = {
        'User-Agent': USER_AGENTS['chrome'],
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0'
    }
    
    start_time = time.time()
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        elapsed = time.time() - start_time
        
        print(f"  Status: {response.status_code} | Time: {elapsed:.2f}s | Size: {len(response.content)} bytes")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Try to find manual links in various ways
            manual_links = []
            
            # Method A: Look for modelManual links
            for link in soup.find_all('a', href=True):
                href = link['href']
                if '/modelManual/' in href and href.endswith('.pdf'):
                    manual_links.append(href)
            
            # Method B: Look for data attributes or JavaScript data
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string and 'modelManual' in script.string:
                    # Try to extract URLs from JavaScript
                    matches = re.findall(r'/modelManual/[^"\']+\.pdf[^"\']*', script.string)
                    manual_links.extend(matches)
            
            # Method C: Look for specific divs/sections
            manuals_section = soup.find('div', {'id': 'mdptabmanuals'})
            if manuals_section:
                for link in manuals_section.find_all('a', href=True):
                    if '.pdf' in link['href']:
                        manual_links.append(link['href'])
            
            manual_links = list(set(manual_links))  # Remove duplicates
            print(f"  ✅ Found {len(manual_links)} manual links")
            return {"success": True, "manuals": manual_links, "time": elapsed}
        else:
            print(f"  ❌ HTTP {response.status_code}")
            return {"success": False, "error": f"HTTP {response.status_code}", "time": elapsed}
            
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"  ❌ Error: {e}")
        return {"success": False, "error": str(e), "time": elapsed}

def method2_api_endpoint(manufacturer_uri, model_code):
    """Method 2: Try to find/call API endpoints directly"""
    print(f"\n🔍 Method 2: API endpoint search for {manufacturer_uri}/{model_code}")
    
    # Common API patterns
    api_patterns = [
        f"https://www.partstown.com/api/models/{manufacturer_uri}/{model_code}/manuals",
        f"https://www.partstown.com/api/products/{manufacturer_uri}/{model_code}/documents",
        f"https://www.partstown.com/{manufacturer_uri}/{model_code}/manuals.json",
        f"https://www.partstown.com/api/v1/manuals?manufacturer={manufacturer_uri}&model={model_code}"
    ]
    
    headers = {
        'User-Agent': USER_AGENTS['chrome'],
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': f'https://www.partstown.com/{manufacturer_uri}/{model_code}/parts',
        'X-Requested-With': 'XMLHttpRequest'
    }
    
    for api_url in api_patterns:
        start_time = time.time()
        try:
            response = requests.get(api_url, headers=headers, timeout=5)
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                print(f"  ✅ Found API at: {api_url}")
                print(f"  Time: {elapsed:.2f}s | Size: {len(response.content)} bytes")
                return {"success": True, "url": api_url, "data": response.text[:500], "time": elapsed}
        except:
            pass
    
    print(f"  ❌ No API endpoints found")
    return {"success": False, "error": "No API endpoints found"}

def method3_session_based(manufacturer_uri, model_code):
    """Method 3: Use session with cookies"""
    print(f"\n🔍 Method 3: Session-based request for {manufacturer_uri}/{model_code}")
    
    session = requests.Session()
    
    # First visit the main page to get cookies
    base_url = f"https://www.partstown.com/{manufacturer_uri}/{model_code}/parts"
    
    headers = {
        'User-Agent': USER_AGENTS['chrome'],
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    }
    
    start_time = time.time()
    
    try:
        # Step 1: Get the main page
        response1 = session.get(base_url, headers=headers, timeout=10)
        
        # Step 2: Request with manuals tab
        url = f"https://www.partstown.com/{manufacturer_uri}/{model_code}/parts#id=mdptabmanuals"
        response2 = session.get(url, headers=headers, timeout=10)
        
        elapsed = time.time() - start_time
        
        if response2.status_code == 200:
            # Parse for manuals
            content = response2.text
            manual_links = re.findall(r'/modelManual/[^"\']+\.pdf[^"\']*', content)
            manual_links = list(set(manual_links))
            
            print(f"  Status: {response2.status_code} | Time: {elapsed:.2f}s")
            print(f"  ✅ Found {len(manual_links)} manual links")
            print(f"  Cookies: {len(session.cookies)}")
            return {"success": True, "manuals": manual_links, "time": elapsed}
        else:
            print(f"  ❌ HTTP {response2.status_code}")
            return {"success": False, "error": f"HTTP {response2.status_code}", "time": elapsed}
            
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"  ❌ Error: {e}")
        return {"success": False, "error": str(e), "time": elapsed}

def method4_xhr_simulation(manufacturer_uri, model_code):
    """Method 4: Simulate XHR/AJAX requests"""
    print(f"\n🔍 Method 4: XHR simulation for {manufacturer_uri}/{model_code}")
    
    # First get the page to find any API calls
    base_url = f"https://www.partstown.com/{manufacturer_uri}/{model_code}/parts"
    
    headers = {
        'User-Agent': USER_AGENTS['chrome'],
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': base_url,
        'X-Requested-With': 'XMLHttpRequest',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
    }
    
    start_time = time.time()
    
    try:
        # Try different XHR patterns
        xhr_urls = [
            f"https://www.partstown.com/{manufacturer_uri}/{model_code}/manuals",
            f"https://www.partstown.com/{manufacturer_uri}/{model_code}/documents",
            f"https://www.partstown.com/{manufacturer_uri}/{model_code}/parts/manuals"
        ]
        
        for xhr_url in xhr_urls:
            response = requests.get(xhr_url, headers=headers, timeout=5)
            if response.status_code == 200:
                elapsed = time.time() - start_time
                print(f"  ✅ XHR endpoint found: {xhr_url}")
                print(f"  Time: {elapsed:.2f}s")
                
                # Try to parse response
                if 'json' in response.headers.get('content-type', ''):
                    data = response.json()
                    print(f"  JSON response with {len(str(data))} chars")
                else:
                    # Look for PDFs in HTML response
                    manual_links = re.findall(r'/modelManual/[^"\']+\.pdf[^"\']*', response.text)
                    manual_links = list(set(manual_links))
                    print(f"  Found {len(manual_links)} manual links")
                
                return {"success": True, "url": xhr_url, "time": elapsed}
        
        elapsed = time.time() - start_time
        print(f"  ❌ No XHR endpoints found")
        return {"success": False, "error": "No XHR endpoints", "time": elapsed}
        
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"  ❌ Error: {e}")
        return {"success": False, "error": str(e), "time": elapsed}

def run_all_tests():
    """Run all methods on test URLs"""
    print("="*60)
    print("TESTING DIRECT REQUEST METHODS FOR PARTSTTOWN MANUALS")
    print("="*60)
    
    results = []
    
    for test_item in TEST_URLS[:3]:  # Test first 3 for now
        print(f"\n{'='*60}")
        print(f"Testing: {test_item['manufacturer']} - Model {test_item['model']}")
        print(f"{'='*60}")
        
        result = {
            "manufacturer": test_item['manufacturer'],
            "model": test_item['model'],
            "methods": {}
        }
        
        # Test each method
        result["methods"]["direct_html"] = method1_direct_html_request(test_item['uri'], test_item['model'])
        result["methods"]["api_search"] = method2_api_endpoint(test_item['uri'], test_item['model'])
        result["methods"]["session"] = method3_session_based(test_item['uri'], test_item['model'])
        result["methods"]["xhr"] = method4_xhr_simulation(test_item['uri'], test_item['model'])
        
        results.append(result)
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY OF RESULTS")
    print("="*60)
    
    for result in results:
        print(f"\n{result['manufacturer']} - Model {result['model']}:")
        for method_name, method_result in result['methods'].items():
            status = "✅" if method_result.get("success") else "❌"
            time_str = f"{method_result.get('time', 0):.2f}s" if 'time' in method_result else "N/A"
            manuals = len(method_result.get('manuals', [])) if 'manuals' in method_result else 0
            print(f"  {status} {method_name:15} | Time: {time_str:6} | Manuals: {manuals}")

if __name__ == "__main__":
    run_all_tests()