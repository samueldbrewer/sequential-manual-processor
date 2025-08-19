#!/usr/bin/env python3
"""
Cache all manual links for all models
Run this locally where curl works, then deploy the cache to Railway
"""

import json
import os
import time
from fetch_manuals_curl import fetch_manuals_via_curl

CACHE_DIR = 'cache'
MODELS_CACHE_DIR = os.path.join(CACHE_DIR, 'models')
MANUALS_CACHE_DIR = os.path.join(CACHE_DIR, 'manuals')

def cache_all_manuals():
    """Cache manual links for all models"""
    
    # Create manuals cache directory
    os.makedirs(MANUALS_CACHE_DIR, exist_ok=True)
    
    # Get list of all manufacturer files
    model_files = [f for f in os.listdir(MODELS_CACHE_DIR) if f.endswith('.json')]
    
    print(f"Found {len(model_files)} manufacturer cache files")
    
    total_models = 0
    total_manuals = 0
    manufacturers_with_manuals = 0
    
    for i, filename in enumerate(model_files, 1):
        manufacturer_id = filename.replace('.json', '')
        
        # Load manufacturer data
        with open(os.path.join(MODELS_CACHE_DIR, filename), 'r') as f:
            data = json.load(f)
        
        manufacturer_uri = data['manufacturer']['uri']
        models = data.get('models', [])
        
        if not models:
            print(f"[{i}/{len(model_files)}] {manufacturer_id}: No models, skipping")
            continue
            
        print(f"\n[{i}/{len(model_files)}] Processing {manufacturer_id} ({manufacturer_uri}) - {len(models)} models")
        
        # Cache for this manufacturer
        manuals_cache = {
            'manufacturer': data['manufacturer'],
            'models_with_manuals': {},
            'cached_at': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        models_with_manuals = 0
        
        # Fetch manuals for each model
        for j, model in enumerate(models[:10], 1):  # Limit to first 10 models for testing
            model_code = model.get('code', model.get('name', ''))
            
            if not model_code:
                continue
                
            print(f"  [{j}/{min(10, len(models))}] Fetching manuals for {model_code}...", end='')
            
            try:
                manuals = fetch_manuals_via_curl(manufacturer_uri, model_code)
                
                if manuals:
                    manuals_cache['models_with_manuals'][model_code] = {
                        'name': model.get('name'),
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
        
        total_models += len(models)
        
        if models_with_manuals > 0:
            manufacturers_with_manuals += 1
            # Save cache file
            cache_file = os.path.join(MANUALS_CACHE_DIR, f"{manufacturer_id}.json")
            with open(cache_file, 'w') as f:
                json.dump(manuals_cache, f, indent=2)
            print(f"  💾 Cached {models_with_manuals} models with manuals")
    
    print("\n" + "="*60)
    print(f"✅ Caching complete!")
    print(f"  - Manufacturers processed: {len(model_files)}")
    print(f"  - Manufacturers with manuals: {manufacturers_with_manuals}")
    print(f"  - Total models: {total_models}")
    print(f"  - Total manuals cached: {total_manuals}")

if __name__ == "__main__":
    print("Starting manual link caching...")
    print("This will fetch manual links for all models")
    print("Press Ctrl+C to stop at any time")
    print("="*60)
    
    try:
        cache_all_manuals()
    except KeyboardInterrupt:
        print("\n\n⚠️ Caching interrupted by user")