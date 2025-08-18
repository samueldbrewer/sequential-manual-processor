#!/usr/bin/env python3
"""
Test programmatic manual URL construction and validation
"""

import requests
import asyncio

def test_manual_url_exists(url):
    """Test if a manual URL exists using HEAD request"""
    try:
        response = requests.head(f"https://www.partstown.com{url}", timeout=10)
        return response.status_code == 200
    except:
        return False

def construct_manual_urls(manufacturer_prefix, model_code):
    """Construct all possible manual URLs for a model"""
    manual_types = ['spm', 'iom', 'pm', 'wd', 'sm']
    urls = []
    
    for manual_type in manual_types:
        # Try different model code formats
        possible_codes = [
            model_code,                    # As-is: "500pvs"
            model_code.upper(),           # Upper: "500PVS"  
            model_code.replace('pvs', 'PVS'), # Mixed: "500PVS"
        ]
        
        for code in possible_codes:
            url = f"/modelManual/{manufacturer_prefix}-{code}_{manual_type}.pdf"
            urls.append((manual_type, url))
    
    return urls

def test_henny_penny_models():
    """Test manual URL construction for Henny Penny models"""
    print("🔧 Testing manual URL construction for Henny Penny...")
    
    # Test models we know exist
    test_cases = [
        ("HEN", "500", "Henny Penny 500"),
        ("HEN", "PF500", "Henny Penny 500 (with PF prefix)"),
        ("HEN", "500pvs", "Henny Penny 500PVS"),
        ("HEN", "PF500pvs", "Henny Penny 500PVS (with PF prefix)"),
    ]
    
    for prefix, model_code, description in test_cases:
        print(f"\n🔍 Testing: {description}")
        manual_urls = construct_manual_urls(prefix, model_code)
        
        for manual_type, url in manual_urls:
            exists = test_manual_url_exists(url)
            status = "✅" if exists else "❌"
            print(f"   {status} {manual_type.upper()}: {url}")
            
            # If we find a working URL, we've discovered the pattern!
            if exists:
                print(f"      🎯 FOUND WORKING URL!")

if __name__ == "__main__":
    test_henny_penny_models()