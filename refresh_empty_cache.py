#!/usr/bin/env python3
"""
Refresh cache for manufacturers with empty model arrays.
Calls the running server's API to trigger proper model fetching.
"""

import json
import os
import requests
import time
from datetime import datetime

# Cache directories
CACHE_DIR = os.path.join(os.path.dirname(__file__), 'cache')
MODELS_CACHE_DIR = os.path.join(CACHE_DIR, 'models')

# Server URL (make sure server.py is running, not server_cached.py)
SERVER_URL = "http://localhost:8888"

def get_empty_manufacturers():
    """Get list of manufacturers with empty model arrays"""
    with open(os.path.join(CACHE_DIR, 'manufacturers.json'), 'r') as f:
        manufacturers = json.load(f)
    
    empty = []
    for mfg in manufacturers:
        cache_file = os.path.join(MODELS_CACHE_DIR, f"{mfg['code']}.json")
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
                if len(cache_data.get('models', [])) == 0:
                    empty.append({
                        'code': mfg['code'],
                        'name': mfg['name'],
                        'uri': mfg['uri'],
                        'cache_file': cache_file
                    })
    
    return empty

def fetch_models_from_server(manufacturer_code):
    """Call the server API to fetch models"""
    try:
        url = f"{SERVER_URL}/api/manufacturers/{manufacturer_code}/models"
        response = requests.get(url, timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            if 'data' in data:
                return data['data']
            else:
                return []
        else:
            print(f"   ❌ Server returned {response.status_code}")
            return None
            
    except requests.exceptions.Timeout:
        print(f"   ⏱️ Request timeout after 60 seconds")
        return None
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None

def update_cache_file(manufacturer, models):
    """Update the cache file with fetched models"""
    cache_data = {
        'manufacturer': {
            'code': manufacturer['code'],
            'name': manufacturer['name'],
            'uri': manufacturer['uri']
        },
        'models': models,
        'cached_at': datetime.now().isoformat(),
        'source': 'refresh_cache_script'
    }
    
    with open(manufacturer['cache_file'], 'w') as f:
        json.dump(cache_data, f, indent=2)
    
    return True

def main():
    print("=" * 60)
    print("REFRESH EMPTY CACHE FILES")
    print("=" * 60)
    
    # Check if server is running
    try:
        response = requests.get(f"{SERVER_URL}/api/manufacturers", timeout=5)
        if response.status_code != 200:
            print("❌ Server not responding properly")
            print("   Make sure server.py (NOT server_cached.py) is running")
            return
    except:
        print("❌ Cannot connect to server at http://localhost:8888")
        print("   Please start the server first:")
        print("   python3 server.py")
        return
    
    # Get manufacturers with empty models
    empty = get_empty_manufacturers()
    
    if not empty:
        print("\n✅ No manufacturers with empty model arrays!")
        return
    
    print(f"\n📊 Found {len(empty)} manufacturers with empty models")
    
    # Show first 10
    print(f"\n🔍 Manufacturers to refresh:")
    for i, mfg in enumerate(empty[:10]):
        print(f"   {i+1}. {mfg['name']} ({mfg['code']})")
    
    if len(empty) > 10:
        print(f"   ... and {len(empty) - 10} more")
    
    # For testing, just do a small batch
    test_batch = 5
    print(f"\n📝 Testing with first {test_batch} manufacturers")
    print("   Note: Each request may take 10-30 seconds")
    
    response = input("\nProceed? (y/n): ")
    if response.lower() != 'y':
        print("Aborted.")
        return
    
    # Process manufacturers
    success_count = 0
    failed = []
    
    for i, mfg in enumerate(empty[:test_batch], 1):
        print(f"\n[{i}/{test_batch}] {mfg['name']} ({mfg['code']})")
        print(f"   Fetching from server...")
        
        models = fetch_models_from_server(mfg['code'])
        
        if models is not None:
            if len(models) > 0:
                print(f"   ✅ Got {len(models)} models")
                update_cache_file(mfg, models)
                success_count += 1
            else:
                print(f"   ⚠️ No models returned")
                # Still update cache to mark as processed
                update_cache_file(mfg, [])
        else:
            print(f"   ❌ Failed to fetch")
            failed.append(mfg)
        
        # Rate limiting
        if i < test_batch:
            print("   ⏳ Waiting 2 seconds...")
            time.sleep(2)
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"✅ Successfully processed: {success_count}/{test_batch}")
    
    if failed:
        print(f"❌ Failed: {len(failed)}")
        for mfg in failed:
            print(f"   - {mfg['name']}")
    
    if success_count > 0:
        print(f"\n🎉 Test successful!")
        print(f"   To process all {len(empty)} manufacturers, run:")
        print(f"   python3 refresh_empty_cache.py --all")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--all':
        print("Full batch mode not implemented yet")
        print("Run without --all flag for test mode")
    else:
        main()