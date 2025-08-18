#!/usr/bin/env python3
"""
Synchronous manual fetcher using requests and BeautifulSoup
Simpler approach without browser automation
"""

import requests
from bs4 import BeautifulSoup
import re

def fetch_manuals_simple(manufacturer_uri, model_code):
    """Fetch manuals using simple HTTP request"""
    
    model_url = f"https://www.partstown.com/{manufacturer_uri}/{model_code}/parts"
    print(f"🔍 Fetching manuals from: {model_url}")
    
    try:
        # Simple HTTP request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(model_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find manual links
        manual_links = soup.find_all('a', href=re.compile(r'/modelManual/'))
        
        manuals = []
        for link in manual_links:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            
            if href:
                # Extract manual type from filename
                if '_spm.' in href:
                    manual_type = 'spm'
                    title = 'Service & Parts Manual'
                elif '_iom.' in href:
                    manual_type = 'iom'
                    title = 'Installation & Operation Manual'
                elif '_pm.' in href:
                    manual_type = 'pm'
                    title = 'Parts Manual'
                elif '_wd.' in href:
                    manual_type = 'wd'
                    title = 'Wiring Diagrams'
                elif '_sm.' in href:
                    manual_type = 'sm'
                    title = 'Service Manual'
                else:
                    manual_type = 'unknown'
                    title = text if text else 'Manual'
                
                manuals.append({
                    'type': manual_type,
                    'title': title,
                    'link': href,
                    'text': text if text else title
                })
        
        print(f"✅ Found {len(manuals)} manuals")
        return manuals
        
    except Exception as e:
        print(f"❌ Error fetching manuals: {e}")
        # If simple request fails, return empty list
        # The site might require JavaScript rendering
        return []

if __name__ == "__main__":
    # Test with APW Wyott AT-10
    manuals = fetch_manuals_simple("apw-wyott", "at-10")
    import json
    print(json.dumps(manuals, indent=2))