#!/usr/bin/env python3
"""
Analyze page structure differences between manufacturers with and without models.
Compare successful (Henny Penny, Garland) vs failed (American Water Heaters, Bard).
"""

import subprocess
import json
import os
import re
import time

def fetch_page(manufacturer_uri, with_models_tab=False):
    """Fetch a manufacturer page with curl"""
    if with_models_tab:
        timestamp = int(time.time() * 1000)
        url = f"https://www.partstown.com/{manufacturer_uri}/parts?v={timestamp}&narrow=#id=mdptabmodels"
    else:
        url = f"https://www.partstown.com/{manufacturer_uri}/parts"
    
    curl_cmd = [
        'curl',
        '-s',  # Silent
        '-L',  # Follow redirects
        '-H', 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        '-H', 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        '-H', 'Accept-Language: en-US,en;q=0.9',
        '--compressed',
        '--max-time', '10',
        '-w', '\n===STATUS=%{http_code}===\n===REDIRECT=%{redirect_url}===',
        url
    ]
    
    try:
        result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=15)
        if result.returncode == 0:
            return result.stdout
        return None
    except:
        return None

def analyze_page(html_content, manufacturer_name):
    """Analyze page structure and content"""
    if not html_content:
        return {"error": "No content"}
    
    analysis = {
        "manufacturer": manufacturer_name,
        "status_code": None,
        "redirect_url": None,
        "has_models_section": False,
        "has_parts_section": False,
        "model_links": [],
        "api_endpoints": [],
        "javascript_data": {},
        "page_type": "unknown"
    }
    
    # Extract status and redirect
    status_match = re.search(r'===STATUS=(\d+)===', html_content)
    if status_match:
        analysis["status_code"] = status_match.group(1)
    
    redirect_match = re.search(r'===REDIRECT=(.+?)===', html_content)
    if redirect_match and redirect_match.group(1):
        analysis["redirect_url"] = redirect_match.group(1)
    
    # Check for direct model redirect (single model manufacturer)
    if analysis["redirect_url"] and '/parts' not in analysis["redirect_url"]:
        analysis["page_type"] = "single_model_redirect"
        # Extract model from redirect
        model_match = re.search(r'/([^/]+)$', analysis["redirect_url"])
        if model_match:
            analysis["single_model"] = model_match.group(1)
    
    # Look for model links
    model_pattern = rf'href="/[^/]+/([^/"]+)/parts"'
    model_matches = re.findall(model_pattern, html_content)
    analysis["model_links"] = list(set(model_matches))[:10]  # First 10 unique
    
    # Look for API endpoints
    api_patterns = [
        r'"/api/[^"]+models[^"]*"',
        r'"/[^"]+/models[^"]*"',
        r'"modelData":\s*"([^"]+)"',
        r'data-models-url="([^"]+)"'
    ]
    
    for pattern in api_patterns:
        matches = re.findall(pattern, html_content)
        analysis["api_endpoints"].extend(matches[:3])
    
    # Look for JavaScript model data
    js_patterns = [
        (r'window\.models\s*=\s*(\[.*?\]);', 'window.models'),
        (r'var\s+models\s*=\s*(\[.*?\]);', 'var models'),
        (r'"models":\s*(\[.*?\])', 'json models'),
        (r'data-models=\'([^\']+)\'', 'data-models attribute')
    ]
    
    for pattern, name in js_patterns:
        match = re.search(pattern, html_content, re.DOTALL)
        if match:
            analysis["javascript_data"][name] = match.group(1)[:100] + "..."
    
    # Check for sections
    if 'id="mdptabmodels"' in html_content or 'Models</h' in html_content:
        analysis["has_models_section"] = True
    
    if 'id="mdptabparts"' in html_content or 'Parts</h' in html_content:
        analysis["has_parts_section"] = True
    
    # Determine page type
    if analysis["model_links"]:
        analysis["page_type"] = "multi_model"
    elif analysis["has_models_section"]:
        analysis["page_type"] = "models_tab_present"
    elif analysis["redirect_url"]:
        analysis["page_type"] = "redirect"
    else:
        analysis["page_type"] = "standard_parts"
    
    return analysis

def main():
    print("=" * 70)
    print("ANALYZING PAGE STRUCTURE DIFFERENCES")
    print("=" * 70)
    
    # Test cases: successful vs failed manufacturers
    test_cases = [
        # Successful (have models in cache)
        {"name": "Henny Penny", "uri": "henny-penny", "status": "success"},
        {"name": "Garland", "uri": "garland", "status": "success"},
        {"name": "Pitco", "uri": "pitco", "status": "success"},
        
        # Failed (no models in cache)
        {"name": "American Water Heaters", "uri": "american-water-heaters", "status": "failed"},
        {"name": "Bard", "uri": "bard", "status": "failed"},
        {"name": "Blue Air", "uri": "blue-air", "status": "failed"},
    ]
    
    results = []
    
    # Test 1: Without mdptabmodels parameter
    print("\n📊 TEST 1: Standard URL (no mdptabmodels)")
    print("-" * 70)
    
    for case in test_cases:
        print(f"\n🔍 Analyzing {case['name']} ({case['status']})...")
        html = fetch_page(case['uri'], with_models_tab=False)
        analysis = analyze_page(html, case['name'])
        analysis["expected_status"] = case["status"]
        analysis["url_type"] = "standard"
        results.append(analysis)
        
        print(f"   Status: {analysis['status_code']}")
        print(f"   Page type: {analysis['page_type']}")
        print(f"   Model links found: {len(analysis['model_links'])}")
        if analysis['redirect_url']:
            print(f"   Redirects to: {analysis['redirect_url']}")
        if analysis.get('single_model'):
            print(f"   Single model: {analysis['single_model']}")
    
    # Test 2: With mdptabmodels parameter
    print("\n📊 TEST 2: With mdptabmodels parameter")
    print("-" * 70)
    
    for case in test_cases:
        print(f"\n🔍 Analyzing {case['name']} with models tab...")
        html = fetch_page(case['uri'], with_models_tab=True)
        analysis = analyze_page(html, case['name'])
        analysis["expected_status"] = case["status"]
        analysis["url_type"] = "with_models_tab"
        results.append(analysis)
        
        print(f"   Status: {analysis['status_code']}")
        print(f"   Page type: {analysis['page_type']}")
        print(f"   Model links found: {len(analysis['model_links'])}")
        if analysis['redirect_url']:
            print(f"   Redirects to: {analysis['redirect_url']}")
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY OF FINDINGS")
    print("=" * 70)
    
    # Group by success/failure
    successful = [r for r in results if r["expected_status"] == "success"]
    failed = [r for r in results if r["expected_status"] == "failed"]
    
    print("\n✅ SUCCESSFUL MANUFACTURERS (have models in cache):")
    for r in successful[:6]:  # Show first 3 of each type
        print(f"   {r['manufacturer']:25} - {r['url_type']:15} - Type: {r['page_type']:20} - Models: {len(r['model_links'])}")
    
    print("\n❌ FAILED MANUFACTURERS (no models in cache):")
    for r in failed[:6]:
        print(f"   {r['manufacturer']:25} - {r['url_type']:15} - Type: {r['page_type']:20} - Models: {len(r['model_links'])}")
        if r.get('single_model'):
            print(f"      → Single model redirect: {r['single_model']}")
    
    # Key differences
    print("\n🔑 KEY DIFFERENCES:")
    print("-" * 70)
    
    # Check redirects
    success_redirects = sum(1 for r in successful if r.get('redirect_url'))
    failed_redirects = sum(1 for r in failed if r.get('redirect_url'))
    print(f"Redirects: Successful={success_redirects}/{len(successful)}, Failed={failed_redirects}/{len(failed)}")
    
    # Check model links
    success_with_models = sum(1 for r in successful if r['model_links'])
    failed_with_models = sum(1 for r in failed if r['model_links'])
    print(f"Has model links: Successful={success_with_models}/{len(successful)}, Failed={failed_with_models}/{len(failed)}")
    
    # Check impact of mdptabmodels
    print("\n📊 IMPACT OF mdptabmodels PARAMETER:")
    for name in ["Henny Penny", "American Water Heaters"]:
        standard = [r for r in results if r['manufacturer'] == name and r['url_type'] == 'standard'][0]
        with_tab = [r for r in results if r['manufacturer'] == name and r['url_type'] == 'with_models_tab'][0]
        
        print(f"\n{name}:")
        print(f"   Standard URL: {len(standard['model_links'])} models, type={standard['page_type']}")
        print(f"   With models tab: {len(with_tab['model_links'])} models, type={with_tab['page_type']}")
        
        if standard['model_links'] != with_tab['model_links']:
            print(f"   ⚠️ Different results with mdptabmodels!")
    
    # Save detailed results
    with open('page_analysis_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Detailed results saved to page_analysis_results.json")

if __name__ == "__main__":
    main()