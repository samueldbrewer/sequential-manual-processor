# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
Sequential AI Manual Processor - A web application that integrates with PartsTown.com to browse equipment manufacturers, models, and technical manuals. The system downloads PDFs locally, generates previews, and provides infrastructure for AI-powered manual processing.

## Commands

### Starting the Application
```bash
./start.sh        # Recommended: Starts both frontend and backend, installs dependencies
./stop.sh         # Stops all services
```

### Manual startup (if start.sh fails):
```bash
# Backend (port 8888)
python -u server.py > backend.log 2>&1 &

# Frontend (port 3000)
npm start
```

### Monitoring
```bash
tail -f backend.log  # View backend logs with PDF processing details
```

### Testing Manual Processing
When testing PDF downloads and preview generation, check logs for:
- `📥 Downloaded X bytes` - Confirms PDF download
- `✅ Generated preview using PyMuPDF` - Preview generation success
- `📝 Tracking PDF for session` - Session management working
- `❌` prefixed messages indicate failures

## Architecture

### Backend (server.py)
- **Flask API** on port 8888 with session-based management
- **PartsTown Scraper Integration**: Uses `../API Scraper V2/interactive_scraper.py` for web scraping
- **Async Browser Management**: Maintains Playwright browser instance for authenticated scraping
- **PDF Processing Pipeline**:
  1. Downloads PDFs using authenticated Playwright session
  2. Stores in `public/temp-pdfs/` with hash-based naming
  3. Generates preview using PyMuPDF (primary) or pdf2image (fallback)
  4. Tracks PDFs per session to prevent concurrent user conflicts
  5. Auto-cleanup of old PDFs (24 hours)

### Frontend (React/TypeScript)
- **App.tsx**: Main component with manufacturer/model selection workflow
- **API Service**: Uses axios with credentials for session management
- **Loading Progress**: Logarithmic progress bars that slow after 80%
- **Session Cleanup**: Clears PDFs on back navigation, reset, or page unload

### Critical Dependencies
The application REQUIRES the PartsTown scraper in the parent directory:
```
../API Scraper V2/interactive_scraper.py
```

### Session Management
- Each user gets a unique session ID via Flask sessions
- PDFs are tracked in `session_pdfs` dictionary
- `/api/clear-session-pdfs` only removes current session's PDFs
- Prevents interference between concurrent users

## API Endpoints

### Core Endpoints
- `GET /api/manufacturers` - Returns cached manufacturer list
- `GET /api/manufacturers/{id}/models` - Fetches models with enhanced pagination support
  - Automatically detects pagination limits (50, 100, 104 models)
  - Attempts to fetch additional pages using offset/limit parameters
  - Tries higher limits (500, 1000) to bypass pagination
  - Deduplicates models across pages
- `GET /api/manual-metadata?url={pdf_url}` - Downloads PDF, generates preview, returns metadata
- `POST /api/clear-session-pdfs` - Clears PDFs for current session only

### Response Patterns
- 500 errors during startup are normal (browser initializing)
- First manufacturer fetch takes 10-15 seconds (browser startup)
- Subsequent requests use caching (5 minute TTL)

## Known Limitations

### Model Fetching Pagination
The PartsTown API returns models in pages. While we've implemented enhanced pagination:
- Some manufacturers may have more models than displayed
- The API may limit results despite pagination attempts
- Manual verification on the website may show additional models
- Future improvements could include parallel API requests or DOM scraping

## Common Issues and Solutions

### PDF Preview Not Loading
Check if PyMuPDF and pdf2image are installed in the virtual environment:
```bash
source venv/bin/activate
pip install PyMuPDF pdf2image
```

### Logs Not Showing Debug Messages
Ensure Python runs with unbuffered output (`python -u`) in start.sh

### Port Already in Use
```bash
lsof -i :8888 | grep LISTEN | awk '{print $2}' | xargs kill -9
lsof -i :3000 | grep LISTEN | awk '{print $2}' | xargs kill -9
```

### Browser Not Starting
The scraper needs Playwright browsers installed:
```bash
playwright install chromium
```

## Development Workflow

### Adding New Features
1. Backend changes go in `server.py`
2. Frontend components in `src/components/`
3. API integration through `src/services/api.ts`
4. Always test PDF download/preview functionality after changes

### Testing PDF Processing
1. Select any manufacturer (e.g., "Henny Penny")
2. Choose a model with manuals
3. Click a manual to trigger download
4. Check backend.log for processing status
5. Verify preview appears in UI

### Session Testing
Open multiple browser tabs/incognito windows to test concurrent sessions. Each should maintain separate PDF collections.

## Important File Locations
- Downloaded PDFs: `public/temp-pdfs/`
- Backend logs: `backend.log`
- Virtual environment: `venv/`
- Scraper dependency: `../API Scraper V2/`