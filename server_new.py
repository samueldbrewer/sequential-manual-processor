#!/usr/bin/env python3
"""
Sequential Manual Processor API Server - Updated with Working Subprocess Approach
Provides REST endpoints for the Sequential AI Manual Processing web application
"""

from flask import Flask, jsonify, request, session
from flask_cors import CORS
import sys
import os
import asyncio
import time
from threading import Thread
from queue import Queue
import requests
import PyPDF2
import tempfile
from io import BytesIO
import base64
import hashlib
from datetime import datetime, timedelta
import shutil
import uuid
import secrets
import subprocess
import json
import threading

app = Flask(__name__, static_folder='public', static_url_path='/public')
app.secret_key = secrets.token_hex(32)  # Generate a secure secret key
CORS(app, origins=['http://localhost:3000', 'http://localhost:3001'], supports_credentials=True)

# Global cache for scraped data
scraper_cache = {
    'manufacturers': None,
    'models': {},
    'manuals': {},
    'timestamp': 0,
    'manufacturers_timestamp': None
}

CACHE_DURATION = 300  # 5 minutes cache
TEMP_PDF_DIR = os.path.join(os.path.dirname(__file__), 'public', 'temp-pdfs')
PDF_CLEANUP_HOURS = 24  # Clean up PDFs older than 24 hours

# Session-based PDF tracking
session_pdfs = {}  # Maps session_id to list of PDF filenames

# Request serialization
request_lock = threading.Lock()
request_cache_lock = threading.Lock()
request_cache = {}

def cleanup_old_pdfs():
    """Remove PDF files older than PDF_CLEANUP_HOURS"""
    try:
        if not os.path.exists(TEMP_PDF_DIR):
            os.makedirs(TEMP_PDF_DIR)
            return
            
        now = datetime.now()
        for filename in os.listdir(TEMP_PDF_DIR):
            filepath = os.path.join(TEMP_PDF_DIR, filename)
            if os.path.isfile(filepath):
                file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                if now - file_time > timedelta(hours=PDF_CLEANUP_HOURS):
                    os.remove(filepath)
                    print(f"Cleaned up old PDF: {filename}")
    except Exception as e:
        print(f"Error cleaning up PDFs: {e}")

def get_manufacturers_sync():
    """Get manufacturers using subprocess to avoid event loop issues"""
    global scraper_cache
    
    # Check cache
    if scraper_cache['manufacturers'] and scraper_cache['manufacturers_timestamp']:
        if (datetime.now() - scraper_cache['manufacturers_timestamp']).seconds < CACHE_DURATION:
            return scraper_cache['manufacturers']
    
    # Run the scraper in a subprocess
    script = """
import asyncio
import sys
import os
sys.path.append('../API Scraper V2')
from interactive_scraper import PartsTownExplorer

async def main():
    explorer = PartsTownExplorer()
    manufacturers = await explorer.get_manufacturers()
    return manufacturers

result = asyncio.run(main())
import json
print(json.dumps(result))
"""
    
    try:
        result = subprocess.run(
            ['python3', '-c', script],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=os.path.dirname(__file__)
        )
        
        if result.returncode == 0:
            # Extract JSON from output (might have debug messages)
            output = result.stdout
            # Find the JSON array in the output
            try:
                # Look for JSON array starting with [
                start = output.rfind('[')
                if start != -1:
                    json_str = output[start:]
                    manufacturers = json.loads(json_str)
                    scraper_cache['manufacturers'] = manufacturers
                    scraper_cache['manufacturers_timestamp'] = datetime.now()
                    return manufacturers
            except:
                pass
            return []
        else:
            print(f"Error getting manufacturers: {result.stderr}")
            return []
    except Exception as e:
        print(f"Exception getting manufacturers: {e}")
        return []

def get_models_sync(manufacturer_uri, manufacturer_code):
    """Get models for a manufacturer using subprocess"""
    
    # Check cache
    cache_key = manufacturer_code
    if cache_key in scraper_cache['models']:
        cached_time, cached_models = scraper_cache['models'][cache_key]
        if (datetime.now() - cached_time).seconds < CACHE_DURATION:
            print(f"DEBUG: Returning cached models for {manufacturer_code}")
            return cached_models
    
    print(f"DEBUG: Cache miss for {manufacturer_code}, fetching fresh data")
    
    # Run the scraper in a subprocess
    script = f"""
import asyncio
import sys
import os
sys.path.append('../API Scraper V2')
from interactive_scraper import PartsTownExplorer

async def main():
    explorer = PartsTownExplorer()
    models = await explorer.get_models_for_manufacturer('{manufacturer_uri}', '{manufacturer_code}')
    return models

result = asyncio.run(main())
import json
print(json.dumps(result))
"""
    
    try:
        result = subprocess.run(
            ['python3', '-c', script],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=os.path.dirname(__file__)
        )
        
        if result.returncode == 0:
            # Extract JSON from output (might have debug messages)
            output = result.stdout
            print(f"DEBUG: Raw output length: {len(output)}")
            print(f"DEBUG: Raw output last 500 chars: {output[-500:]}")
            # Find the JSON array in the output
            try:
                # Look for JSON array starting with [
                start = output.rfind('[')
                print(f"DEBUG: Found '[' at position: {start}")
                if start != -1:
                    json_str = output[start:]
                    print(f"DEBUG: JSON string first 200 chars: {json_str[:200]}")
                    models = json.loads(json_str)
                    print(f"DEBUG: Parsed {len(models)} models")
                    # Cache the result
                    scraper_cache['models'][cache_key] = (datetime.now(), models)
                    return models
            except Exception as e:
                print(f"DEBUG: Error parsing JSON: {e}")
                import traceback
                traceback.print_exc()
                pass
            return []
        else:
            print(f"Error getting models: {result.stderr}")
            return []
    except Exception as e:
        print(f"Exception getting models: {e}")
        return []

def download_pdf_sync(pdf_url):
    """Download a PDF using subprocess and Playwright"""
    
    # Generate filename from URL hash
    url_hash = hashlib.md5(pdf_url.encode()).hexdigest()[:10]
    filename = pdf_url.split('/')[-1].split('?')[0]
    local_filename = f"{url_hash}_{filename}"
    local_path = os.path.join(TEMP_PDF_DIR, local_filename)
    
    # Check if already downloaded
    if os.path.exists(local_path):
        with open(local_path, 'rb') as f:
            return f.read()
    
    # Download using Playwright in subprocess
    script = f"""
import asyncio
from playwright.async_api import async_playwright
import base64
import tempfile
import os

async def download_pdf(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            viewport={{'width': 1920, 'height': 1080}}
        )
        
        # Set extra headers for PartsTown
        await context.set_extra_http_headers({{
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/pdf,*/*"
        }})
        
        page = await context.new_page()
        
        # First navigate to PartsTown to establish session
        await page.goto("https://www.partstown.com", wait_until='domcontentloaded')
        await page.wait_for_timeout(1000)
        
        pdf_content = None
        
        # Try using page.request.get() first
        try:
            response = await page.request.get(url)
            if response.ok:
                pdf_content = await response.body()
        except:
            pass
        
        # Fallback: Try download with expect_download
        if not pdf_content:
            try:
                download_page = await context.new_page()
                
                async with download_page.expect_download(timeout=30000) as download_info:
                    await download_page.goto(url)
                
                download = await download_info.value
                temp_path = os.path.join(tempfile.gettempdir(), "temp.pdf")
                await download.save_as(temp_path)
                
                with open(temp_path, 'rb') as f:
                    pdf_content = f.read()
                
                os.unlink(temp_path)
                await download_page.close()
            except:
                pass
        
        await browser.close()
        
        if pdf_content:
            # Return base64 encoded
            return base64.b64encode(pdf_content).decode('utf-8')
        else:
            return ""

result = asyncio.run(download_pdf('{pdf_url}'))
print(result)
"""
    
    try:
        result = subprocess.run(
            ['python3', '-c', script],
            capture_output=True,
            text=True,
            timeout=45,
            cwd=os.path.dirname(__file__)
        )
        
        if result.returncode == 0 and result.stdout.strip():
            # Decode base64 and save
            pdf_data = base64.b64decode(result.stdout.strip())
            
            # Save to file
            with open(local_path, 'wb') as f:
                f.write(pdf_data)
            
            return pdf_data
        else:
            print(f"Error downloading PDF: {result.stderr}")
            return None
    except Exception as e:
        print(f"Exception downloading PDF: {e}")
        return None

@app.route('/')
def index():
    """API documentation homepage"""
    return jsonify({
        "name": "Sequential Manual Processor API",
        "version": "2.0",
        "endpoints": {
            "health": "/health",
            "manufacturers": "/api/manufacturers",
            "models": "/api/manufacturers/<id>/models", 
            "manuals": "/api/manufacturers/<id>/models/<model_id>/manuals",
            "manual_metadata": "/api/manual-metadata?url=<pdf_url>",
            "clear_session_pdfs": "/api/clear-session-pdfs"
        }
    })

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})

@app.route('/api/manufacturers')
def get_manufacturers():
    """Get all manufacturers"""
    print("\n📋 Fetching manufacturers...")
    manufacturers = get_manufacturers_sync()
    return jsonify(manufacturers)

@app.route('/api/manufacturers/<manufacturer_id>/models')
def get_models(manufacturer_id):
    """Get models for a specific manufacturer"""
    print(f"\n🔧 Fetching models for {manufacturer_id}...")
    
    # Check if we have a recent cached response for this exact request
    cache_key = f"models_{manufacturer_id}"
    with request_cache_lock:
        if cache_key in request_cache:
            cached_time, cached_response = request_cache[cache_key]
            if time.time() - cached_time < 5:  # 5 second cache to handle React rerenders
                print(f"📦 Returning cached response for {manufacturer_id}")
                return cached_response
    
    # Get manufacturer info
    manufacturers = get_manufacturers_sync()
    manufacturer = next((m for m in manufacturers if m['code'] == manufacturer_id), None)
    
    if not manufacturer:
        return jsonify({"error": f"Manufacturer '{manufacturer_id}' not found"}), 404
    
    # Get models using the working subprocess approach
    models = get_models_sync(manufacturer['uri'], manufacturer['code'])
    
    print(f"📊 Final model count for {manufacturer['name']}: {len(models)}")
    
    # Cache the response
    response = jsonify({
        "manufacturer": manufacturer['name'],
        "models": models
    })
    
    with request_cache_lock:
        request_cache[cache_key] = (time.time(), response)
    
    return response

@app.route('/api/manufacturers/<manufacturer_id>/models/<model_id>/manuals')
def get_manuals(manufacturer_id, model_id):
    """Get manuals for a specific model"""
    # For now, return empty array - this can be implemented later if needed
    return jsonify([])

@app.route('/api/manual-metadata')
def get_manual_metadata():
    """Download PDF to local temp folder and analyze it"""
    manual_url = request.args.get('url')
    
    if not manual_url:
        return jsonify({"error": "Manual URL is required"}), 400
    
    # Initialize session if not exists
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
        session.permanent = False
    
    session_id = session['session_id']
    
    # Clean up old PDFs
    cleanup_old_pdfs()
    
    try:
        # Ensure the URL has the full domain
        if not manual_url.startswith('http'):
            manual_url = f'https://www.partstown.com{manual_url}'
        
        # Extract filename from URL for display
        filename = manual_url.split('/')[-1].split('?')[0]
        
        # Generate a unique filename based on URL hash
        url_hash = hashlib.md5(manual_url.encode()).hexdigest()[:8]
        local_filename = f"{url_hash}_{filename}"
        local_path = os.path.join(TEMP_PDF_DIR, local_filename)
        
        # Download the PDF
        pdf_content = download_pdf_sync(manual_url)
        
        if not pdf_content:
            return jsonify({"error": "Failed to download PDF"}), 500
        
        print(f"📥 Downloaded {len(pdf_content)} bytes")
        
        # Track this PDF for the session
        if session_id not in session_pdfs:
            session_pdfs[session_id] = []
        if local_filename not in session_pdfs[session_id]:
            session_pdfs[session_id].append(local_filename)
            print(f"📝 Tracking PDF for session {session_id[:8]}: {local_filename}")
        
        # Generate preview
        preview_generated = False
        preview_path = local_path.replace('.pdf', '_preview.jpg')
        relative_preview_path = f"/public/temp-pdfs/{os.path.basename(preview_path)}"
        
        # Try to generate preview with PyMuPDF
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(local_path)
            page = doc[0]  # First page
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better quality
            pix.save(preview_path)
            doc.close()
            preview_generated = True
            print(f"✅ Generated preview using PyMuPDF")
        except Exception as e:
            print(f"PyMuPDF preview failed: {e}")
            
            # Fallback to pdf2image
            try:
                from pdf2image import convert_from_path
                images = convert_from_path(local_path, first_page=1, last_page=1, dpi=150)
                if images:
                    images[0].save(preview_path, 'JPEG')
                    preview_generated = True
                    print(f"✅ Generated preview using pdf2image")
            except Exception as e2:
                print(f"pdf2image preview failed: {e2}")
        
        # Get PDF metadata
        try:
            pdf_reader = PyPDF2.PdfReader(BytesIO(pdf_content))
            num_pages = len(pdf_reader.pages)
        except:
            num_pages = 1
        
        return jsonify({
            "status": "success",
            "metadata": {
                "title": filename,
                "pages": num_pages,
                "size": len(pdf_content)
            },
            "preview_url": relative_preview_path if preview_generated else None,
            "pdf_url": f"/public/temp-pdfs/{local_filename}",
            "filename": filename
        })
        
    except Exception as e:
        print(f"❌ Error processing manual: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to process manual: {str(e)}"}), 500

@app.route('/api/clear-session-pdfs', methods=['POST'])
def clear_session_pdfs():
    """Clear PDFs for the current session only"""
    session_id = session.get('session_id')
    
    if not session_id or session_id not in session_pdfs:
        return jsonify({"status": "ok", "message": "No PDFs to clear"})
    
    # Get list of PDFs for this session
    pdfs_to_remove = session_pdfs.get(session_id, [])
    removed_count = 0
    
    for filename in pdfs_to_remove:
        try:
            # Remove PDF file
            pdf_path = os.path.join(TEMP_PDF_DIR, filename)
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
                removed_count += 1
            
            # Remove preview if exists
            preview_path = pdf_path.replace('.pdf', '_preview.jpg')
            if os.path.exists(preview_path):
                os.remove(preview_path)
                
        except Exception as e:
            print(f"Error removing PDF {filename}: {e}")
    
    # Clear the session's PDF list
    del session_pdfs[session_id]
    
    return jsonify({
        "status": "ok",
        "message": f"Cleared {removed_count} PDFs for session"
    })

if __name__ == '__main__':
    print("\n🚀 Starting Sequential Manual Processor API Server...")
    print("📖 API Documentation: http://localhost:8888/")
    print("🔍 Health Check: http://localhost:8888/health")
    print("🏭 Manufacturers: http://localhost:8888/api/manufacturers")
    print()
    print("⚠️  Make sure the PartsTown scraper is available in '../API Scraper V2/'")
    
    # Ensure temp directories exist
    os.makedirs(TEMP_PDF_DIR, exist_ok=True)
    
    # Clean up old PDFs on startup
    cleanup_old_pdfs()
    
    app.run(port=8888, debug=False)