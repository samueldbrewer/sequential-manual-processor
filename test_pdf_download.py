#!/usr/bin/env python3
"""
Test different methods for downloading PDFs from PartsTown
Compare curl, requests, and Playwright approaches
"""

import subprocess
import requests
import time
import os
import hashlib

# Test PDFs from different manufacturers
TEST_PDFS = [
    {
        "name": "Henny Penny 500 SPM",
        "url": "/modelManual/HEN-PF500_spm.pdf?v=1655476514087",
        "manufacturer": "henny-penny",
        "model": "500"
    },
    {
        "name": "Globe 2500 PM",
        "url": "/modelManual/GLO-2XXX_pm.pdf?v=1655476541971",
        "manufacturer": "globe",
        "model": "2500"
    },
    {
        "name": "Pitco 14 PM",
        "url": "/modelManual/PT-7-12-14-14R-PR14-PM14-18_pm.pdf?v=1655476704727",
        "manufacturer": "pitco",
        "model": "14"
    }
]

def method1_direct_curl(pdf_url):
    """Method 1: Direct curl download"""
    print(f"\n🔍 Method 1: Direct curl download")
    
    # Ensure full URL
    if pdf_url.startswith('/'):
        full_url = f"https://www.partstown.com{pdf_url}"
    else:
        full_url = pdf_url
    
    print(f"   URL: {full_url}")
    
    # Output filename
    pdf_hash = hashlib.md5(pdf_url.encode()).hexdigest()
    output_file = f"test_pdfs/{pdf_hash}_curl.pdf"
    os.makedirs("test_pdfs", exist_ok=True)
    
    curl_cmd = [
        'curl',
        '-s',  # Silent
        '-L',  # Follow redirects
        '-H', 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        '-H', 'Accept: application/pdf,*/*',
        '-H', 'Accept-Language: en-US,en;q=0.9',
        '--compressed',
        '--max-time', '30',
        '-o', output_file,  # Output to file
        '-w', '%{http_code}|%{size_download}|%{time_total}',  # Write stats
        full_url
    ]
    
    start_time = time.time()
    
    try:
        result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=35)
        elapsed = time.time() - start_time
        
        if result.returncode == 0:
            # Parse curl stats
            stats = result.stdout.strip().split('|')
            http_code = stats[0] if len(stats) > 0 else '?'
            size = int(stats[1]) if len(stats) > 1 else 0
            
            print(f"   Status: {http_code}")
            print(f"   Time: {elapsed:.2f}s")
            
            # Check if we got a PDF
            if os.path.exists(output_file):
                file_size = os.path.getsize(output_file)
                print(f"   File size: {file_size:,} bytes")
                
                # Check if it's actually a PDF
                with open(output_file, 'rb') as f:
                    header = f.read(4)
                    if header == b'%PDF':
                        print(f"   ✅ Valid PDF downloaded!")
                        return {"success": True, "size": file_size, "time": elapsed, "method": "curl"}
                    else:
                        print(f"   ❌ Not a PDF. Header: {header}")
                        # Check if it's HTML (error page)
                        f.seek(0)
                        content = f.read(1000).decode('utf-8', errors='ignore')
                        if '<html' in content.lower():
                            print(f"   Got HTML error page instead")
                        return {"success": False, "error": "Not a PDF", "time": elapsed}
            else:
                print(f"   ❌ No file created")
                return {"success": False, "error": "No file", "time": elapsed}
        else:
            print(f"   ❌ Curl failed with code {result.returncode}")
            return {"success": False, "error": f"Curl error {result.returncode}", "time": elapsed}
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return {"success": False, "error": str(e), "time": time.time() - start_time}

def method2_curl_with_referer(pdf_url, manufacturer_uri, model_code):
    """Method 2: Curl with referer header"""
    print(f"\n🔍 Method 2: Curl with referer header")
    
    if pdf_url.startswith('/'):
        full_url = f"https://www.partstown.com{pdf_url}"
    else:
        full_url = pdf_url
    
    referer = f"https://www.partstown.com/{manufacturer_uri}/{model_code}/parts"
    print(f"   URL: {full_url}")
    print(f"   Referer: {referer}")
    
    pdf_hash = hashlib.md5(pdf_url.encode()).hexdigest()
    output_file = f"test_pdfs/{pdf_hash}_referer.pdf"
    
    curl_cmd = [
        'curl',
        '-s',
        '-L',
        '-H', 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        '-H', f'Referer: {referer}',
        '-H', 'Accept: application/pdf,application/octet-stream,*/*',
        '--compressed',
        '--max-time', '30',
        '-o', output_file,
        '-w', '%{http_code}|%{size_download}|%{time_total}',
        full_url
    ]
    
    start_time = time.time()
    
    try:
        result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=35)
        elapsed = time.time() - start_time
        
        if result.returncode == 0:
            stats = result.stdout.strip().split('|')
            http_code = stats[0] if len(stats) > 0 else '?'
            
            print(f"   Status: {http_code}")
            print(f"   Time: {elapsed:.2f}s")
            
            if os.path.exists(output_file):
                file_size = os.path.getsize(output_file)
                print(f"   File size: {file_size:,} bytes")
                
                with open(output_file, 'rb') as f:
                    header = f.read(4)
                    if header == b'%PDF':
                        print(f"   ✅ Valid PDF downloaded!")
                        return {"success": True, "size": file_size, "time": elapsed, "method": "curl-referer"}
                    else:
                        print(f"   ❌ Not a PDF")
                        return {"success": False, "error": "Not a PDF", "time": elapsed}
            else:
                return {"success": False, "error": "No file", "time": elapsed}
        else:
            print(f"   ❌ Curl failed")
            return {"success": False, "error": f"Curl error", "time": elapsed}
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return {"success": False, "error": str(e), "time": time.time() - start_time}

def method3_curl_with_cookies(pdf_url, manufacturer_uri, model_code):
    """Method 3: First get page with curl to get cookies, then download PDF"""
    print(f"\n🔍 Method 3: Curl with cookie jar")
    
    if pdf_url.startswith('/'):
        full_url = f"https://www.partstown.com{pdf_url}"
    else:
        full_url = pdf_url
    
    model_page = f"https://www.partstown.com/{manufacturer_uri}/{model_code}/parts"
    cookie_file = "test_pdfs/cookies.txt"
    
    print(f"   Step 1: Get cookies from {model_page}")
    
    # First request to get cookies
    curl_cmd1 = [
        'curl',
        '-s',
        '-L',
        '-c', cookie_file,  # Save cookies
        '-H', 'User-Agent: Mozilla/5.0',
        '--max-time', '10',
        '-o', '/dev/null',
        model_page
    ]
    
    start_time = time.time()
    
    try:
        subprocess.run(curl_cmd1, timeout=15)
        
        print(f"   Step 2: Download PDF with cookies")
        
        pdf_hash = hashlib.md5(pdf_url.encode()).hexdigest()
        output_file = f"test_pdfs/{pdf_hash}_cookies.pdf"
        
        # Second request with cookies
        curl_cmd2 = [
            'curl',
            '-s',
            '-L',
            '-b', cookie_file,  # Use cookies
            '-c', cookie_file,  # Update cookies
            '-H', 'User-Agent: Mozilla/5.0',
            '-H', f'Referer: {model_page}',
            '--compressed',
            '--max-time', '30',
            '-o', output_file,
            '-w', '%{http_code}|%{size_download}',
            full_url
        ]
        
        result = subprocess.run(curl_cmd2, capture_output=True, text=True, timeout=35)
        elapsed = time.time() - start_time
        
        if result.returncode == 0:
            stats = result.stdout.strip().split('|')
            http_code = stats[0] if len(stats) > 0 else '?'
            
            print(f"   Status: {http_code}")
            print(f"   Time: {elapsed:.2f}s")
            
            if os.path.exists(output_file):
                file_size = os.path.getsize(output_file)
                print(f"   File size: {file_size:,} bytes")
                
                with open(output_file, 'rb') as f:
                    header = f.read(4)
                    if header == b'%PDF':
                        print(f"   ✅ Valid PDF downloaded!")
                        return {"success": True, "size": file_size, "time": elapsed, "method": "curl-cookies"}
                    else:
                        print(f"   ❌ Not a PDF")
                        return {"success": False, "error": "Not a PDF", "time": elapsed}
            else:
                return {"success": False, "error": "No file", "time": elapsed}
        else:
            return {"success": False, "error": "Curl error", "time": elapsed}
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return {"success": False, "error": str(e), "time": time.time() - start_time}
    finally:
        # Clean up cookie file
        if os.path.exists(cookie_file):
            os.remove(cookie_file)

def method4_python_requests(pdf_url):
    """Method 4: Python requests (for comparison)"""
    print(f"\n🔍 Method 4: Python requests")
    
    if pdf_url.startswith('/'):
        full_url = f"https://www.partstown.com{pdf_url}"
    else:
        full_url = pdf_url
    
    print(f"   URL: {full_url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept': 'application/pdf,*/*',
    }
    
    start_time = time.time()
    
    try:
        response = requests.get(full_url, headers=headers, timeout=30, allow_redirects=True)
        elapsed = time.time() - start_time
        
        print(f"   Status: {response.status_code}")
        print(f"   Time: {elapsed:.2f}s")
        
        if response.status_code == 200:
            print(f"   Size: {len(response.content):,} bytes")
            
            # Check if it's a PDF
            if response.content[:4] == b'%PDF':
                print(f"   ✅ Valid PDF!")
                
                pdf_hash = hashlib.md5(pdf_url.encode()).hexdigest()
                output_file = f"test_pdfs/{pdf_hash}_requests.pdf"
                
                with open(output_file, 'wb') as f:
                    f.write(response.content)
                
                return {"success": True, "size": len(response.content), "time": elapsed, "method": "requests"}
            else:
                print(f"   ❌ Not a PDF. Got: {response.content[:100]}")
                return {"success": False, "error": "Not a PDF", "time": elapsed}
        else:
            print(f"   ❌ HTTP {response.status_code}")
            return {"success": False, "error": f"HTTP {response.status_code}", "time": elapsed}
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return {"success": False, "error": str(e), "time": time.time() - start_time}

def run_all_tests():
    """Test all methods on multiple PDFs"""
    print("="*60)
    print("PDF DOWNLOAD METHOD TESTING")
    print("="*60)
    
    # Clean up test directory
    os.makedirs("test_pdfs", exist_ok=True)
    
    results = []
    
    for pdf_info in TEST_PDFS:
        print(f"\n{'='*60}")
        print(f"Testing: {pdf_info['name']}")
        print(f"URL: {pdf_info['url']}")
        print(f"{'='*60}")
        
        test_result = {
            "pdf": pdf_info['name'],
            "methods": {}
        }
        
        # Test each method
        test_result["methods"]["curl_direct"] = method1_direct_curl(pdf_info['url'])
        test_result["methods"]["curl_referer"] = method2_curl_with_referer(
            pdf_info['url'], 
            pdf_info['manufacturer'], 
            pdf_info['model']
        )
        test_result["methods"]["curl_cookies"] = method3_curl_with_cookies(
            pdf_info['url'],
            pdf_info['manufacturer'],
            pdf_info['model']
        )
        test_result["methods"]["requests"] = method4_python_requests(pdf_info['url'])
        
        results.append(test_result)
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY OF RESULTS")
    print("="*60)
    
    for result in results:
        print(f"\n{result['pdf']}:")
        for method_name, method_result in result['methods'].items():
            status = "✅" if method_result.get("success") else "❌"
            time_str = f"{method_result.get('time', 0):.2f}s"
            size = f"{method_result.get('size', 0):,}" if method_result.get('size') else "0"
            print(f"  {status} {method_name:15} | Time: {time_str:6} | Size: {size:>10} bytes")
    
    # Overall stats
    print("\n" + "="*60)
    print("OVERALL STATISTICS")
    print("="*60)
    
    method_stats = {}
    for result in results:
        for method_name, method_result in result['methods'].items():
            if method_name not in method_stats:
                method_stats[method_name] = {"success": 0, "total": 0, "times": []}
            
            method_stats[method_name]["total"] += 1
            if method_result.get("success"):
                method_stats[method_name]["success"] += 1
                method_stats[method_name]["times"].append(method_result.get("time", 0))
    
    for method_name, stats in method_stats.items():
        success_rate = (stats["success"] / stats["total"]) * 100
        avg_time = sum(stats["times"]) / len(stats["times"]) if stats["times"] else 0
        print(f"{method_name:15} - Success: {success_rate:5.1f}% | Avg time: {avg_time:.2f}s")
    
    # Clean up
    print("\nCleaning up test files...")
    import shutil
    if os.path.exists("test_pdfs"):
        shutil.rmtree("test_pdfs")

if __name__ == "__main__":
    run_all_tests()