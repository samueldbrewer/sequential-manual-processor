#!/usr/bin/env python3
"""
Complete the missing cache by fetching models for manufacturers without cached data.
This script identifies manufacturers without model cache files and fetches their models.
"""

import json
import os
import sys
import time
from datetime import datetime
import subprocess
import hashlib

# Cache directories
CACHE_DIR = os.path.join(os.path.dirname(__file__), 'cache')
MODELS_CACHE_DIR = os.path.join(CACHE_DIR, 'models')

def get_missing_manufacturers():
    """Get list of manufacturers without cached models"""
    # Load manufacturers list
    with open(os.path.join(CACHE_DIR, 'manufacturers.json'), 'r') as f:
        manufacturers = json.load(f)
    
    # Check which ones have cache files
    missing = []
    for mfg in manufacturers:
        cache_file = os.path.join(MODELS_CACHE_DIR, f"{mfg['code']}.json")
        if not os.path.exists(cache_file):
            missing.append(mfg)
    
    return missing

def fetch_models_via_curl(manufacturer_uri):
    """Fetch models for a manufacturer using curl (bypasses CloudFlare)"""
    url = f"https://www.partstown.com/{manufacturer_uri}/parts"
    
    # Build curl command
    curl_cmd = [
        'curl',
        '-s',  # Silent
        '-L',  # Follow redirects
        '-H', 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        '-H', 'Accept: text/html,application/xhtml+xml',
        '-H', 'Accept-Language: en-US,en;q=0.9',
        '--compressed',
        '--max-time', '30',
        url
    ]
    
    try:
        result = subprocess.run(
            curl_cmd,
            capture_output=True,
            text=True,
            timeout=35
        )
        
        if result.returncode == 0:
            return result.stdout
        else:
            print(f"  ❌ Curl failed with return code {result.returncode}")
            return None
            
    except subprocess.TimeoutExpired:
        print(f"  ❌ Timeout after 35 seconds")
        return None
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return None

def parse_models_from_html(html_content):
    """Parse model data from the HTML content"""
    import re
    
    models = []
    
    # Look for model links in the HTML
    # Pattern: /manufacturer/model-code/parts
    model_pattern = r'href="(/[^/]+/([^/]+)/parts)"[^>]*>([^<]+)</a>'
    
    matches = re.findall(model_pattern, html_content)
    seen = set()
    
    for match in matches:
        full_url, model_code, model_name = match
        
        # Skip if we've already seen this model
        if model_code in seen:
            continue
        seen.add(model_code)
        
        # Clean up the model name
        model_name = model_name.strip()
        
        # Only include if it looks like a model (not navigation links)
        if not model_name or model_name in ['Parts', 'Manuals', 'Home', 'Back']:
            continue
            
        models.append({
            'code': model_code,
            'name': model_name,
            'url': f"https://www.partstown.com{full_url}"
        })
    
    return models

def fetch_and_cache_manufacturer(mfg):
    """Fetch and cache models for a single manufacturer"""
    print(f"\n📦 Processing {mfg['name']} ({mfg['code']})")
    print(f"   URI: {mfg['uri']}")
    
    # Fetch the page
    print(f"   🔍 Fetching models page...")
    html_content = fetch_models_via_curl(mfg['uri'])
    
    if not html_content:
        print(f"   ⚠️ Failed to fetch page")
        return False
    
    # Parse models
    models = parse_models_from_html(html_content)
    
    if not models:
        print(f"   ⚠️ No models found (might be JavaScript-rendered)")
        # Still save empty cache to avoid re-fetching
        cache_data = {
            'manufacturer': {
                'code': mfg['code'],
                'name': mfg['name'],
                'uri': mfg['uri']
            },
            'models': [],
            'cached_at': datetime.now().isoformat(),
            'source': 'complete_cache_script'
        }
    else:
        print(f"   ✅ Found {len(models)} models")
        cache_data = {
            'manufacturer': {
                'code': mfg['code'],
                'name': mfg['name'],
                'uri': mfg['uri']
            },
            'models': models,
            'cached_at': datetime.now().isoformat(),
            'source': 'complete_cache_script'
        }
    
    # Save to cache file
    cache_file = os.path.join(MODELS_CACHE_DIR, f"{mfg['code']}.json")
    with open(cache_file, 'w') as f:
        json.dump(cache_data, f, indent=2)
    
    print(f"   💾 Saved to cache: {cache_file}")
    return True

def update_cache_timestamp(total_cached, new_cached):
    """Update the cache timestamp file"""
    timestamp_file = os.path.join(CACHE_DIR, 'cache_timestamp.json')
    
    timestamp_data = {
        'last_updated': datetime.now().isoformat(),
        'total_manufacturers': 489,
        'total_models_cached': total_cached,
        'new_models_cached': new_cached,
        'cache_completion': f"{(total_cached / 489) * 100:.1f}%"
    }
    
    with open(timestamp_file, 'w') as f:
        json.dump(timestamp_data, f, indent=2)
    
    print(f"\n📅 Updated cache timestamp: {timestamp_file}")

def main():
    """Main function to complete the cache"""
    print("=" * 60)
    print("CACHE COMPLETION SCRIPT")
    print("=" * 60)
    
    # Get missing manufacturers
    missing = get_missing_manufacturers()
    
    if not missing:
        print("\n✅ Cache is already complete!")
        return
    
    print(f"\n📊 Cache Status:")
    print(f"   Total manufacturers: 489")
    print(f"   Currently cached: {489 - len(missing)}")
    print(f"   Missing: {len(missing)}")
    print(f"   Coverage: {((489 - len(missing)) / 489) * 100:.1f}%")
    
    # Show first 10 missing manufacturers
    print(f"\n🔍 First 10 missing manufacturers:")
    for i, mfg in enumerate(missing[:10]):
        print(f"   {i+1}. {mfg['name']} ({mfg['code']})")
    
    if len(missing) > 10:
        print(f"   ... and {len(missing) - 10} more")
    
    # Ask for confirmation
    print(f"\n⚠️ This will fetch models for {len(missing)} manufacturers.")
    print("   This may take several minutes due to rate limiting.")
    response = input("\nProceed? (y/n): ")
    
    if response.lower() != 'y':
        print("Aborted.")
        return
    
    # Process each missing manufacturer
    print(f"\n🚀 Starting cache completion...")
    success_count = 0
    failed = []
    
    for i, mfg in enumerate(missing, 1):
        print(f"\n[{i}/{len(missing)}] ", end="")
        
        try:
            if fetch_and_cache_manufacturer(mfg):
                success_count += 1
            else:
                failed.append(mfg)
        except Exception as e:
            print(f"   ❌ Error: {e}")
            failed.append(mfg)
        
        # Rate limiting - wait between requests
        if i < len(missing):
            time.sleep(1)  # 1 second delay between requests
    
    # Summary
    print("\n" + "=" * 60)
    print("COMPLETION SUMMARY")
    print("=" * 60)
    print(f"✅ Successfully cached: {success_count}/{len(missing)}")
    
    if failed:
        print(f"❌ Failed: {len(failed)}")
        print("\nFailed manufacturers:")
        for mfg in failed[:10]:
            print(f"   - {mfg['name']} ({mfg['code']})")
        if len(failed) > 10:
            print(f"   ... and {len(failed) - 10} more")
    
    # Update cache timestamp
    total_cached = 489 - len(missing) + success_count
    update_cache_timestamp(total_cached, success_count)
    
    print(f"\n📊 Final cache coverage: {(total_cached / 489) * 100:.1f}%")
    
    if success_count == len(missing):
        print("\n🎉 Cache is now 100% complete!")
    else:
        print(f"\n⚠️ Cache is now {(total_cached / 489) * 100:.1f}% complete")
        print(f"   Run this script again to retry failed manufacturers")

if __name__ == "__main__":
    main()