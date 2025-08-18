#!/usr/bin/env python3
"""
Test script to understand how manual links are retrieved
"""

import asyncio
import sys
import os

# Add the scraper to the path
sys.path.append('../API Scraper V2')
from interactive_scraper import PartsTownExplorer

async def test_manual_retrieval():
    explorer = PartsTownExplorer()
    
    # Test with Henny Penny first - we know it has models
    print("🔧 Testing manual retrieval for Henny Penny...")
    
    # Get models first
    models = await explorer.get_models_for_manufacturer('henny-penny', 'PT_CAT1095')
    print(f"📊 Found {len(models)} models for Henny Penny")
    
    if models:
        # Test with first few models
        for i, model in enumerate(models[:3]):
            print(f"\n🔍 Testing model {i+1}: {model['name']} ({model['code']})")
            print(f"   Model URL: {model['url']}")
            
            # Try to get manuals for this model
            try:
                # The current scraper has multiple methods - let's see which one works
                # Method 1: Direct manuals endpoint (if it exists)
                print(f"   Attempting to get manuals...")
                
                # For now, let's just show what we would need to scrape
                # The model URL format is: /henny-penny/model-name/parts
                # Manuals are usually at: /henny-penny/model-name/manuals
                
                manual_url = model['url'].replace('/parts', '/manuals')
                print(f"   Expected manual URL: https://www.partstown.com{manual_url}")
                
                # We would scrape this page to get the manual links
                # Manual links typically look like: /modelManual/FILENAME_TYPE.pdf
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
    
    else:
        print("❌ No models found - can't test manual retrieval")

if __name__ == "__main__":
    asyncio.run(test_manual_retrieval())