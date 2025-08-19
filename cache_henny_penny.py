#!/usr/bin/env python3
"""
Cache manual links for Henny Penny only
"""

import json
import os
import time
from fetch_manuals_curl import fetch_manuals_via_curl

CACHE_DIR = 'cache'
MODELS_CACHE_DIR = os.path.join(CACHE_DIR, 'models')
MANUALS_CACHE_DIR = os.path.join(CACHE_DIR, 'manuals')

def cache_henny_penny_manuals():
    """Cache manual links for Henny Penny models"""
    
    # Create manuals cache directory
    os.makedirs(MANUALS_CACHE_DIR, exist_ok=True)
    
    # Load Henny Penny data
    manufacturer_id = 'PT_CAT1095'
    cache_file = os.path.join(MODELS_CACHE_DIR, f'{manufacturer_id}.json')
    
    with open(cache_file, 'r') as f:
        data = json.load(f)
    
    manufacturer_uri = data['manufacturer']['uri']
    models = data.get('models', [])
    
    print(f"Processing Henny Penny ({manufacturer_uri}) - {len(models)} models")
    print("="*60)
    
    # Cache for this manufacturer
    manuals_cache = {
        'manufacturer': data['manufacturer'],
        'models_with_manuals': {},
        'cached_at': time.strftime('%Y-%m-%d %H:%M:%S')
    }
    
    models_with_manuals = 0
    total_manuals = 0
    
    # Fetch manuals for each model
    for j, model in enumerate(models, 1):
        model_code = model.get('code', model.get('name', ''))
        model_name = model.get('name', model_code)
        
        if not model_code:
            continue
            
        print(f"[{j}/{len(models)}] Fetching manuals for {model_code} ({model_name})...", end='', flush=True)
        
        try:
            manuals = fetch_manuals_via_curl(manufacturer_uri, model_code)
            
            if manuals:
                manuals_cache['models_with_manuals'][model_code] = {
                    'name': model_name,
                    'manuals': manuals
                }
                models_with_manuals += 1
                total_manuals += len(manuals)
                print(f" ✅ {len(manuals)} manuals")
            else:
                print(f" ⚠️ No manuals")
                
        except Exception as e:
            print(f" ❌ Error: {e}")
        
        # Small delay to be nice to the server
        time.sleep(0.5)
    
    # Save cache file
    cache_file = os.path.join(MANUALS_CACHE_DIR, f"{manufacturer_id}.json")
    with open(cache_file, 'w') as f:
        json.dump(manuals_cache, f, indent=2)
    
    print("\n" + "="*60)
    print(f"✅ Caching complete for Henny Penny!")
    print(f"  - Models processed: {len(models)}")
    print(f"  - Models with manuals: {models_with_manuals}")
    print(f"  - Total manuals cached: {total_manuals}")
    print(f"  - Cache file: cache/manuals/{manufacturer_id}.json")

if __name__ == "__main__":
    print("Starting Henny Penny manual caching...")
    print("="*60)
    
    try:
        cache_henny_penny_manuals()
    except KeyboardInterrupt:
        print("\n\n⚠️ Caching interrupted by user")