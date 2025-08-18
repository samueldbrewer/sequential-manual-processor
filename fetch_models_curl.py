#!/usr/bin/env python3
"""
Fetch models for manufacturers using curl - the same method that works for manuals.
This bypasses CloudFlare and JavaScript rendering issues.
"""

import json
import os
import subprocess
import time
import re
from datetime import datetime

# Cache directories
CACHE_DIR = os.path.join(os.path.dirname(__file__), 'cache')
MODELS_CACHE_DIR = os.path.join(CACHE_DIR, 'models')

def get_manufacturers_without_models():
    """Get manufacturers that have empty model arrays or no cache file"""
    with open(os.path.join(CACHE_DIR, 'manufacturers.json'), 'r') as f:
        manufacturers = json.load(f)
    
    need_models = []
    for mfg in manufacturers:
        cache_file = os.path.join(MODELS_CACHE_DIR, f"{mfg['code']}.json")
        
        # Check if file doesn't exist or has empty models
        if not os.path.exists(cache_file):
            need_models.append(mfg)
        else:
            with open(cache_file, 'r') as f:
                data = json.load(f)
                if len(data.get('models', [])) == 0:
                    need_models.append(mfg)
    
    return need_models

def fetch_models_via_curl(manufacturer_uri, max_models=50):
    """
    Fetch models using curl by scraping the HTML directly.
    Similar to how we fetch manuals successfully.
    """
    
    # First, get the main parts page
    url = f"https://www.partstown.com/{manufacturer_uri}/parts"
    
    curl_cmd = [
        'curl',
        '-s',  # Silent
        '-L',  # Follow redirects
        '-H', 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        '-H', 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
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
            html_content = result.stdout
            
            # Look for model links in the HTML
            # Pattern 1: Direct model links like /manufacturer/model-code/parts
            model_pattern1 = rf'href="/{manufacturer_uri}/([^/"]+)/parts"[^>]*>([^<]+)</a>'
            
            # Pattern 2: Model links in data attributes
            model_pattern2 = r'data-model-code="([^"]+)"[^>]*data-model-name="([^"]+)"'
            
            # Pattern 3: JavaScript model data
            model_pattern3 = r'"modelCode":\s*"([^"]+)"[^}]*"modelName":\s*"([^"]+)"'
            
            models = []
            seen_codes = set()
            
            # Try all patterns
            for pattern in [model_pattern1, model_pattern2, model_pattern3]:
                matches = re.findall(pattern, html_content, re.IGNORECASE)
                
                for match in matches:
                    if len(match) == 2:
                        model_code, model_name = match
                    else:
                        continue
                    
                    # Clean up the model name
                    model_name = model_name.strip()
                    model_code = model_code.strip()
                    
                    # Skip duplicates and navigation links
                    if (model_code in seen_codes or 
                        model_name in ['Parts', 'Manuals', 'Home', 'Back', ''] or
                        'javascript' in model_code.lower()):
                        continue
                    
                    seen_codes.add(model_code)
                    
                    models.append({
                        'code': model_code,
                        'name': model_name,
                        'url': f"/{manufacturer_uri}/{model_code}/parts"
                    })
                    
                    # Cap at max_models
                    if len(models) >= max_models:
                        break
                
                if len(models) >= max_models:
                    break
            
            # If no models found with patterns, try to find the models API endpoint
            if not models:
                # Look for API endpoints in the HTML
                api_pattern = r'"/([^"]*models[^"]*)"'
                api_matches = re.findall(api_pattern, html_content)
                
                for api_path in api_matches[:3]:  # Try first 3 API endpoints found
                    if 'facets' not in api_path:  # Skip facets endpoint
                        api_url = f"https://www.partstown.com/{api_path}"
                        
                        # Try to fetch from API endpoint
                        api_cmd = curl_cmd[:-1] + [api_url]
                        api_result = subprocess.run(api_cmd, capture_output=True, text=True, timeout=10)
                        
                        if api_result.returncode == 0:
                            try:
                                # Try to parse as JSON
                                data = json.loads(api_result.stdout)
                                
                                # Extract models from various possible structures
                                if isinstance(data, list):
                                    for item in data[:max_models]:
                                        if isinstance(item, dict):
                                            models.append({
                                                'code': item.get('code', item.get('modelCode', '')),
                                                'name': item.get('name', item.get('modelName', '')),
                                                'url': f"/{manufacturer_uri}/{item.get('code', item.get('modelCode', ''))}/parts"
                                            })
                                elif isinstance(data, dict):
                                    if 'models' in data:
                                        for item in data['models'][:max_models]:
                                            models.append({
                                                'code': item.get('code', item.get('modelCode', '')),
                                                'name': item.get('name', item.get('modelName', '')),
                                                'url': f"/{manufacturer_uri}/{item.get('code', item.get('modelCode', ''))}/parts"
                                            })
                                
                                if models:
                                    break
                            except json.JSONDecodeError:
                                continue
            
            return models
            
        else:
            print(f"   ❌ Curl failed with return code {result.returncode}")
            return []
            
    except subprocess.TimeoutExpired:
        print(f"   ❌ Timeout after 35 seconds")
        return []
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return []

def save_manufacturer_cache(manufacturer, models):
    """Save models to cache file"""
    cache_file = os.path.join(MODELS_CACHE_DIR, f"{manufacturer['code']}.json")
    
    cache_data = {
        'manufacturer': {
            'code': manufacturer['code'],
            'name': manufacturer['name'],
            'uri': manufacturer['uri']
        },
        'models': models,
        'cached_at': datetime.now().isoformat(),
        'source': 'fetch_models_curl',
        'method': 'curl_html_scraping'
    }
    
    if not models:
        cache_data['note'] = 'No models found via curl scraping'
    
    with open(cache_file, 'w') as f:
        json.dump(cache_data, f, indent=2)
    
    return cache_file

def update_timestamp():
    """Update cache timestamp"""
    total_files = len([f for f in os.listdir(MODELS_CACHE_DIR) if f.endswith('.json')])
    
    timestamp_data = {
        'last_updated': datetime.now().isoformat(),
        'total_manufacturers': 489,
        'total_models_cached': total_files,
        'cache_completion': f"{(total_files / 489) * 100:.1f}%",
        'method': 'curl_scraping'
    }
    
    with open(os.path.join(CACHE_DIR, 'cache_timestamp.json'), 'w') as f:
        json.dump(timestamp_data, f, indent=2)

def main():
    print("=" * 60)
    print("FETCH MODELS USING CURL (FAST METHOD)")
    print("=" * 60)
    
    # Get manufacturers needing models
    need_models = get_manufacturers_without_models()
    
    print(f"\n📊 Found {len(need_models)} manufacturers needing models")
    
    if not need_models:
        print("✅ All manufacturers have model data!")
        return
    
    # Show first 10
    print(f"\n🔍 First 10 manufacturers to process:")
    for i, mfg in enumerate(need_models[:10]):
        print(f"   {i+1}. {mfg['name']} ({mfg['uri']})")
    
    if len(need_models) > 10:
        print(f"   ... and {len(need_models) - 10} more")
    
    print(f"\n⚡ Using fast curl method (2-3 seconds per manufacturer)")
    print(f"⏱️ Estimated time: {len(need_models) * 2.5 / 60:.1f} minutes")
    
    response = input(f"\nProcess all {len(need_models)} manufacturers? (y/n): ")
    if response.lower() != 'y':
        print("Aborted.")
        return
    
    # Process manufacturers
    success_with_models = 0
    empty_results = 0
    total_models = 0
    
    print(f"\n🚀 Starting fast model fetching...")
    start_time = time.time()
    
    for i, mfg in enumerate(need_models, 1):
        print(f"\n[{i}/{len(need_models)}] 🏭 {mfg['name']}")
        print(f"   URI: {mfg['uri']}")
        
        # Fetch models
        models = fetch_models_via_curl(mfg['uri'], max_models=50)
        
        if models:
            print(f"   ✅ Found {len(models)} models")
            success_with_models += 1
            total_models += len(models)
        else:
            print(f"   ⚠️ No models found")
            empty_results += 1
        
        # Save to cache
        cache_file = save_manufacturer_cache(mfg, models)
        print(f"   💾 Saved: {os.path.basename(cache_file)}")
        
        # Progress update every 20
        if i % 20 == 0:
            elapsed = time.time() - start_time
            rate = i / elapsed if elapsed > 0 else 0
            remaining = (len(need_models) - i) / rate if rate > 0 else 0
            print(f"\n📈 Progress: {i}/{len(need_models)} - ETA: {remaining/60:.1f} minutes")
        
        # Small delay to be respectful
        if i < len(need_models):
            time.sleep(0.5)
    
    # Update timestamp
    update_timestamp()
    
    # Summary
    elapsed_total = time.time() - start_time
    print("\n" + "=" * 60)
    print("COMPLETION SUMMARY")
    print("=" * 60)
    print(f"✅ Manufacturers with models: {success_with_models}")
    print(f"⚠️ Manufacturers without models: {empty_results}")
    print(f"📊 Total models fetched: {total_models}")
    print(f"⏱️ Total time: {elapsed_total/60:.1f} minutes")
    print(f"⚡ Average time per manufacturer: {elapsed_total/len(need_models):.1f} seconds")
    
    # Final cache status
    total_cached = len([f for f in os.listdir(MODELS_CACHE_DIR) if f.endswith('.json')])
    print(f"\n🎉 Cache coverage: {total_cached}/489 ({(total_cached / 489) * 100:.1f}%)")

if __name__ == "__main__":
    main()