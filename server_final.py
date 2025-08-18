#!/usr/bin/env python3
"""
Sequential Manual Processor API Server - Final version with synchronous scraper
"""

from flask import Flask, jsonify, request, session
from flask_cors import CORS
import sys
import os
import time
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
import json

# Add the scraper to the path
sys.path.append('../API Scraper V2')
from sync_scraper import PartsTownSyncScraper

app = Flask(__name__, static_folder='public', static_url_path='/public')
app.secret_key = secrets.token_hex(32)
CORS(app, origins=['http://localhost:3000', 'http://localhost:3001'], supports_credentials=True)

# Global scraper instance
scraper = PartsTownSyncScraper()

# Global cache for scraped data
scraper_cache = {
    'manufacturers': None,
    'models': {},
    'manufacturers_timestamp': None
}

CACHE_DURATION = 300  # 5 minutes cache
TEMP_PDF_DIR = os.path.join(os.path.dirname(__file__), 'public', 'temp-pdfs')
PDF_CLEANUP_HOURS = 24

# Session-based PDF tracking
session_pdfs = {}

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

@app.route('/')
def index():
    """API documentation homepage"""
    return jsonify({
        "name": "Sequential Manual Processor API",
        "version": "3.0",
        "endpoints": {
            "health": "/health",
            "manufacturers": "/api/manufacturers",
            "models": "/api/manufacturers/<id>/models", 
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
    global scraper_cache
    
    # Check cache
    if scraper_cache['manufacturers'] and scraper_cache['manufacturers_timestamp']:
        if (datetime.now() - scraper_cache['manufacturers_timestamp']).seconds < CACHE_DURATION:
            return jsonify(scraper_cache['manufacturers'])
    
    print("📋 Fetching manufacturers...")
    manufacturers = scraper.get_manufacturers()
    
    # Update cache
    scraper_cache['manufacturers'] = manufacturers
    scraper_cache['manufacturers_timestamp'] = datetime.now()
    
    return jsonify(manufacturers)

@app.route('/api/manufacturers/<manufacturer_id>/models')
def get_models(manufacturer_id):
    """Get models for a specific manufacturer"""
    global scraper_cache
    
    print(f"🔧 Fetching models for {manufacturer_id}...")
    
    # Check cache
    if manufacturer_id in scraper_cache['models']:
        cached_time, cached_models = scraper_cache['models'][manufacturer_id]
        if (datetime.now() - cached_time).seconds < CACHE_DURATION:
            print(f"📦 Returning cached models for {manufacturer_id}")
            return jsonify({
                "manufacturer": manufacturer_id,
                "models": cached_models
            })
    
    # Get manufacturer info
    manufacturers_response = get_manufacturers()
    manufacturers = manufacturers_response.get_json()
    manufacturer = next((m for m in manufacturers if m['code'] == manufacturer_id), None)
    
    if not manufacturer:
        return jsonify({"error": f"Manufacturer '{manufacturer_id}' not found"}), 404
    
    # Get models using synchronous scraper
    print(f"🔄 Fetching fresh models for {manufacturer['name']}...")
    models = scraper.get_models_for_manufacturer(manufacturer['uri'], manufacturer['code'])
    
    # Update cache
    scraper_cache['models'][manufacturer_id] = (datetime.now(), models)
    
    print(f"📊 Final model count for {manufacturer['name']}: {len(models)}")
    
    return jsonify({
        "manufacturer": manufacturer['name'],
        "models": models
    })

@app.route('/api/manual-metadata')
def get_manual_metadata():
    """Download PDF and analyze it"""
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
        
        # Extract filename from URL
        filename = manual_url.split('/')[-1].split('?')[0]
        
        # Generate a unique filename based on URL hash
        url_hash = hashlib.md5(manual_url.encode()).hexdigest()[:8]
        local_filename = f"{url_hash}_{filename}"
        local_path = os.path.join(TEMP_PDF_DIR, local_filename)
        
        # Download the PDF if not already cached
        if not os.path.exists(local_path):
            print(f"📥 Downloading PDF: {manual_url}")
            response = requests.get(manual_url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }, timeout=30)
            
            if response.status_code == 200:
                with open(local_path, 'wb') as f:
                    f.write(response.content)
                print(f"✅ Downloaded {len(response.content)} bytes")
            else:
                return jsonify({"error": f"Failed to download PDF: {response.status_code}"}), 500
        
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
            with open(local_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                num_pages = len(pdf_reader.pages)
        except:
            num_pages = 1
        
        return jsonify({
            "status": "success",
            "metadata": {
                "title": filename,
                "pages": num_pages,
                "size": os.path.getsize(local_path)
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
    print("\n🚀 Starting Sequential Manual Processor API Server (Final)...")
    print("📖 API Documentation: http://localhost:8888/")
    print("🔍 Health Check: http://localhost:8888/health")
    print("🏭 Manufacturers: http://localhost:8888/api/manufacturers")
    print()
    print("✨ Using synchronous scraper - no subprocess complexity!")
    
    # Ensure temp directories exist
    os.makedirs(TEMP_PDF_DIR, exist_ok=True)
    
    # Clean up old PDFs on startup
    cleanup_old_pdfs()
    
    app.run(port=8888, debug=False)