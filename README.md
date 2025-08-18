# Sequential Manual Processor

A web application for browsing and accessing equipment manuals from PartsTown, with local PDF caching and preview generation.

## Features

- Browse equipment manufacturers and models
- Fetch and display technical manuals
- Download and cache PDFs locally
- Generate PDF previews
- Fast cached data for instant responses
- Session-based PDF management

## Tech Stack

- **Frontend**: React, TypeScript, Material-UI
- **Backend**: Python Flask
- **PDF Processing**: PyMuPDF
- **Data**: Cached manufacturer/model data (344 manufacturers with models)

## Installation

### Prerequisites

- Node.js 14+
- Python 3.8+
- pip

### Setup

1. Clone the repository:
```bash
git clone https://github.com/samueldbrewer/sequential-manual-processor.git
cd sequential-manual-processor
```

2. Install frontend dependencies:
```bash
npm install
```

3. Install backend dependencies:
```bash
pip install -r requirements.txt
```

4. Install Playwright browsers (if needed):
```bash
playwright install chromium
```

## Running Locally

### Quick Start
```bash
./start.sh
```

This will start both frontend (port 3000) and backend (port 8888).

### Manual Start

Backend:
```bash
python server_cached.py
```

Frontend:
```bash
npm start
```

Access the application at http://localhost:3000

## Project Structure

```
sequential-manual-app/
├── src/                    # React frontend source
├── public/                 # Static files and temp PDFs
├── cache/                  # Cached manufacturer/model data
│   ├── manufacturers.json  # 489 manufacturers
│   └── models/            # Model data for each manufacturer
├── server_cached.py       # Flask backend server
├── fetch_manuals_curl.py  # Fast manual fetching
├── download_pdf_curl.py   # Fast PDF downloading
└── requirements.txt       # Python dependencies
```

## Deployment

The application is configured for deployment on Railway with:
- Automatic dependency installation
- Environment variable support
- Static file serving

## Environment Variables

- `PORT`: Server port (default: 8888)
- `NODE_ENV`: Node environment (development/production)

## Cache Information

- 344 manufacturers with model data
- 145 manufacturers without models (hidden in UI)
- Fast response times using cached data
- Manual fetching available for all models

## License

MIT