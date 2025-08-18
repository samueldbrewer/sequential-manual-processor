#!/usr/bin/env python3
"""
Fast manual fetching using curl subprocess
Much faster and simpler than Playwright
"""

import subprocess
import json
import re
import time

def fetch_manuals_via_curl(manufacturer_uri, model_code):
    """Fetch manuals using curl command - fast and reliable"""
    
    url = f"https://www.partstown.com/{manufacturer_uri}/{model_code}/parts"
    
    # Curl command with minimal headers
    curl_cmd = [
        'curl',
        '-s',  # Silent mode
        '-H', 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        '-H', 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        '-H', 'Accept-Language: en-US,en;q=0.5',
        '--compressed',  # Handle gzip/deflate
        '--max-time', '10',  # 10 second timeout
        url
    ]
    
    try:
        start_time = time.time()
        print(f"🔍 Executing curl command: {' '.join(curl_cmd)}")
        
        # Execute curl
        result = subprocess.run(
            curl_cmd,
            capture_output=True,
            text=True,
            timeout=15
        )
        
        elapsed = time.time() - start_time
        print(f"📊 Curl returned code {result.returncode} in {elapsed:.2f}s")
        
        if result.returncode == 0 and result.stdout:
            print(f"📄 Got {len(result.stdout)} bytes of HTML")
            # Extract manual links from HTML
            manual_pattern = r'/modelManual/([^"\']+\.pdf[^"\']*)'
            matches = re.findall(manual_pattern, result.stdout)
            print(f"🔎 Found {len(matches)} manual links in HTML")
            
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
            
            print(f"✅ Found {len(manuals)} manuals in {elapsed:.2f}s via curl")
            return manuals
            
        else:
            print(f"❌ Curl failed with return code {result.returncode}")
            if result.stderr:
                print(f"   Error: {result.stderr}")
            return []
            
    except subprocess.TimeoutExpired:
        print(f"❌ Curl timeout for {manufacturer_uri}/{model_code}")
        return []
    except Exception as e:
        print(f"❌ Error running curl: {e}")
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