#!/usr/bin/env python3
"""
Sequential Manual Processor API Server
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
import concurrent.futures

# Add parent directory to path to import the scraper
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'API Scraper V2'))
from interactive_scraper import PartsTownExplorer

app = Flask(__name__, static_folder='public', static_url_path='/public')
app.secret_key = secrets.token_hex(32)  # Generate a secure secret key
CORS(app, origins=['http://localhost:3000', 'http://localhost:3001'], supports_credentials=True)

# Global scraper instance
scraper = None
scraper_cache = {
    'manufacturers': None,
    'models': {},
    'manuals': {},
    'timestamp': 0
}

CACHE_DURATION = 300  # 5 minutes cache
TEMP_PDF_DIR = os.path.join(os.path.dirname(__file__), 'public', 'temp-pdfs')
PDF_CLEANUP_HOURS = 24  # Clean up PDFs older than 24 hours

# Session-based PDF tracking
session_pdfs = {}  # Maps session_id to list of PDF filenames

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

import threading
import uuid as request_uuid
from browser_pool import browser_pool

class AsyncScraper:
    """Simple wrapper for the async scraper with browser pool"""
    
    def __init__(self):
        self.explorer = PartsTownExplorer()
        self.ready = True
        self.lock = threading.Lock()
        self.active_requests = {}
        self.browser_pool = browser_pool
        
    async def get_models_with_pool(self, manufacturer_uri, manufacturer_code):
        """Get models using browser pool"""
        browser_id = None
        page = None
        
        try:
            # Get browser from pool
            browser_id, browser, context, page = await self.browser_pool.get_browser()
            print(f"🔧 Using browser {browser_id} for {manufacturer_uri}")
            
            # Navigate to the models page
            models_url = f"https://www.partstown.com/{manufacturer_uri}/parts?v={int(time.time()*1000)}&narrow=#id=mdptabmodels"
            print(f"🌐 Navigating to: {models_url}")
            
            response = await page.goto(models_url, timeout=30000, wait_until='domcontentloaded')
            print(f"📄 Navigation completed with status: {response.status if response else 'No response'}")
            
            # Wait for page to load
            await asyncio.sleep(3)
            
            # Try to extract models from DOM
            print("Attempting to extract models from page DOM...")
            
            if page.is_closed():
                print("❌ Page is closed")
                return []
            
            models_data = await page.evaluate("""
                () => {
                    const models = [];
                    const selectors = [
                        '.model-item', '.model-card', '.product-tile', 
                        '[data-model]', '.model', '.equipment-model',
                        'a[href*="/parts"]', '.model-link'
                    ];
                    
                    for (const selector of selectors) {
                        const elements = document.querySelectorAll(selector);
                        elements.forEach(el => {
                            const text = el.textContent?.trim();
                            const href = el.getAttribute('href');
                            
                            if (text && text.length > 0 && text.length < 100) {
                                models.push({
                                    name: text,
                                    url: href || '',
                                    element_type: selector
                                });
                            }
                        });
                        
                        if (models.length > 0) break;
                    }
                    
                    // Remove duplicates
                    const unique = [];
                    const seen = new Set();
                    
                    for (const model of models) {
                        const key = model.name.toLowerCase().trim();
                        if (!seen.has(key) && key.length > 1) {
                            seen.add(key);
                            unique.push(model);
                        }
                    }
                    
                    return unique.slice(0, 50);
                }
            """)
            
            print(f"✅ Extracted {len(models_data) if models_data else 0} models")
            return models_data or []
            
        except Exception as e:
            print(f"❌ Error fetching models: {e}")
            return []
        finally:
            # Release browser back to pool
            if browser_id:
                await self.browser_pool.release_browser(browser_id, page)
        
    def run_async(self, coro):
        """Run an async function with proper event loop management"""
        request_id = str(request_uuid.uuid4())[:8]
        
        # Serialize ALL requests to prevent browser conflicts
        with self.lock:
            try:
                print(f"🔐 Starting request {request_id}")
                self.active_requests[request_id] = True
                
                # Add a delay between requests to prevent browser conflicts
                if len(self.active_requests) > 1:
                    print(f"⏳ Waiting for other requests to complete...")
                    time.sleep(2.0)
                
                # Create new event loop but DON'T close it immediately
                # This keeps Playwright objects alive
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    # Run the coroutine
                    result = loop.run_until_complete(coro)
                    print(f"✅ Request {request_id} completed successfully")
                    return result
                finally:
                    # Close the loop AFTER we're done with the result
                    # Give Playwright time to clean up properly
                    time.sleep(0.1)
                    loop.close()
                    
            except asyncio.TimeoutError:
                print(f"⚠️ Request {request_id} timed out")
                return None
            except Exception as e:
                print(f"⚠️ Request {request_id} error: {e}")
                import traceback
                traceback.print_exc()
                return None
            finally:
                if request_id in self.active_requests:
                    del self.active_requests[request_id]
                print(f"🔓 Released request {request_id}")
                # Add a delay after releasing to ensure cleanup
                time.sleep(0.5)

# Initialize scraper as singleton
scraper = None

def get_scraper():
    """Get or initialize the scraper singleton"""
    global scraper
    
    if scraper:
        return scraper
    
    # Initialize if needed
    if not scraper:
        print("🚀 Initializing scraper...")
        scraper = AsyncScraper()
        print("✅ Scraper ready!")
    
    return scraper

def init_scraper():
    """Initialize the scraper (called when first needed)"""
    get_scraper()

@app.route('/')
def index():
    """API documentation homepage"""
    return jsonify({
        "name": "Sequential Manual Processor API",
        "version": "1.0.0",
        "description": "REST API for Sequential AI Manual Processing",
        "endpoints": {
            "manufacturers": "/api/manufacturers",
            "models": "/api/manufacturers/<manufacturer_id>/models",
            "manuals": "/api/manufacturers/<manufacturer_id>/models/<model_id>/manuals",
            "process_manual": "/api/process-manual",
            "health": "/health"
        }
    })

@app.route('/health')
def health():
    """Health check endpoint"""
    # Initialize session if not exists
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
        session.permanent = False
    
    scraper_instance = get_scraper() if not scraper else scraper
    return jsonify({
        "status": "healthy" if scraper_instance and scraper_instance.ready else "initializing",
        "scraper_ready": scraper_instance.ready if scraper_instance else False,
        "session_id": session.get('session_id'),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cache_status": {
            "manufacturers_cached": scraper_cache['manufacturers'] is not None,
            "models_cached": len(scraper_cache['models']),
            "cache_age": time.time() - scraper_cache['timestamp'] if scraper_cache['timestamp'] > 0 else 0
        }
    })

@app.route('/api/manufacturers')
def get_manufacturers():
    """Get all manufacturers with caching"""
    # Initialize session if not exists
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
        session.permanent = False
    
    scraper_instance = get_scraper()
    if not scraper_instance or not scraper_instance.ready:
        return jsonify({"error": "Scraper not ready"}), 503
    
    try:
        # Check cache
        if scraper_cache['manufacturers'] and (time.time() - scraper_cache['timestamp']) < CACHE_DURATION:
            manufacturers = scraper_cache['manufacturers']
        else:
            # Fetch fresh data
            manufacturers = scraper_instance.run_async(scraper_instance.explorer.get_manufacturers())
            
            if not manufacturers:
                return jsonify({"error": "Failed to fetch manufacturers"}), 500
            
            # Update cache
            scraper_cache['manufacturers'] = manufacturers
            scraper_cache['timestamp'] = time.time()
        
        # Apply search filter if provided
        search = request.args.get('search', '').lower()
        if search:
            manufacturers = [m for m in manufacturers if search in m['name'].lower()]
        
        # Apply limit if provided
        limit = request.args.get('limit', type=int)
        if limit:
            manufacturers = manufacturers[:limit]
        
        # Format for frontend
        formatted_manufacturers = []
        for m in manufacturers:
            formatted_manufacturers.append({
                "id": m['code'],
                "name": m['name'],
                "uri": m['uri'],
                "modelCount": m['model_count']
            })
        
        return jsonify({
            "success": True,
            "count": len(formatted_manufacturers),
            "data": formatted_manufacturers
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to fetch manufacturers: {str(e)}"}), 500

# Request deduplication cache
request_cache = {}
request_cache_lock = threading.Lock()
active_model_requests = set()

@app.route('/api/manufacturers/<manufacturer_id>/models')
def get_models(manufacturer_id):
    """Get models for a specific manufacturer with enhanced pagination"""
    # Check if we have a recent cached response for this exact request
    cache_key = f"models_{manufacturer_id}"
    with request_cache_lock:
        if cache_key in request_cache:
            cached_time, cached_response = request_cache[cache_key]
            if time.time() - cached_time < 5:  # 5 second cache to handle React rerenders
                print(f"📦 Returning cached response for {manufacturer_id}")
                return cached_response
        
        # Check if this exact request is already in progress
        if manufacturer_id in active_model_requests:
            print(f"⏳ Request for {manufacturer_id} already in progress, waiting...")
            # Wait for the other request to complete
            time.sleep(2)
            # Check cache again
            if cache_key in request_cache:
                cached_time, cached_response = request_cache[cache_key]
                if time.time() - cached_time < 10:
                    print(f"📦 Returning cached response after wait for {manufacturer_id}")
                    return cached_response
        
        # Mark this request as active
        active_model_requests.add(manufacturer_id)
    
    scraper_instance = get_scraper()
    if not scraper_instance or not scraper_instance.ready:
        return jsonify({"error": "Scraper not ready"}), 503
    
    try:
        # Check cache
        cache_key = manufacturer_id
        if cache_key in scraper_cache['models'] and (time.time() - scraper_cache['timestamp']) < CACHE_DURATION:
            models = scraper_cache['models'][cache_key]
            manufacturer_name = scraper_cache.get('manufacturer_name_' + cache_key, manufacturer_id)
        else:
            # Get manufacturer info
            manufacturers = scraper_cache['manufacturers'] or scraper_instance.run_async(scraper_instance.explorer.get_manufacturers())
            manufacturer = next((m for m in manufacturers if m['code'] == manufacturer_id or m['uri'] == manufacturer_id), None)
            
            if not manufacturer:
                return jsonify({"error": f"Manufacturer '{manufacturer_id}' not found"}), 404
            
            # Get models with better isolation
            models = scraper_instance.run_async(
                scraper_instance.explorer.get_models_for_manufacturer(
                    manufacturer['uri'], 
                    manufacturer['code']
                )
            )
            
            # Enhanced pagination: If we got a common page size limit, try to get more
            if models and len(models) in [50, 100, 104]:  # Common pagination limits
                print(f"📄 Detected potential pagination ({len(models)} models), attempting to fetch more...")
                
                try:
                    import json
                    import re
                    
                    # Collect all models from different methods
                    all_models = models.copy()
                    
                    # Method 1: Try with higher limit
                    async def fetch_with_limit(limit):
                        try:
                            await scraper_instance.explorer.page.goto(
                                f"https://www.partstown.com/part-predictor/{manufacturer['code']}/models?limit={limit}",
                                timeout=10000
                            )
                            await asyncio.sleep(1)
                            content = await scraper_instance.explorer.page.content()
                            return content
                        except:
                            return None
                    
                    for limit in [500, 1000]:
                        content = scraper_instance.run_async(fetch_with_limit(limit))
                        if content:
                            json_match = re.search(r'\[.*?\]', content)
                            if json_match:
                                try:
                                    extended = json.loads(json_match.group())
                                    if isinstance(extended, list) and len(extended) > len(all_models):
                                        all_models = extended
                                        print(f"✅ Found {len(extended)} models with limit={limit}")
                                        break
                                except:
                                    pass
                    
                    # Method 2: Try offset pagination if still at limit
                    if len(all_models) in [50, 100, 104]:
                        offset = len(all_models)
                        
                        for _ in range(10):  # Try up to 10 pages
                            async def fetch_page():
                                try:
                                    await scraper_instance.explorer.page.goto(
                                        f"https://www.partstown.com/part-predictor/{manufacturer['code']}/models?offset={offset}&limit=100",
                                        timeout=8000
                                    )
                                    await asyncio.sleep(0.5)
                                    content = await scraper_instance.explorer.page.content()
                                    return content
                                except:
                                    return None
                            
                            content = scraper_instance.run_async(fetch_page())
                            if content:
                                json_match = re.search(r'\[.*?\]', content)
                                if json_match:
                                    try:
                                        page_models = json.loads(json_match.group())
                                        if isinstance(page_models, list) and page_models:
                                            all_models.extend(page_models)
                                            print(f"✅ Found {len(page_models)} more at offset {offset}")
                                            offset += len(page_models)
                                            
                                            if len(page_models) < 100:
                                                break
                                        else:
                                            break
                                    except:
                                        break
                            else:
                                break
                    
                    # Deduplicate models
                    if len(all_models) > len(models):
                        unique = {}
                        for m in all_models:
                            if isinstance(m, dict):
                                key = m.get('name') or m.get('code') or m.get('modelCode', '')
                                if key and key not in unique:
                                    unique[key] = m
                        
                        models = list(unique.values())
                        print(f"✅ Total unique models: {len(models)} (was {len(all_models)} with duplicates)")
                
                except Exception as e:
                    print(f"⚠️ Enhanced pagination error: {e}")
                    # Continue with original models
            
            if not models:
                return jsonify({"error": "Failed to fetch models"}), 500
            
            print(f"📊 Final model count for {manufacturer['name']}: {len(models)}")
            
            # Update cache
            scraper_cache['models'][cache_key] = models
            scraper_cache['manufacturer_name_' + cache_key] = manufacturer['name']
            manufacturer_name = manufacturer['name']
        
        # Apply search filter if provided
        search = request.args.get('search', '').lower()
        if search:
            models = [m for m in models if search in m.get('name', '').lower() or search in m.get('description', '').lower()]
        
        # Apply limit if provided
        limit = request.args.get('limit', type=int)
        if limit:
            models = models[:limit]
        
        # Format for frontend
        formatted_models = []
        for m in models:
            model_entry = {
                "id": m.get('code', m.get('name', 'unknown')),
                "name": m.get('name', 'Unknown Model'),
                "description": m.get('description', ''),
                "url": m.get('url', ''),
                "manualCount": len(m.get('manuals', []))
            }
            
            # Include manuals if available
            if 'manuals' in m and m['manuals']:
                model_entry['manuals'] = []
                for manual in m['manuals']:
                    model_entry['manuals'].append({
                        "type": manual.get('type', 'Manual'),
                        "url": f"https://www.partstown.com{manual.get('link', '')}",
                        "language": manual.get('language', 'en')
                    })
            
            formatted_models.append(model_entry)
        
        response = jsonify({
            "success": True,
            "manufacturer": manufacturer_name,
            "count": len(formatted_models),
            "data": formatted_models
        })
        
        # Cache the successful response
        cache_key = f"models_{manufacturer_id}"
        with request_cache_lock:
            request_cache[cache_key] = (time.time(), response)
            # Remove from active requests
            active_model_requests.discard(manufacturer_id)
        
        return response
        
    except Exception as e:
        # Remove from active requests on error
        with request_cache_lock:
            active_model_requests.discard(manufacturer_id)
        return jsonify({"error": f"Failed to fetch models: {str(e)}"}), 500

@app.route('/api/manufacturers/<manufacturer_id>/models/<model_id>/manuals')
def get_manuals(manufacturer_id, model_id):
    """Get manuals for a specific model"""
    scraper_instance = get_scraper()
    if not scraper_instance or not scraper_instance.ready:
        return jsonify({"error": "Scraper not ready"}), 503
    
    try:
        # Check if we have the model data in cache
        cache_key = manufacturer_id
        if cache_key in scraper_cache['models']:
            models = scraper_cache['models'][cache_key]
        else:
            # Get manufacturer info
            manufacturers = scraper_cache['manufacturers'] or scraper_instance.run_async(scraper_instance.explorer.get_manufacturers())
            manufacturer = next((m for m in manufacturers if m['code'] == manufacturer_id or m['uri'] == manufacturer_id), None)
            
            if not manufacturer:
                return jsonify({"error": f"Manufacturer '{manufacturer_id}' not found"}), 404
            
            # Get models with better isolation
            models = scraper_instance.run_async(
                scraper_instance.explorer.get_models_for_manufacturer(
                    manufacturer['uri'], 
                    manufacturer['code']
                )
            )
            
            if not models:
                return jsonify({"error": "Failed to fetch models"}), 500
            
            # Update cache
            scraper_cache['models'][cache_key] = models
        
        # Find the specific model
        model = next((m for m in models if 
                     m.get('code', '') == model_id or 
                     m.get('name', '') == model_id or
                     m.get('name', '').lower().replace(' ', '-') == model_id.lower()), None)
        
        if not model:
            return jsonify({"error": f"Model '{model_id}' not found"}), 404
        
        # Extract manuals
        manuals = []
        if 'manuals' in model and model['manuals']:
            for manual in model['manuals']:
                manuals.append({
                    "type": manual.get('type', 'Manual'),
                    "url": f"https://www.partstown.com{manual.get('link', '')}",
                    "language": manual.get('language', 'en'),
                    "format": "PDF"
                })
        
        return jsonify({
            "success": True,
            "model": model.get('name', model_id),
            "description": model.get('description', ''),
            "count": len(manuals),
            "data": manuals
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to fetch manuals: {str(e)}"}), 500

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
    
    if not scraper or not scraper.ready:
        init_scraper()
        if not scraper.ready:
            return jsonify({"error": "Scraper not ready"}), 503
    
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
        
        # Check if file already exists
        if os.path.exists(local_path):
            print(f"📄 PDF already cached: {local_filename}")
            with open(local_path, 'rb') as f:
                pdf_content = f.read()
        else:
            # Download the PDF using the browser session
            async def download_pdf():
                page = scraper_instance.explorer.page
                
                try:
                    # Use page.request to download with authentication
                    response = await page.request.get(manual_url)
                    if response.ok:
                        pdf_content = await response.body()
                        print(f"✅ Downloaded PDF: {len(pdf_content)} bytes")
                        return pdf_content
                    else:
                        print(f"❌ HTTP {response.status}")
                except Exception as e:
                    print(f"Request error: {e}")
                
                # Fallback: Try direct navigation
                try:
                    context = page.context
                    download_page = await context.new_page()
                    
                    async with download_page.expect_download(timeout=30000) as download_info:
                        await download_page.goto(manual_url)
                    
                    download = await download_info.value
                    temp_path = os.path.join(tempfile.gettempdir(), "temp.pdf")
                    await download.save_as(temp_path)
                    
                    with open(temp_path, 'rb') as f:
                        content = f.read()
                    
                    os.unlink(temp_path)
                    await download_page.close()
                    
                    print(f"✅ Downloaded via navigation: {len(content)} bytes")
                    return content
                    
                except Exception as e:
                    print(f"Download error: {e}")
                    if 'download_page' in locals():
                        await download_page.close()
                    
                return None
        
            # Download the PDF using the async scraper
            scraper_instance = get_scraper()
            if not scraper_instance or not scraper_instance.ready:
                return jsonify({"error": "Scraper not ready"}), 503
            
            pdf_content = scraper_instance.run_async(download_pdf())
            
            # Save to local file if download successful
            if pdf_content:
                print(f"📥 Downloaded {len(pdf_content)} bytes")
                with open(local_path, 'wb') as f:
                    f.write(pdf_content)
                print(f"💾 Saved PDF locally: {local_filename}")
                
                # Track this PDF for the session
                if session_id not in session_pdfs:
                    session_pdfs[session_id] = []
                if local_filename not in session_pdfs[session_id]:
                    session_pdfs[session_id].append(local_filename)
                    print(f"📝 Tracking PDF {local_filename} for session {session_id}")
            else:
                print(f"⚠️ Failed to download PDF from {manual_url}")
        
        if pdf_content:
            # Get file size
            file_size_bytes = len(pdf_content)
            if file_size_bytes < 1024:
                file_size = f"{file_size_bytes} B"
            elif file_size_bytes < 1024 * 1024:
                file_size = f"{file_size_bytes / 1024:.1f} KB"
            else:
                file_size = f"{file_size_bytes / (1024 * 1024):.1f} MB"
            
            # Parse PDF to get page count and generate preview
            try:
                pdf_file = BytesIO(pdf_content)
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                page_count = len(pdf_reader.pages)
                
                # Generate preview of first page
                preview_base64 = None
                
                # Try PyMuPDF first (more reliable)
                try:
                    import fitz  # PyMuPDF
                    pdf_doc = fitz.open(stream=pdf_content, filetype="pdf")
                    if len(pdf_doc) > 0:
                        page = pdf_doc[0]  # First page
                        pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))  # 1.5x zoom for balance of quality and size
                        img_data = pix.pil_tobytes(format="PNG")
                        preview_base64 = base64.b64encode(img_data).decode('utf-8')
                        pdf_doc.close()
                        print(f"✅ Generated preview using PyMuPDF - {len(preview_base64)} chars")
                    else:
                        print("⚠️ PDF has no pages")
                except ImportError:
                    print("PyMuPDF not installed - trying pdf2image")
                    # Fallback to pdf2image
                    try:
                        from pdf2image import convert_from_bytes
                        # Convert first page to image with lower DPI for smaller size
                        images = convert_from_bytes(pdf_content, first_page=1, last_page=1, dpi=100)
                        if images:
                            # Convert PIL image to base64
                            img_buffer = BytesIO()
                            images[0].save(img_buffer, format='PNG', optimize=True)
                            img_buffer.seek(0)
                            preview_base64 = base64.b64encode(img_buffer.read()).decode('utf-8')
                            print(f"✅ Generated preview using pdf2image - {len(preview_base64)} chars")
                        else:
                            print("⚠️ pdf2image returned no images")
                    except ImportError:
                        print("❌ Neither PyMuPDF nor pdf2image installed - preview not available")
                    except Exception as e:
                        print(f"❌ Error with pdf2image: {e}")
                except Exception as e:
                    print(f"❌ Error generating preview with PyMuPDF: {e}")
                    import traceback
                    print(traceback.format_exc())
                    
            except Exception as e:
                print(f"Error parsing PDF: {e}")
                page_count = "Unknown"
                preview_base64 = None
            
            result = {
                "success": True,
                "pageCount": page_count,
                "fileSize": file_size,
                "filename": filename,
                "url": manual_url,
                "localUrl": f"/public/temp-pdfs/{local_filename}"
            }
            
            # Add preview if available
            if preview_base64:
                result["preview"] = f"data:image/png;base64,{preview_base64}"
                
            return jsonify(result)
        else:
            # If download failed, return placeholder data
            return jsonify({
                "success": True,
                "pageCount": "Unable to download",
                "fileSize": "N/A",
                "filename": filename,
                "url": manual_url,
                "note": "PDF could not be downloaded - may require manual access"
            })
        
    except Exception as e:
        import traceback
        print(f"Error in manual metadata: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": f"Failed to process manual: {str(e)}"}), 500

@app.route('/api/session-status')
def session_status():
    """Get current session status and PDFs"""
    session_id = session.get('session_id')
    if not session_id:
        session['session_id'] = str(uuid.uuid4())
        session.permanent = False
        session_id = session['session_id']
    
    pdfs = session_pdfs.get(session_id, [])
    
    return jsonify({
        "session_id": session_id,
        "pdf_count": len(pdfs),
        "pdfs": pdfs,
        "active_sessions": len(session_pdfs)
    })

@app.route('/api/cleanup-pdfs', methods=['POST'])
def cleanup_pdfs_endpoint():
    """Manual cleanup endpoint to remove old PDFs"""
    try:
        cleanup_old_pdfs()
        # Also count current PDFs
        pdf_count = 0
        total_size = 0
        if os.path.exists(TEMP_PDF_DIR):
            for filename in os.listdir(TEMP_PDF_DIR):
                filepath = os.path.join(TEMP_PDF_DIR, filename)
                if os.path.isfile(filepath):
                    pdf_count += 1
                    total_size += os.path.getsize(filepath)
        
        return jsonify({
            "success": True,
            "message": "Cleanup completed",
            "remaining_pdfs": pdf_count,
            "total_size_mb": round(total_size / (1024 * 1024), 2)
        })
    except Exception as e:
        return jsonify({"error": f"Cleanup failed: {str(e)}"}), 500

@app.route('/api/clear-session-pdfs', methods=['POST'])
def clear_session_pdfs():
    """Clear PDFs for the current session only"""
    try:
        # Get session ID
        session_id = session.get('session_id')
        if not session_id:
            return jsonify({
                "success": True,
                "message": "No session to clear",
                "count": 0
            })
        
        cleared_count = 0
        if session_id in session_pdfs and os.path.exists(TEMP_PDF_DIR):
            for filename in session_pdfs[session_id]:
                filepath = os.path.join(TEMP_PDF_DIR, filename)
                if os.path.isfile(filepath):
                    os.remove(filepath)
                    cleared_count += 1
                    print(f"Removed PDF for session {session_id}: {filename}")
            
            # Clear the session's PDF list
            del session_pdfs[session_id]
        
        return jsonify({
            "success": True,
            "message": f"Cleared {cleared_count} PDFs for session {session_id}",
            "session_id": session_id,
            "count": cleared_count
        })
    except Exception as e:
        return jsonify({"error": f"Clear failed: {str(e)}"}), 500

@app.route('/api/clear-all-pdfs', methods=['POST'])
def clear_all_pdfs():
    """Legacy endpoint - now clears only session PDFs"""
    return clear_session_pdfs()

@app.route('/api/clear-pdf', methods=['POST'])
def clear_specific_pdf():
    """Clear a specific PDF by filename"""
    try:
        data = request.get_json() or {}
        filename = data.get('filename')
        
        if not filename:
            return jsonify({"error": "Filename is required"}), 400
        
        session_id = session.get('session_id')
        
        filepath = os.path.join(TEMP_PDF_DIR, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            print(f"Removed specific PDF: {filename}")
            
            # Remove from session tracking
            if session_id and session_id in session_pdfs:
                if filename in session_pdfs[session_id]:
                    session_pdfs[session_id].remove(filename)
                    if not session_pdfs[session_id]:  # Clean up empty session
                        del session_pdfs[session_id]
            
            return jsonify({
                "success": True,
                "message": f"Removed {filename}"
            })
        else:
            return jsonify({
                "success": False,
                "message": "File not found"
            })
    except Exception as e:
        return jsonify({"error": f"Clear failed: {str(e)}"}), 500

@app.route('/api/process-manual', methods=['POST'])
def process_manual():
    """Process a manual into components (placeholder for future implementation)"""
    data = request.get_json()
    
    if not data or 'manualUrl' not in data:
        return jsonify({"error": "Manual URL is required"}), 400
    
    manual_url = data['manualUrl']
    
    # Placeholder response for manual processing
    # This would be where the AI processing happens
    return jsonify({
        "success": True,
        "message": "Manual processing initiated",
        "manualUrl": manual_url,
        "status": "processing",
        "estimatedTime": "2-3 minutes",
        "components": {
            "steps": "Extracting step-by-step procedures...",
            "visuals": "Identifying diagrams and images...",
            "parts": "Cataloging parts and components...",
            "warnings": "Extracting safety warnings..."
        }
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    print("🚀 Starting Sequential Manual Processor API Server...")
    print("📖 API Documentation: http://localhost:8888/")
    print("🔍 Health Check: http://localhost:8888/health")
    print("🏭 Manufacturers: http://localhost:8888/api/manufacturers")
    print("\n⚠️  Make sure the PartsTown scraper is available in '../API Scraper V2/'")
    
    # Run the server - using single thread to avoid Playwright conflicts
    app.run(host='127.0.0.1', port=8888, debug=False, threaded=False)