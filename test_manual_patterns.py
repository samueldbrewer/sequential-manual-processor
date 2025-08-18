#!/usr/bin/env python3
"""
Test script to analyze PartsTown manual URL patterns across different manufacturers
"""

import json
import time
from fetch_manuals_subprocess import fetch_manuals_for_model

# Test combinations as specified
TEST_CASES = [
    # Henny Penny
    ("henny-penny", "500"),
    ("henny-penny", "320"),
    ("henny-penny", "600"),
    
    # APW Wyott
    ("apw-wyott", "at-10"),
    ("apw-wyott", "m-83"),
    ("apw-wyott", "hd-4"),
    
    # Delfield
    ("delfield", "4427n"),
    ("delfield", "4448n"),
    ("delfield", "f17"),
    
    # Frymaster
    ("frymaster", "mj35"),
    ("frymaster", "re14"),
    ("frymaster", "h55"),
    
    # True
    ("true", "t-23"),
    ("true", "gdm-49"),
    ("true", "tuc-27")
]

def analyze_manual_patterns():
    """Fetch manual URLs and analyze patterns"""
    
    results = {}
    all_urls = []
    
    print("Testing PartsTown manual URL patterns...")
    print("=" * 60)
    
    for manufacturer_uri, model_code in TEST_CASES:
        print(f"\nTesting {manufacturer_uri} / {model_code}")
        print("-" * 40)
        
        try:
            manuals = fetch_manuals_for_model(manufacturer_uri, model_code)
            
            if manuals:
                print(f"Found {len(manuals)} manuals:")
                for manual in manuals:
                    print(f"  - {manual['type']}: {manual['link']}")
                    all_urls.append({
                        'manufacturer_uri': manufacturer_uri,
                        'model_code': model_code,
                        'manual_type': manual['type'],
                        'url': manual['link'],
                        'title': manual['title']
                    })
                
                results[f"{manufacturer_uri}_{model_code}"] = manuals
            else:
                print("  No manuals found")
                results[f"{manufacturer_uri}_{model_code}"] = []
            
            # Be respectful - add delay between requests
            time.sleep(2)
            
        except Exception as e:
            print(f"  Error: {e}")
            results[f"{manufacturer_uri}_{model_code}"] = []
    
    return results, all_urls

def analyze_url_patterns(all_urls):
    """Analyze patterns in the fetched URLs"""
    
    print("\n" + "=" * 60)
    print("URL PATTERN ANALYSIS")
    print("=" * 60)
    
    if not all_urls:
        print("No URLs found to analyze")
        return
    
    # Group by manufacturer
    by_manufacturer = {}
    for url_data in all_urls:
        manufacturer = url_data['manufacturer_uri']
        if manufacturer not in by_manufacturer:
            by_manufacturer[manufacturer] = []
        by_manufacturer[manufacturer].append(url_data)
    
    print(f"\nTotal URLs found: {len(all_urls)}")
    print(f"Manufacturers with manuals: {len(by_manufacturer)}")
    
    # Analyze each manufacturer's patterns
    for manufacturer, urls in by_manufacturer.items():
        print(f"\n{manufacturer.upper()} ANALYSIS:")
        print("-" * 30)
        print(f"Manual count: {len(urls)}")
        
        # Show sample URLs
        print("Sample URLs:")
        for url_data in urls[:3]:  # Show first 3
            print(f"  {url_data['model_code']} ({url_data['manual_type']}): {url_data['url']}")
        
        # Extract URL patterns
        url_patterns = set()
        for url_data in urls:
            url = url_data['url']
            # Extract the pattern between modelManual/ and the file extension
            if '/modelManual/' in url:
                manual_part = url.split('/modelManual/')[1]
                if '.' in manual_part:
                    filename = manual_part.split('.')[0]  # Remove extension
                    url_patterns.add(filename)
        
        print(f"Filename patterns found:")
        for pattern in sorted(url_patterns):
            print(f"  {pattern}")
    
    # Analyze filename patterns across all URLs
    print(f"\nFILENAME PATTERN ANALYSIS:")
    print("-" * 30)
    
    filename_structures = {}
    manufacturer_prefixes = set()
    model_transformations = {}
    
    for url_data in all_urls:
        url = url_data['url']
        manufacturer = url_data['manufacturer_uri']
        model = url_data['model_code']
        manual_type = url_data['manual_type']
        
        if '/modelManual/' in url:
            manual_part = url.split('/modelManual/')[1]
            if '.' in manual_part:
                filename = manual_part.split('.')[0]  # Remove extension
                
                # Try to identify manufacturer prefix
                if '_' in filename:
                    potential_prefix = filename.split('_')[0].lower()
                    manufacturer_prefixes.add(potential_prefix)
                
                # Store the transformation
                key = f"{manufacturer}_{model}"
                if key not in model_transformations:
                    model_transformations[key] = []
                model_transformations[key].append({
                    'original_model': model,
                    'filename': filename,
                    'manual_type': manual_type,
                    'url': url
                })
                
                # Analyze filename structure
                structure = filename.replace(model.upper(), 'MODEL').replace(model.lower(), 'MODEL')
                if structure not in filename_structures:
                    filename_structures[structure] = []
                filename_structures[structure].append({
                    'manufacturer': manufacturer,
                    'model': model,
                    'filename': filename,
                    'manual_type': manual_type
                })
    
    print(f"Potential manufacturer prefixes: {sorted(manufacturer_prefixes)}")
    
    print(f"\nFilename structures (MODEL = model placeholder):")
    for structure, examples in filename_structures.items():
        print(f"  {structure}")
        print(f"    Examples: {len(examples)} files")
        for example in examples[:2]:  # Show 2 examples
            print(f"      {example['manufacturer']} {example['model']} -> {example['filename']} ({example['manual_type']})")
    
    print(f"\nModel transformations by manufacturer:")
    for key, transformations in model_transformations.items():
        manufacturer, model = key.split('_', 1)
        print(f"  {manufacturer} | {model}:")
        for t in transformations:
            print(f"    {t['manual_type']}: {t['filename']}")
    
    return by_manufacturer, filename_structures, model_transformations

def save_results(results, all_urls, analysis_data):
    """Save results to JSON file"""
    
    output_data = {
        'test_cases': TEST_CASES,
        'results': results,
        'all_urls': all_urls,
        'analysis': {
            'by_manufacturer': analysis_data[0],
            'filename_structures': analysis_data[1],
            'model_transformations': analysis_data[2]
        },
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
    }
    
    with open('manual_patterns_analysis.json', 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"\nResults saved to manual_patterns_analysis.json")

if __name__ == "__main__":
    print("PartsTown Manual URL Pattern Analysis")
    print("=====================================")
    
    # Fetch manual data
    results, all_urls = analyze_manual_patterns()
    
    # Analyze patterns
    analysis_data = analyze_url_patterns(all_urls)
    
    # Save results
    save_results(results, all_urls, analysis_data)
    
    print(f"\nAnalysis complete!")