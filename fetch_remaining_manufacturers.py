#!/usr/bin/env python3
"""
Fetch models for the remaining 145 manufacturers using Playwright scraper.
Caps each manufacturer at 50 models to keep cache manageable.
"""

import json
import os
import sys
import time
import asyncio
from datetime import datetime
from pathlib import Path

# Add the scraper to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'API Scraper V2'))

try:
    from interactive_scraper import PartsTownExplorer
except ImportError:
    print("❌ Could not import PartsTownExplorer from ../API Scraper V2/")
    print("   Make sure the scraper is available in the parent directory")
    sys.exit(1)

# Cache directories
CACHE_DIR = os.path.join(os.path.dirname(__file__), 'cache')
MODELS_CACHE_DIR = os.path.join(CACHE_DIR, 'models')

class RemainingManufacturersFetcher:
    def __init__(self, max_models_per_manufacturer=50):
        self.scraper = None
        self.max_models = max_models_per_manufacturer
        self.stats = {
            'processed': 0,
            'success': 0,
            'failed': [],
            'total_models': 0,
            'start_time': time.time()
        }
    
    def get_missing_manufacturers(self):
        """Get list of manufacturers without cached models"""
        # Load manufacturers list
        with open(os.path.join(CACHE_DIR, 'manufacturers.json'), 'r') as f:
            manufacturers = json.load(f)
        
        # Check which ones don't have cache files
        missing = []
        for mfg in manufacturers:
            cache_file = os.path.join(MODELS_CACHE_DIR, f"{mfg['code']}.json")
            if not os.path.exists(cache_file):
                missing.append(mfg)
        
        return missing
    
    async def fetch_models_for_manufacturer(self, manufacturer):
        """Fetch models for a single manufacturer"""
        mfg_name = manufacturer['name']
        mfg_code = manufacturer['code']
        mfg_uri = manufacturer['uri']
        
        try:
            print(f"   🔍 Fetching models from {mfg_uri}...")
            
            # Use the scraper to get models
            models = await self.scraper.get_models_for_manufacturer(mfg_uri, mfg_code)
            
            if models:
                # Cap at max_models
                original_count = len(models)
                if len(models) > self.max_models:
                    models = models[:self.max_models]
                    print(f"   📊 Found {original_count} models, capped at {self.max_models}")
                else:
                    print(f"   ✅ Found {len(models)} models")
                
                # Save to cache
                cache_file = os.path.join(MODELS_CACHE_DIR, f"{mfg_code}.json")
                cache_data = {
                    'manufacturer': {
                        'name': mfg_name,
                        'code': mfg_code,
                        'uri': mfg_uri
                    },
                    'models': models,
                    'cached_at': datetime.now().isoformat(),
                    'source': 'fetch_remaining_manufacturers',
                    'capped': original_count > self.max_models
                }
                
                with open(cache_file, 'w') as f:
                    json.dump(cache_data, f, indent=2)
                
                print(f"   💾 Saved to cache: {os.path.basename(cache_file)}")
                
                self.stats['success'] += 1
                self.stats['total_models'] += len(models)
                return True
            else:
                print(f"   ⚠️ No models found")
                # Still save empty cache to avoid re-fetching
                cache_file = os.path.join(MODELS_CACHE_DIR, f"{mfg_code}.json")
                cache_data = {
                    'manufacturer': {
                        'name': mfg_name,
                        'code': mfg_code,
                        'uri': mfg_uri
                    },
                    'models': [],
                    'cached_at': datetime.now().isoformat(),
                    'source': 'fetch_remaining_manufacturers',
                    'note': 'No models found'
                }
                
                with open(cache_file, 'w') as f:
                    json.dump(cache_data, f, indent=2)
                
                return False
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            self.stats['failed'].append({
                'manufacturer': mfg_name,
                'code': mfg_code,
                'error': str(e)
            })
            return False
    
    def update_cache_timestamp(self):
        """Update the cache timestamp file"""
        timestamp_file = os.path.join(CACHE_DIR, 'cache_timestamp.json')
        
        # Count total cache files
        total_cached = len([f for f in os.listdir(MODELS_CACHE_DIR) if f.endswith('.json')])
        
        timestamp_data = {
            'last_updated': datetime.now().isoformat(),
            'total_manufacturers': 489,
            'total_models_cached': total_cached,
            'cache_completion': f"{(total_cached / 489) * 100:.1f}%",
            'last_batch': {
                'processed': self.stats['processed'],
                'success': self.stats['success'],
                'failed': len(self.stats['failed']),
                'total_models': self.stats['total_models']
            }
        }
        
        with open(timestamp_file, 'w') as f:
            json.dump(timestamp_data, f, indent=2)
        
        print(f"\n📅 Updated cache timestamp")
        print(f"   Total cache coverage: {total_cached}/489 ({(total_cached / 489) * 100:.1f}%)")
    
    async def run(self):
        """Main execution function"""
        print("=" * 60)
        print("FETCH REMAINING MANUFACTURERS WITH PLAYWRIGHT")
        print("=" * 60)
        
        # Get missing manufacturers
        missing = self.get_missing_manufacturers()
        
        if not missing:
            print("\n✅ All manufacturers already have cache files!")
            return
        
        print(f"\n📊 Found {len(missing)} manufacturers without cache")
        print(f"⚙️ Max models per manufacturer: {self.max_models}")
        
        # Show first 10
        print(f"\n🔍 First 10 manufacturers to fetch:")
        for i, mfg in enumerate(missing[:10]):
            print(f"   {i+1}. {mfg['name']} ({mfg['code']})")
        
        if len(missing) > 10:
            print(f"   ... and {len(missing) - 10} more")
        
        print(f"\n⏱️ Estimated time: {len(missing) * 15 / 60:.1f} minutes (15s per manufacturer)")
        
        response = input("\nProceed with all 145 manufacturers? (y/n): ")
        if response.lower() != 'y':
            print("Aborted.")
            return
        
        # Initialize scraper
        print("\n🚀 Initializing Playwright scraper...")
        self.scraper = PartsTownExplorer()
        print("✅ Scraper initialized")
        
        # Process each manufacturer
        print(f"\n🔄 Processing {len(missing)} manufacturers...")
        
        for i, manufacturer in enumerate(missing, 1):
            print(f"\n[{i}/{len(missing)}] 🏭 {manufacturer['name']} ({manufacturer['code']})")
            
            self.stats['processed'] += 1
            await self.fetch_models_for_manufacturer(manufacturer)
            
            # Rate limiting - wait between requests
            if i < len(missing):
                wait_time = 3  # 3 seconds between requests to be respectful
                print(f"   ⏳ Waiting {wait_time} seconds before next request...")
                await asyncio.sleep(wait_time)
            
            # Progress update every 10 manufacturers
            if i % 10 == 0:
                elapsed = time.time() - self.stats['start_time']
                rate = i / elapsed
                remaining = (len(missing) - i) / rate if rate > 0 else 0
                print(f"\n📈 Progress: {i}/{len(missing)} - ETA: {remaining/60:.1f} minutes")
        
        # Cleanup
        print("\n🧹 Scraper cleanup complete")
        
        # Update timestamp
        self.update_cache_timestamp()
        
        # Final summary
        elapsed_total = time.time() - self.stats['start_time']
        print("\n" + "=" * 60)
        print("COMPLETION SUMMARY")
        print("=" * 60)
        print(f"✅ Successfully cached: {self.stats['success']}/{self.stats['processed']}")
        print(f"📊 Total models fetched: {self.stats['total_models']}")
        print(f"⏱️ Total time: {elapsed_total/60:.1f} minutes")
        
        if self.stats['failed']:
            print(f"\n❌ Failed manufacturers: {len(self.stats['failed'])}")
            for item in self.stats['failed'][:5]:
                print(f"   - {item['manufacturer']}: {item['error'][:50]}")
            if len(self.stats['failed']) > 5:
                print(f"   ... and {len(self.stats['failed']) - 5} more")
        
        # Final cache status
        total_cached = len([f for f in os.listdir(MODELS_CACHE_DIR) if f.endswith('.json')])
        print(f"\n🎉 Final cache coverage: {total_cached}/489 ({(total_cached / 489) * 100:.1f}%)")
        
        if total_cached == 489:
            print("   🏆 Cache is now 100% complete!")

async def main():
    fetcher = RemainingManufacturersFetcher(max_models_per_manufacturer=50)
    await fetcher.run()

if __name__ == "__main__":
    asyncio.run(main())