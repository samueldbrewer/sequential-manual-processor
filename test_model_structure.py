#!/usr/bin/env python3
"""
Test to see the structure of model data and check for manual links
"""

import asyncio
import sys
import os
import json

# Add the scraper to the path
sys.path.append('../API Scraper V2')
from interactive_scraper import PartsTownExplorer

async def test_model_structure():
    explorer = PartsTownExplorer()
    
    print("🔧 Getting model structure for Henny Penny...")
    
    # Get models
    models = await explorer.get_models_for_manufacturer('henny-penny', 'PT_CAT1095')
    print(f"📊 Found {len(models)} models")
    
    if models:
        # Show structure of first few models
        for i, model in enumerate(models[:5]):
            print(f"\n🔍 Model {i+1}: {model['name']}")
            print(f"   Full structure:")
            print(json.dumps(model, indent=4))
            
            # Check if manuals are already included
            if 'manuals' in model:
                print(f"   ✅ Has manual links directly in model data!")
                for manual in model['manuals']:
                    print(f"      • {manual}")
            else:
                print(f"   ❌ No manual links in model data - need to scrape separately")
            
            print("-" * 50)

if __name__ == "__main__":
    asyncio.run(test_model_structure())