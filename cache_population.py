#!/usr/bin/env python3
"""
Cache Population Script - Pre-scrape manufacturers and models for caching
Caps each manufacturer at 50 models to keep cache size manageable
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime

# Add the scraper to the path
sys.path.append('../API Scraper V2')
from interactive_scraper import PartsTownExplorer

class CachePopulator:
    def __init__(self, max_models_per_manufacturer=50):
        self.scraper = PartsTownExplorer()
        self.max_models = max_models_per_manufacturer
        self.cache_dir = "cache"
        self.stats = {
            'manufacturers_processed': 0,
            'models_cached': 0,
            'start_time': time.time(),
            'errors': []
        }
        
        # Create cache directory
        os.makedirs(self.cache_dir, exist_ok=True)
        os.makedirs(f"{self.cache_dir}/models", exist_ok=True)
    
    def save_cache_timestamp(self):
        """Save when the cache was last updated"""
        timestamp_data = {
            'last_updated': datetime.now().isoformat(),
            'total_manufacturers': self.stats['manufacturers_processed'],
            'total_models_cached': self.stats['models_cached'],
            'max_models_per_manufacturer': self.max_models,
            'errors': self.stats['errors']
        }
        
        with open(f"{self.cache_dir}/cache_timestamp.json", 'w') as f:
            json.dump(timestamp_data, f, indent=2)
    
    async def populate_cache(self):
        """Main cache population function"""
        print(f"🚀 Starting cache population (max {self.max_models} models per manufacturer)")
        print(f"📂 Cache directory: {self.cache_dir}")
        
        try:
            # Step 1: Get all manufacturers
            print("\n📋 Fetching all manufacturers...")
            manufacturers = await self.scraper.get_manufacturers()
            
            if not manufacturers:
                print("❌ No manufacturers found")
                return
            
            print(f"✅ Found {len(manufacturers)} manufacturers")
            
            # Save manufacturers to cache
            with open(f"{self.cache_dir}/manufacturers.json", 'w') as f:
                json.dump(manufacturers, f, indent=2)
            
            print(f"💾 Saved manufacturers to cache")
            
            # Step 2: Process each manufacturer
            print(f"\n🔄 Processing manufacturers (limited to {self.max_models} models each)...")
            
            for i, manufacturer in enumerate(manufacturers):
                mfg_name = manufacturer['name']
                mfg_code = manufacturer['code']
                mfg_uri = manufacturer['uri']
                
                print(f"\n[{i+1}/{len(manufacturers)}] 🏭 Processing: {mfg_name}")
                print(f"   Code: {mfg_code}, URI: {mfg_uri}")
                
                try:
                    # Get models for this manufacturer
                    models = await self.scraper.get_models_for_manufacturer(mfg_uri, mfg_code)
                    
                    if models:
                        # Cap at max_models
                        if len(models) > self.max_models:
                            print(f"   📊 Found {len(models)} models, capping at {self.max_models}")
                            models = models[:self.max_models]
                        else:
                            print(f"   📊 Found {len(models)} models")
                        
                        # Save models to cache file
                        cache_file = f"{self.cache_dir}/models/{mfg_code}.json"
                        cache_data = {
                            'manufacturer': {
                                'name': mfg_name,
                                'code': mfg_code,
                                'uri': mfg_uri
                            },
                            'models': models,
                            'total_models': len(models),
                            'cached_at': datetime.now().isoformat()
                        }
                        
                        with open(cache_file, 'w') as f:
                            json.dump(cache_data, f, indent=2)
                        
                        self.stats['models_cached'] += len(models)
                        print(f"   ✅ Cached {len(models)} models")
                    else:
                        print(f"   ⚠️ No models found")
                
                except Exception as e:
                    error_msg = f"Error processing {mfg_name}: {str(e)}"
                    print(f"   ❌ {error_msg}")
                    self.stats['errors'].append(error_msg)
                
                self.stats['manufacturers_processed'] += 1
                
                # Show progress
                elapsed = time.time() - self.stats['start_time']
                rate = self.stats['manufacturers_processed'] / elapsed if elapsed > 0 else 0
                remaining = len(manufacturers) - self.stats['manufacturers_processed']
                eta = remaining / rate if rate > 0 else 0
                
                print(f"   📈 Progress: {self.stats['manufacturers_processed']}/{len(manufacturers)} "
                      f"({rate:.1f}/min, ETA: {eta/60:.1f}min)")
                
                # Small delay to be respectful
                await asyncio.sleep(0.5)
        
        except Exception as e:
            print(f"❌ Critical error: {e}")
            self.stats['errors'].append(f"Critical error: {str(e)}")
        
        finally:
            # Save cache timestamp and stats
            self.save_cache_timestamp()
            
            # Final statistics
            elapsed = time.time() - self.stats['start_time']
            print(f"\n{'='*60}")
            print(f"🎉 Cache Population Complete!")
            print(f"{'='*60}")
            print(f"⏱️ Total time: {elapsed/60:.1f} minutes")
            print(f"🏭 Manufacturers processed: {self.stats['manufacturers_processed']}")
            print(f"🔧 Models cached: {self.stats['models_cached']}")
            print(f"❌ Errors: {len(self.stats['errors'])}")
            
            if self.stats['errors']:
                print(f"\nErrors encountered:")
                for error in self.stats['errors']:
                    print(f"   • {error}")

async def main():
    # Default to 50 models per manufacturer unless specified
    max_models = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    
    populator = CachePopulator(max_models_per_manufacturer=max_models)
    await populator.populate_cache()

if __name__ == "__main__":
    print("🔧 PartsTown Cache Population Tool")
    print("Usage: python cache_population.py [max_models_per_manufacturer]")
    print("Example: python cache_population.py 50")
    print()
    
    asyncio.run(main())