#!/usr/bin/env python3
"""
Fetch real model data for manufacturers with empty model arrays.
Uses the actual PartsTown scraper with Playwright to get JavaScript-rendered content.
"""

import json
import os
import sys
import time
import asyncio
from datetime import datetime
from pathlib import Path

# Add the scraper path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'API Scraper V2'))

# Import the actual scraper
try:
    from interactive_scraper import InteractiveScraper
except ImportError:
    print("❌ Could not import InteractiveScraper from ../API Scraper V2/")
    print("   Make sure the scraper is available in the parent directory")
    sys.exit(1)

# Cache directories
CACHE_DIR = os.path.join(os.path.dirname(__file__), 'cache')
MODELS_CACHE_DIR = os.path.join(CACHE_DIR, 'models')

def get_empty_manufacturers():
    """Get list of manufacturers with empty model arrays"""
    # Load manufacturers list
    with open(os.path.join(CACHE_DIR, 'manufacturers.json'), 'r') as f:
        manufacturers = json.load(f)
    
    empty = []
    for mfg in manufacturers:
        cache_file = os.path.join(MODELS_CACHE_DIR, f"{mfg['code']}.json")
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
                if len(cache_data.get('models', [])) == 0:
                    empty.append(mfg)
    
    return empty

async def fetch_models_with_scraper(scraper, manufacturer):
    """Fetch models for a manufacturer using the actual scraper"""
    try:
        print(f"   🔍 Fetching models for {manufacturer['uri']}...")
        
        # Use the scraper's get_models method
        models = await scraper.get_models(manufacturer['uri'])
        
        if models:
            print(f"   ✅ Found {len(models)} models")
            return models
        else:
            print(f"   ⚠️ No models found")
            return []
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return []

async def update_manufacturer_cache(manufacturer, models):
    """Update the cache file with real model data"""
    cache_file = os.path.join(MODELS_CACHE_DIR, f"{manufacturer['code']}.json")
    
    cache_data = {
        'manufacturer': {
            'code': manufacturer['code'],
            'name': manufacturer['name'],
            'uri': manufacturer['uri']
        },
        'models': models,
        'cached_at': datetime.now().isoformat(),
        'source': 'fetch_missing_models_script'
    }
    
    with open(cache_file, 'w') as f:
        json.dump(cache_data, f, indent=2)
    
    print(f"   💾 Updated cache: {cache_file}")

async def main():
    """Main function to fetch missing model data"""
    print("=" * 60)
    print("FETCH MISSING MODELS WITH PLAYWRIGHT")
    print("=" * 60)
    
    # Get manufacturers with empty models
    empty = get_empty_manufacturers()
    
    if not empty:
        print("\n✅ No manufacturers with empty model arrays!")
        return
    
    print(f"\n📊 Found {len(empty)} manufacturers with empty models")
    
    # Show first 10
    print(f"\n🔍 First 10 manufacturers to update:")
    for i, mfg in enumerate(empty[:10]):
        print(f"   {i+1}. {mfg['name']} ({mfg['code']})")
    
    if len(empty) > 10:
        print(f"   ... and {len(empty) - 10} more")
    
    # Ask for confirmation
    print(f"\n⚠️ This will fetch real model data for {len(empty)} manufacturers.")
    print("   This uses Playwright and may take 30-60 seconds per manufacturer.")
    print(f"   Estimated time: {len(empty) * 45 / 60:.1f} minutes")
    
    # For testing, just do the first 5
    print("\n📝 For testing, we'll just do the first 5 manufacturers.")
    response = input("\nProceed with first 5? (y/n): ")
    
    if response.lower() != 'y':
        print("Aborted.")
        return
    
    # Initialize scraper
    print("\n🚀 Initializing scraper...")
    scraper = InteractiveScraper()
    await scraper.init()
    
    # Process first 5 manufacturers
    test_batch = empty[:5]
    success_count = 0
    
    for i, mfg in enumerate(test_batch, 1):
        print(f"\n[{i}/{len(test_batch)}] Processing {mfg['name']} ({mfg['code']})")
        
        try:
            # Fetch models
            models = await fetch_models_with_scraper(scraper, mfg)
            
            if models:
                # Update cache
                await update_manufacturer_cache(mfg, models)
                success_count += 1
            else:
                print(f"   ⚠️ No models to update")
                
        except Exception as e:
            print(f"   ❌ Failed: {e}")
        
        # Rate limiting
        if i < len(test_batch):
            print("   ⏳ Waiting 2 seconds...")
            await asyncio.sleep(2)
    
    # Cleanup
    print("\n🧹 Closing scraper...")
    await scraper.close()
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST BATCH SUMMARY")
    print("=" * 60)
    print(f"✅ Successfully updated: {success_count}/{len(test_batch)}")
    
    if success_count > 0:
        print(f"\n🎉 Test successful! {success_count} manufacturers now have real model data.")
        print(f"   Run with --all flag to process remaining {len(empty) - 5} manufacturers")
    else:
        print("\n⚠️ No models were fetched. The scraper may need adjustments.")

if __name__ == "__main__":
    # Check for --all flag
    if len(sys.argv) > 1 and sys.argv[1] == '--all':
        print("Full batch mode not implemented yet. Run without flags for test mode.")
    else:
        asyncio.run(main())