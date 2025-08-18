#!/usr/bin/env python3
"""
Sequential Manual Processor API Server - Cached Version
Uses pre-scraped cache data for manufacturers and models, fetches manuals live
"""

from flask import Flask, jsonify, request, session
from flask_cors import CORS
import json
import os
import sys
import time
import requests
import hashlib
from datetime import datetime, timedelta
import secrets
import asyncio
from pathlib import Path
import base64
from io import BytesIO

# For live manual fetching when needed
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'API Scraper V2'))

app = Flask(__name__, static_folder='public', static_url_path='/public')
app.secret_key = secrets.token_hex(32)
CORS(app, origins=['http://localhost:3000', 'http://localhost:3001'], supports_credentials=True)

# Cache directories
CACHE_DIR = os.path.join(os.path.dirname(__file__), 'cache')
MODELS_CACHE_DIR = os.path.join(CACHE_DIR, 'models')
TEMP_PDF_DIR = os.path.join(os.path.dirname(__file__), 'public', 'temp-pdfs')
PDF_CLEANUP_HOURS = 24

# Session-based PDF tracking
session_pdfs = {}

# Load manufacturers cache on startup
manufacturers_cache = None
try:
    with open(os.path.join(CACHE_DIR, 'manufacturers.json'), 'r') as f:
        manufacturers_cache = json.load(f)
        print(f"✅ Loaded {len(manufacturers_cache)} manufacturers from cache")
except Exception as e:
    print(f"❌ Error loading manufacturers cache: {e}")
    manufacturers_cache = []

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

def get_session_id():
    """Get or create a session ID for the current user"""
    if 'session_id' not in session:
        session['session_id'] = secrets.token_hex(16)
    return session['session_id']

@app.route('/api/manufacturers', methods=['GET'])
def get_manufacturers():
    """Return cached manufacturers instantly"""
    try:
        if not manufacturers_cache:
            return jsonify({'success': False, 'error': 'No manufacturers data available'}), 503
        
        # Transform data to match frontend expectations
        transformed_manufacturers = []
        for mfg in manufacturers_cache:
            # Check actual model count from cache file
            cache_file = os.path.join(MODELS_CACHE_DIR, f"{mfg['code']}.json")
            actual_model_count = 0
            
            if os.path.exists(cache_file):
                try:
                    with open(cache_file, 'r') as f:
                        cache_data = json.load(f)
                        actual_model_count = len(cache_data.get('models', []))
                except:
                    pass
            
            transformed_manufacturers.append({
                'id': mfg['code'],  # Frontend expects 'id' not 'code'
                'name': mfg['name'],
                'uri': mfg['uri'],
                'modelCount': actual_model_count,  # Use actual count from cache
                'hasModels': actual_model_count > 0  # Add flag for filtering
            })
        
        return jsonify({'success': True, 'data': transformed_manufacturers})
    except Exception as e:
        print(f"❌ Error getting manufacturers: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/manufacturers/<manufacturer_id>/models', methods=['GET'])
def get_models(manufacturer_id):
    """Return cached models for a manufacturer instantly"""
    try:
        # Load models from cache file
        cache_file = os.path.join(MODELS_CACHE_DIR, f"{manufacturer_id}.json")
        
        if not os.path.exists(cache_file):
            print(f"⚠️ No cache file for {manufacturer_id}")
            return jsonify({'success': False, 'error': f'No models data for manufacturer {manufacturer_id}'}), 404
        
        with open(cache_file, 'r') as f:
            cache_data = json.load(f)
        
        models = cache_data.get('models', [])
        print(f"✅ Returning {len(models)} cached models for {manufacturer_id}")
        
        # Transform models to match frontend expectations
        transformed_models = []
        for model in models:
            transformed_models.append({
                'id': model.get('code', model.get('name')),  # Frontend expects 'id'
                'name': model.get('name'),
                'url': model.get('url'),
                'description': model.get('description'),  # May not exist but frontend checks for it
                'manuals': model.get('manuals', []),  # Include manuals if they exist
                'manualCount': len(model.get('manuals', []))  # Count of manuals
            })
        
        # Return in the expected format
        return jsonify({'success': True, 'data': transformed_models})
        
    except Exception as e:
        print(f"❌ Error getting models for {manufacturer_id}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/manufacturers/<manufacturer_id>/models/<model_id>/manuals', methods=['GET'])
def get_manuals(manufacturer_id, model_id):
    """Get manuals for a specific model - fetch live since not in cache"""
    try:
        # Load the cached models file to get manufacturer info
        cache_file = os.path.join(MODELS_CACHE_DIR, f"{manufacturer_id}.json")
        
        if not os.path.exists(cache_file):
            return jsonify({'error': f'No data for manufacturer {manufacturer_id}'}), 404
        
        with open(cache_file, 'r') as f:
            cache_data = json.load(f)
        
        manufacturer_uri = cache_data['manufacturer']['uri']
        
        # Find the specific model to verify it exists
        models = cache_data.get('models', [])
        model = None
        
        for m in models:
            if m.get('code') == model_id or m.get('name') == model_id:
                model = m
                break
        
        if not model:
            return jsonify({'error': f'Model {model_id} not found'}), 404
        
        # Check if manuals are already in cache (unlikely with current cache)
        manuals = model.get('manuals', [])
        
        if manuals:
            print(f"✅ Found {len(manuals)} cached manuals for {model_id}")
            formatted_manuals = []
            for manual in manuals:
                formatted_manuals.append({
                    'type': manual.get('typeCode', manual.get('type', '')),
                    'title': manual.get('type', manual.get('title', '')),
                    'url': manual.get('link', ''),
                    'full_url': f"https://www.partstown.com{manual.get('link', '')}" if manual.get('link') else ''
                })
            return jsonify({'success': True, 'data': formatted_manuals})
        
        # Fetch actual manual links using fast curl method
        print(f"🔍 Fetching manual links for {manufacturer_uri}/{model_id}")
        
        # Use the fast curl-based approach
        from fetch_manuals_curl import fetch_manuals_via_curl
        
        try:
            # Fetch the actual manual links via curl (much faster)
            print(f"🚀 Using fast curl method for '{manufacturer_uri}/{model_id}'")
            manuals = fetch_manuals_via_curl(manufacturer_uri, model_id)
            
            if manuals:
                print(f"✅ Found {len(manuals)} manuals for {model_id}")
                # Format for frontend
                formatted_manuals = []
                for manual in manuals:
                    formatted_manuals.append({
                        'type': manual.get('type', ''),
                        'title': manual.get('title', ''),
                        'url': manual.get('link', ''),
                        'full_url': f"https://www.partstown.com{manual.get('link', '')}" if manual.get('link') else ''
                    })
                return jsonify({'success': True, 'data': formatted_manuals})
            else:
                print(f"⚠️ No manuals found for {model_id}")
                return jsonify({'success': True, 'data': []})
                
        except Exception as e:
            print(f"❌ Error fetching manual links: {e}")
            return jsonify({'success': True, 'data': []})
            
    except Exception as e:
        print(f"❌ Error getting manuals: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/manual-metadata', methods=['GET'])
def get_manual_metadata():
    """Download a manual PDF and generate preview/metadata"""
    manual_url = request.args.get('url')
    if not manual_url:
        return jsonify({'error': 'No URL provided'}), 400
    
    try:
        session_id = get_session_id()
        
        # Parse manufacturer and model from the request
        # We need these to properly authenticate the download
        manufacturer_id = request.args.get('manufacturer_id')
        model_id = request.args.get('model_id')
        
        if not manufacturer_id or not model_id:
            # Try to extract from referrer or use defaults
            # For now, we'll try without them but it may fail
            print("⚠️ No manufacturer_id or model_id provided, download may fail")
        
        # Get manufacturer URI from cache if we have the ID
        manufacturer_uri = None
        if manufacturer_id:
            for mfg in manufacturers_cache:
                if mfg['code'] == manufacturer_id:
                    manufacturer_uri = mfg['uri']
                    break
        
        # Remove query params for cleaner filename
        clean_url = manual_url.split('?')[0] if '?' in manual_url else manual_url
        
        print(f"📥 Downloading manual from: {manual_url}")
        print(f"📦 Manufacturer: {manufacturer_uri}, Model: {model_id}")
        
        # Use the fast curl-based download approach
        from download_pdf_curl import download_pdf_via_curl
        
        # Download PDF using curl (much faster than Playwright)
        result = download_pdf_via_curl(manual_url, manufacturer_uri, model_id)
        
        if result['success']:
            pdf_content = result['content']
            print(f"✅ Downloaded {len(pdf_content)} bytes in {result['time']:.2f}s via curl")
        else:
            print(f"❌ Download failed: {result['error']}")
            # Try fallback without referer
            print("🔄 Trying direct download without referer...")
            result = download_pdf_via_curl(manual_url)
            
            if result['success']:
                pdf_content = result['content']
                print(f"✅ Downloaded {len(pdf_content)} bytes in {result['time']:.2f}s (direct)")
            else:
                print(f"❌ Direct download also failed: {result['error']}")
                return jsonify({'error': f"Failed to download PDF: {result['error']}"}), 500
        
        # Generate filename from URL
        pdf_hash = hashlib.md5(clean_url.encode()).hexdigest()
        pdf_filename = f"{pdf_hash}.pdf"
        pdf_path = os.path.join(TEMP_PDF_DIR, pdf_filename)
        
        # Save PDF
        os.makedirs(TEMP_PDF_DIR, exist_ok=True)
        with open(pdf_path, 'wb') as f:
            f.write(pdf_content)
        
        print(f"💾 Saved PDF to: {pdf_path}")
        
        # Track PDF for this session
        if session_id not in session_pdfs:
            session_pdfs[session_id] = []
        if pdf_filename not in session_pdfs[session_id]:
            session_pdfs[session_id].append(pdf_filename)
            print(f"📝 Tracking PDF for session {session_id}: {pdf_filename}")
        
        # Generate preview and get PDF metadata
        preview_data, page_count = generate_pdf_preview_and_metadata(pdf_path)
        
        # Format file size
        file_size_mb = len(pdf_content) / (1024 * 1024)
        if file_size_mb >= 1:
            file_size_str = f"{file_size_mb:.1f} MB"
        else:
            file_size_kb = len(pdf_content) / 1024
            file_size_str = f"{file_size_kb:.1f} KB"
        
        # Get PDF metadata
        metadata = {
            'title': os.path.basename(clean_url),
            'url': manual_url,
            'local_path': f"/public/temp-pdfs/{pdf_filename}",
            'localUrl': f"/public/temp-pdfs/{pdf_filename}",  # Frontend expects localUrl
            'size': len(pdf_content),
            'fileSize': file_size_str,
            'pageCount': page_count,
            'preview': preview_data,
            'session_id': session_id
        }
        
        return jsonify(metadata)
        
    except Exception as e:
        print(f"❌ Error processing manual: {e}")
        return jsonify({'error': str(e)}), 500

def generate_pdf_preview_and_metadata(pdf_path):
    """Generate a preview image for the PDF and return metadata"""
    try:
        # Try PyMuPDF first (faster and better quality)
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(pdf_path)
            page_count = len(doc)  # Get total page count
            page = doc[0]  # Get first page
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better quality
            img_data = pix.tobytes("png")
            doc.close()
            
            preview_base64 = base64.b64encode(img_data).decode('utf-8')
            print(f"✅ Generated preview using PyMuPDF - {page_count} pages")
            return f"data:image/png;base64,{preview_base64}", page_count
            
        except ImportError:
            print("PyMuPDF not available, trying pdf2image...")
            
            # Fallback to pdf2image
            from pdf2image import convert_from_path
            import fitz
            
            # Get page count using PyMuPDF even if preview fails
            try:
                doc = fitz.open(pdf_path)
                page_count = len(doc)
                doc.close()
            except:
                page_count = None
            
            images = convert_from_path(pdf_path, first_page=1, last_page=1, dpi=150)
            
            if images:
                img_buffer = BytesIO()
                images[0].save(img_buffer, format='PNG')
                img_buffer.seek(0)
                preview_base64 = base64.b64encode(img_buffer.read()).decode('utf-8')
                print(f"✅ Generated preview using pdf2image - {page_count or 'unknown'} pages")
                return f"data:image/png;base64,{preview_base64}", page_count
                
        except Exception as e:
            print(f"❌ Preview generation failed: {e}")
            return None, None
            
    except Exception as e:
        print(f"❌ Error generating preview: {e}")
        return None, None

@app.route('/api/clear-session-pdfs', methods=['POST'])
def clear_session_pdfs():
    """Clear PDFs for the current session only"""
    try:
        session_id = get_session_id()
        
        if session_id in session_pdfs:
            pdfs_to_remove = session_pdfs[session_id]
            for pdf_filename in pdfs_to_remove:
                pdf_path = os.path.join(TEMP_PDF_DIR, pdf_filename)
                if os.path.exists(pdf_path):
                    os.remove(pdf_path)
                    print(f"🗑️ Removed PDF for session {session_id}: {pdf_filename}")
            
            # Clear the session's PDF list
            session_pdfs[session_id] = []
            print(f"✅ Cleared {len(pdfs_to_remove)} PDFs for session {session_id}")
            
            return jsonify({'success': True, 'cleared': len(pdfs_to_remove)})
        else:
            print(f"⚠️ No PDFs to clear for session {session_id}")
            return jsonify({'success': True, 'cleared': 0})
            
    except Exception as e:
        print(f"❌ Error clearing session PDFs: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Check cache status
        cache_info = {
            'manufacturers_loaded': len(manufacturers_cache) if manufacturers_cache else 0,
            'cache_dir_exists': os.path.exists(CACHE_DIR),
            'models_cache_dir_exists': os.path.exists(MODELS_CACHE_DIR),
            'model_files_count': len(os.listdir(MODELS_CACHE_DIR)) if os.path.exists(MODELS_CACHE_DIR) else 0
        }
        
        # Check cache timestamp
        timestamp_file = os.path.join(CACHE_DIR, 'cache_timestamp.json')
        if os.path.exists(timestamp_file):
            with open(timestamp_file, 'r') as f:
                timestamp_data = json.load(f)
                cache_info['last_updated'] = timestamp_data.get('last_updated')
                cache_info['total_models_cached'] = timestamp_data.get('total_models_cached')
        
        return jsonify({
            'status': 'healthy',
            'cache': cache_info,
            'session_id': get_session_id() if 'session_id' in session else None
        })
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

if __name__ == '__main__':
    # Clean up old PDFs on startup
    cleanup_old_pdfs()
    
    # Get port from environment variable or default to 8888
    port = int(os.environ.get('PORT', 8888))
    
    print("🚀 Starting Sequential Manual Processor API Server (Cached Version)")
    print(f"📂 Cache directory: {CACHE_DIR}")
    print(f"📊 Loaded {len(manufacturers_cache)} manufacturers")
    print(f"📁 Model cache files: {len(os.listdir(MODELS_CACHE_DIR)) if os.path.exists(MODELS_CACHE_DIR) else 0}")
    print(f"🌐 Server running on port {port}")
    print("⚡ Using cached data for instant responses!")
    
    # Use host 0.0.0.0 for Railway deployment
    app.run(host='0.0.0.0', port=port, debug=False)