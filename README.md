# Large Language Model Engineering

Automated web scraping pipeline to discover, extract, and normalize public tender opportunities into actionable insights.

## Overview
This project uses Python and Selenium to collect tender data from target sources, with options to persist to a database and export results. It’s structured for reliability and easy extension to new sources.

## Features
- Headless Selenium scraping with configurable driver
- Pluggable target URLs and selectors
- Basic error handling and retry scaffolding
- Exports to CSV/JSON; optional DB persistence

## Project Structure
- `Tender_Intelligence_Platform.py` — main scraping logic/runner
- `web_scrapping using Selenium.ipynb` — exploration/prototyping notebook
- `requirements.txt` — pinned Python dependencies
- `.env` — local environment variables (not committed)
- `.env.example` — template for environment configuration

## Requirements
- Python 3.9+
- Chrome/Chromedriver or compatible WebDriver

## Setup
1. Create and activate a virtual environment
2. Install dependencies
3. Configure environment variables

### 1) Virtual environment
(Windows PowerShell)

```powershell
python -m venv .venv
. .venv\Scripts\Activate.ps1
```

### 2) Install dependencies
```powershell
pip install -r requirements.txt
```

### 3) Configure environment
Copy `.env.example` to `.env` and set values.

```powershell
Copy-Item .env.example .env
```

Key variables:
- `SELENIUM_DRIVER_PATH` — path to your WebDriver executable
- `TARGET_URL` — primary page to scrape
- `DB_CONNECTION_STRING` — connection string if persisting results

## Usage
Run the main script:

```powershell
python Tender_Intelligence_Platform.py
```

Optional flags can be added in the script for headless mode, output paths, etc.

## Run the Shiny dashboard (optional)

You can use a web UI to run scans and explore results.

1) Activate venv and install deps

```powershell
. .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2) Set environment

```powershell
Copy-Item .env.example .env  # then edit OPENAI_API_KEY
```

3) Launch the app

```powershell
python app.py
```

The app will start on http://localhost:8000 by default.

## Development Notes
- Keep secrets out of source control; use `.env` only locally
- Add new sources by extending the scraping functions
- Consider adding unit tests for parsing/normalization functions

## License
MIT — see `LICENSE` for details.
