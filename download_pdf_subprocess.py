#!/usr/bin/env python3
"""
Download PDF files using browser automation in subprocess
Navigates through the page to download PDFs with proper authentication
"""

import subprocess
import json
import sys
import base64

def download_pdf_via_page(manufacturer_uri, model_code, manual_url):
    """Download PDF by navigating through the model page with authentication"""
    
    # Ensure manual URL is complete
    if manual_url.startswith('/'):
        manual_url = f"https://www.partstown.com{manual_url}"
    
    # Python code to run in subprocess
    script = f"""
import asyncio
from playwright.async_api import async_playwright
import json
import base64
import sys

async def download():
    # URL of the model page
    model_page_url = "https://www.partstown.com/{manufacturer_uri}/{model_code}/parts"
    manual_url = "{manual_url}"
    
    playwright = None
    browser = None
    
    try:
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            accept_downloads=True
        )
        page = await context.new_page()
        
        # First navigate to the model page to establish session
        await page.goto(model_page_url, wait_until='networkidle', timeout=60000)
        await page.wait_for_timeout(1000)
        
        # Now download the manual with authentication in place
        async with page.expect_download() as download_info:
            # Navigate to the manual URL which should trigger download
            await page.goto(manual_url, timeout=60000)
            download = await download_info.value
            
            # Read the downloaded file
            path = await download.path()
            with open(path, 'rb') as f:
                pdf_content = f.read()
            
            # Output as base64
            encoded = base64.b64encode(pdf_content).decode('utf-8')
            print(json.dumps({{"success": True, "data": encoded}}))
            return
            
    except Exception as e:
        # Try alternative approach - fetch via page.request
        try:
            # Navigate to model page first for auth
            await page.goto(model_page_url, wait_until='networkidle', timeout=60000)
            await page.wait_for_timeout(1000)
            
            # Make authenticated request for the PDF
            response = await page.request.get(manual_url)
            
            if response.ok:
                pdf_content = await response.body()
                encoded = base64.b64encode(pdf_content).decode('utf-8')
                print(json.dumps({{"success": True, "data": encoded}}))
            else:
                print(json.dumps({{"success": False, "error": f"Status {{response.status}}"}}))
                
        except Exception as e2:
            print(json.dumps({{"success": False, "error": str(e2)}}))
    
    finally:
        if browser:
            await browser.close()
        if playwright:
            await playwright.stop()

asyncio.run(download())
"""
    
    try:
        # Run the script in a subprocess
        result = subprocess.run(
            [sys.executable, '-c', script],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.stdout:
            try:
                response = json.loads(result.stdout.strip())
                if response.get('success'):
                    # Decode the base64 PDF content
                    pdf_content = base64.b64decode(response['data'])
                    return {'success': True, 'content': pdf_content}
                else:
                    return {'success': False, 'error': response.get('error', 'Unknown error')}
            except json.JSONDecodeError:
                return {'success': False, 'error': f'Invalid JSON: {result.stdout}'}
        else:
            error = result.stderr if result.stderr else 'No output from subprocess'
            return {'success': False, 'error': error}
            
    except subprocess.TimeoutExpired:
        return {'success': False, 'error': 'Download timeout'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

if __name__ == "__main__":
    # Test with Henny Penny 500 SPM manual
    result = download_pdf_via_page(
        "henny-penny", 
        "500", 
        "/modelManual/HEN-PF500_spm.pdf?v=1655476514087"
    )
    
    if result['success']:
        print(f"✅ Downloaded {len(result['content'])} bytes")
        with open('test_manual.pdf', 'wb') as f:
            f.write(result['content'])
        print("💾 Saved to test_manual.pdf")
    else:
        print(f"❌ Download failed: {result['error']}")