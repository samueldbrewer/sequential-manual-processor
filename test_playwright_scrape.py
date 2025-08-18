#!/usr/bin/env python3
"""
Test Playwright scraping to see what it can extract that curl cannot.
"""

import asyncio
import json
import sys
import os

# Add the scraper path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'API Scraper V2'))

from interactive_scraper import PartsTownExplorer

async def test_manufacturer(manufacturer_uri, manufacturer_code):
    """Test scraping a single manufacturer"""
    scraper = PartsTownExplorer()
    
    print(f"\n🔍 Testing {manufacturer_uri} with Playwright...")
    
    try:
        models = await scraper.get_models_for_manufacturer(manufacturer_uri, manufacturer_code)
        
        if models:
            print(f"✅ Found {len(models)} models!")
            print("\nFirst 5 models:")
            for model in models[:5]:
                print(f"   - {model.get('name', 'unknown')} ({model.get('code', 'unknown')})")
        else:
            print("❌ No models found")
            
        return models
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

async def main():
    print("=" * 70)
    print("TESTING PLAYWRIGHT VS CURL SCRAPING")
    print("=" * 70)
    
    # Test cases
    test_cases = [
        # Known successful
        {"uri": "henny-penny", "code": "PT_CAT1095", "name": "Henny Penny"},
        {"uri": "garland", "code": "PT_CAT1086", "name": "Garland"},
        
        # Known failures
        {"uri": "american-water-heaters", "code": "PT_CAT375835", "name": "American Water Heaters"},
        {"uri": "bard", "code": "PT_CAT223818", "name": "Bard"},
    ]
    
    results = {}
    
    for case in test_cases:
        print(f"\n{'='*50}")
        print(f"Manufacturer: {case['name']}")
        print(f"URI: {case['uri']}")
        print(f"Code: {case['code']}")
        
        models = await test_manufacturer(case['uri'], case['code'])
        
        results[case['name']] = {
            "uri": case['uri'],
            "code": case['code'],
            "model_count": len(models) if models else 0,
            "sample_models": [m.get('name', 'unknown') for m in (models[:3] if models else [])]
        }
        
        # Wait between requests
        await asyncio.sleep(2)
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    for name, data in results.items():
        print(f"\n{name}:")
        print(f"   Models found: {data['model_count']}")
        if data['sample_models']:
            print(f"   Samples: {', '.join(data['sample_models'])}")
    
    # Save results
    with open('playwright_test_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Results saved to playwright_test_results.json")

if __name__ == "__main__":
    asyncio.run(main())