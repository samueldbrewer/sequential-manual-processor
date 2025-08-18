"""
PDF Processing Module for Sequential Manual Processor
Handles PDF download and analysis using Playwright for authentication
"""

import asyncio
from playwright.async_api import async_playwright
import PyPDF2
from io import BytesIO
import tempfile
import os

class PDFProcessor:
    """Handles PDF downloading and processing through Playwright"""
    
    async def download_and_analyze_pdf(self, pdf_url):
        """
        Download a PDF using Playwright and analyze it
        Returns metadata including page count and file size
        """
        async with async_playwright() as p:
            # Launch browser in headless mode
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                accept_downloads=True
            )
            
            try:
                page = await context.new_page()
                
                # Create a temporary directory for downloads
                with tempfile.TemporaryDirectory() as temp_dir:
                    # Start waiting for download before clicking
                    async with page.expect_download() as download_info:
                        # Navigate to the PDF URL
                        await page.goto(pdf_url)
                    
                    download = await download_info.value
                    
                    # Save the downloaded file
                    temp_path = os.path.join(temp_dir, "temp.pdf")
                    await download.save_as(temp_path)
                    
                    # Read the file for analysis
                    with open(temp_path, 'rb') as f:
                        pdf_content = f.read()
                    
                    # Get file size
                    file_size_bytes = len(pdf_content)
                    if file_size_bytes < 1024:
                        file_size = f"{file_size_bytes} B"
                    elif file_size_bytes < 1024 * 1024:
                        file_size = f"{file_size_bytes / 1024:.1f} KB"
                    else:
                        file_size = f"{file_size_bytes / (1024 * 1024):.1f} MB"
                    
                    # Parse PDF to get page count
                    try:
                        pdf_file = BytesIO(pdf_content)
                        pdf_reader = PyPDF2.PdfReader(pdf_file)
                        page_count = len(pdf_reader.pages)
                    except Exception as e:
                        print(f"Error parsing PDF: {e}")
                        page_count = None
                    
                    return {
                        "success": True,
                        "pageCount": page_count,
                        "fileSize": file_size,
                        "filename": download.suggested_filename or "manual.pdf"
                    }
                    
            except Exception as e:
                print(f"Error downloading PDF: {e}")
                return {
                    "success": False,
                    "error": str(e)
                }
            finally:
                await browser.close()

# Function to run async code from sync context
def process_pdf_sync(pdf_url):
    """Synchronous wrapper for PDF processing"""
    processor = PDFProcessor()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(processor.download_and_analyze_pdf(pdf_url))
        return result
    finally:
        loop.close()