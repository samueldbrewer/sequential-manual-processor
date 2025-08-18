#!/usr/bin/env python3
"""
Command-line tool to test model loading for manufacturers
Usage: python test_models.py [manufacturer_code]
"""

import sys
import asyncio
import json
from datetime import datetime

# Add the scraper to path
import os
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
scraper_path = os.path.join(parent_dir, 'API Scraper V2')
sys.path.append(scraper_path)
from interactive_scraper import PartsTownExplorer

async def test_manufacturer_models(manufacturer_code=None):
    """Test loading models for a manufacturer"""
    explorer = PartsTownExplorer()
    
    print("="*60)
    print("🔍 PARTSTOWN MODEL LOADER TEST")
    print("="*60)
    
    # Get manufacturers list
    print("\n📋 Fetching manufacturers list...")
    manufacturers = await explorer.get_manufacturers()
    print(f"✅ Found {len(manufacturers)} manufacturers")
    
    if not manufacturer_code:
        # Show top manufacturers
        print("\n📊 Top manufacturers by model count:")
        sorted_mfrs = sorted(manufacturers, key=lambda x: x['model_count'], reverse=True)[:10]
        for i, mfr in enumerate(sorted_mfrs, 1):
            print(f"{i:2}. {mfr['name']:<30} ({mfr['model_count']} models) - Code: {mfr['code']}")
        
        print("\n💡 Usage: python test_models.py <manufacturer_code>")
        print("   Example: python test_models.py PT_CAT1095")
        return
    
    # Find the specific manufacturer
    manufacturer = next((m for m in manufacturers if m['code'] == manufacturer_code), None)
    if not manufacturer:
        print(f"❌ Manufacturer with code '{manufacturer_code}' not found")
        print("\n Available codes:")
        for m in manufacturers[:20]:
            if manufacturer_code.lower() in m['name'].lower() or manufacturer_code.lower() in m['code'].lower():
                print(f"  - {m['code']}: {m['name']}")
        return
    
    print(f"\n🏭 Testing: {manufacturer['name']}")
    print(f"📍 URI: {manufacturer['uri']}")
    print(f"📊 Expected models: {manufacturer['model_count']}")
    print("-"*60)
    
    # Warn about manufacturers with too many models
    if manufacturer['model_count'] > 10000:
        print(f"\n⚠️  WARNING: This manufacturer has {manufacturer['model_count']:,} models!")
        print("   This may crash the browser or take a very long time.")
        print("   Consider testing with a smaller manufacturer instead.")
        response = input("\n   Continue anyway? (y/N): ")
        if response.lower() != 'y':
            print("\n❌ Test cancelled")
            return
    
    # Load models
    start_time = datetime.now()
    print(f"\n⏱️  Starting at {start_time.strftime('%H:%M:%S')}")
    print("🔄 Loading models (this may take 30-60 seconds)...\n")
    
    models = await explorer.get_models_for_manufacturer(
        manufacturer['uri'], 
        manufacturer['code']
    )
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print("\n" + "="*60)
    print("📊 RESULTS")
    print("="*60)
    print(f"✅ Successfully loaded {len(models)} models")
    print(f"⏱️  Time taken: {duration:.1f} seconds")
    print(f"📈 Expected: {manufacturer['model_count']}, Got: {len(models)}")
    
    if models:
        print(f"\n📋 First 10 models:")
        for i, model in enumerate(models[:10], 1):
            name = model.get('name', 'Unknown')
            code = model.get('code', model.get('modelCode', 'N/A'))
            url = model.get('url', '')
            print(f"{i:2}. {name:<40} (Code: {code})")
            if url:
                print(f"    URL: {url}")
        
        if len(models) > 10:
            print(f"\n... and {len(models) - 10} more models")
        
        # Save to file
        output_file = f"models_{manufacturer_code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump({
                'manufacturer': manufacturer,
                'model_count': len(models),
                'models': models,
                'timestamp': datetime.now().isoformat()
            }, f, indent=2)
        print(f"\n💾 Full results saved to: {output_file}")
    else:
        print("❌ No models found")
    
    print("\n" + "="*60)

async def main():
    """Main entry point"""
    manufacturer_code = sys.argv[1] if len(sys.argv) > 1 else None
    
    try:
        await test_manufacturer_models(manufacturer_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())