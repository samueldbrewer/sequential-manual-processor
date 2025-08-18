#!/usr/bin/env python3
"""
Test script to simulate Railway environment locally
"""

import os
import sys

# Set PORT to simulate Railway environment
os.environ['PORT'] = '8080'

# Now import and test the fetch function
from fetch_manuals_curl import fetch_manuals_via_curl

def test_manual_fetch():
    print("="*60)
    print("TESTING RAILWAY ENVIRONMENT LOCALLY")
    print("="*60)
    
    # Test with a known model
    manufacturer_uri = "henny-penny"
    model_code = "500"
    
    print(f"\n📋 Testing: {manufacturer_uri}/{model_code}")
    print(f"📊 Environment: PORT={os.environ.get('PORT')}")
    
    try:
        manuals = fetch_manuals_via_curl(manufacturer_uri, model_code)
        
        if manuals:
            print(f"\n✅ SUCCESS: Found {len(manuals)} manuals:")
            for manual in manuals:
                print(f"  - {manual['title']}: {manual['link']}")
        else:
            print("\n⚠️ No manuals found (but no errors)")
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_manual_fetch()