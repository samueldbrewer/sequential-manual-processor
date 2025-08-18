#!/usr/bin/env python3
"""
Fast PDF download using curl - replaces slow Playwright approach
Downloads PDFs directly with curl which bypasses CloudFlare
"""

import subprocess
import os
import time
import hashlib
import base64

def download_pdf_via_curl(manual_url, manufacturer_uri=None, model_code=None):
    """
    Download PDF using curl - much faster than Playwright
    
    Args:
        manual_url: The PDF URL (can be relative or absolute)
        manufacturer_uri: Optional manufacturer URI for referer
        model_code: Optional model code for referer
    
    Returns:
        dict: {success: bool, content: bytes, error: str, time: float}
    """
    
    # Ensure full URL
    if manual_url.startswith('/'):
        full_url = f"https://www.partstown.com{manual_url}"
    else:
        full_url = manual_url
    
    # Create temp file for download
    pdf_hash = hashlib.md5(manual_url.encode()).hexdigest()
    temp_file = f"/tmp/{pdf_hash}_download.pdf"
    
    # Build curl command
    curl_cmd = [
        'curl',
        '-s',  # Silent
        '-L',  # Follow redirects
        '-H', 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        '-H', 'Accept: application/pdf,application/octet-stream,*/*',
        '-H', 'Accept-Language: en-US,en;q=0.9',
        '--compressed',
        '--max-time', '30',
        '-o', temp_file,  # Output to temp file
        '-w', '%{http_code}|%{size_download}|%{time_total}',  # Write stats
    ]
    
    # Add referer if we have manufacturer/model info
    if manufacturer_uri and model_code:
        referer = f"https://www.partstown.com/{manufacturer_uri}/{model_code}/parts"
        curl_cmd.extend(['-H', f'Referer: {referer}'])
        print(f"📥 Downloading PDF with referer: {referer}")
    else:
        print(f"📥 Downloading PDF directly")
    
    curl_cmd.append(full_url)
    
    start_time = time.time()
    
    try:
        # Execute curl
        result = subprocess.run(
            curl_cmd,
            capture_output=True,
            text=True,
            timeout=35
        )
        
        elapsed = time.time() - start_time
        
        if result.returncode == 0:
            # Parse curl stats
            stats = result.stdout.strip().split('|')
            http_code = stats[0] if len(stats) > 0 else '?'
            size = int(stats[1]) if len(stats) > 1 else 0
            
            print(f"   Status: {http_code} | Size: {size:,} bytes | Time: {elapsed:.2f}s")
            
            # Read the downloaded file
            if os.path.exists(temp_file):
                with open(temp_file, 'rb') as f:
                    pdf_content = f.read()
                
                # Verify it's a PDF
                if pdf_content[:4] == b'%PDF':
                    print(f"✅ Successfully downloaded {len(pdf_content):,} bytes in {elapsed:.2f}s")
                    
                    # Clean up temp file
                    os.remove(temp_file)
                    
                    return {
                        'success': True,
                        'content': pdf_content,
                        'time': elapsed
                    }
                else:
                    print(f"❌ Downloaded file is not a PDF")
                    os.remove(temp_file)
                    return {
                        'success': False,
                        'error': 'Downloaded file is not a PDF',
                        'time': elapsed
                    }
            else:
                return {
                    'success': False,
                    'error': 'No file downloaded',
                    'time': elapsed
                }
        else:
            print(f"❌ Curl failed with return code {result.returncode}")
            if result.stderr:
                print(f"   Error: {result.stderr}")
            
            return {
                'success': False,
                'error': f'Curl failed with code {result.returncode}',
                'time': elapsed
            }
            
    except subprocess.TimeoutExpired:
        print(f"❌ Download timeout after 35 seconds")
        # Clean up temp file if it exists
        if os.path.exists(temp_file):
            os.remove(temp_file)
        
        return {
            'success': False,
            'error': 'Download timeout',
            'time': 35.0
        }
        
    except Exception as e:
        print(f"❌ Error downloading PDF: {e}")
        # Clean up temp file if it exists
        if os.path.exists(temp_file):
            os.remove(temp_file)
        
        return {
            'success': False,
            'error': str(e),
            'time': time.time() - start_time
        }

def download_pdf_as_base64(manual_url, manufacturer_uri=None, model_code=None):
    """
    Download PDF and return as base64 (for subprocess compatibility)
    """
    result = download_pdf_via_curl(manual_url, manufacturer_uri, model_code)
    
    if result['success']:
        # Encode to base64 for safe transfer
        encoded = base64.b64encode(result['content']).decode('utf-8')
        return {
            'success': True,
            'data': encoded,
            'time': result['time']
        }
    else:
        return result

if __name__ == "__main__":
    # Test downloads
    test_cases = [
        {
            "url": "/modelManual/HEN-PF500_spm.pdf?v=1655476514087",
            "manufacturer": "henny-penny",
            "model": "500"
        },
        {
            "url": "/modelManual/GLO-2XXX_pm.pdf?v=1655476541971",
            "manufacturer": "globe",
            "model": "2500"
        }
    ]
    
    print("Testing PDF downloads with curl:\n")
    
    for test in test_cases:
        print(f"Testing {test['manufacturer']}/{test['model']}:")
        result = download_pdf_via_curl(
            test['url'],
            test['manufacturer'],
            test['model']
        )
        
        if result['success']:
            print(f"  ✅ Success! Downloaded {len(result['content']):,} bytes")
            print(f"  Time: {result['time']:.2f}s")
            
            # Save for verification
            filename = f"test_{test['manufacturer']}_{test['model']}.pdf"
            with open(filename, 'wb') as f:
                f.write(result['content'])
            print(f"  Saved as {filename}")
        else:
            print(f"  ❌ Failed: {result['error']}")
        
        print()