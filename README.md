# Flight Analyzer

A FastAPI-based web application for analyzing flight data with AI-powered insights using Google's Gemini AI.

## Features

- **Flight Data Scraping**: Scrape real-time flight data from various sources
- **AI-Powered Analysis**: Get insights and recommendations using Google's Gemini AI
- **Structured Data**: Clean, structured flight data in JSON and CSV formats
- **Web Interface**: User-friendly web interface for searching and analyzing flights
- **RESTful API**: Fully documented API for programmatic access

## Project Structure

```
flight_analyzer/
├── app/                      # Application package
│   ├── api/                  # API endpoints
│   │   └── endpoints/        # Route handlers
│   ├── core/                 # Core functionality
│   ├── models/               # Pydantic models
│   ├── services/             # Business logic
│   ├── static/               # Static files (CSS, JS, images)
│   └── templates/            # HTML templates
├── tests/                    # Test files
├── .env.example             # Example environment variables
├── main.py                  # Application entry point
├── requirements.txt         # Project dependencies
└── README.md                # This file
```

## Prerequisites

- Python 3.9+
- Playwright (for web scraping)
- Google Gemini API key (for AI analysis)

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/w7Ali/flight-analyzer.git
   cd flight-analyzer
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Playwright browsers**
   ```bash
   playwright install
   ```

5. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

## Configuration

Create a `.env` file in the project root with the following variables:

```env
# Application
DEBUG=True
HOST=0.0.0.0
PORT=8000
WORKERS=1
LOG_LEVEL=INFO

# Gemini AI
GEMINI_API_KEY=your_gemini_api_key

# Playwright
PLAYWRIGHT_HEADLESS=True
PLAYWRIGHT_TIMEOUT=120000
```

## Running the Application

### Development Mode

```bash
uvicorn app.main:app --reload
```

### Production Mode

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

The application will be available at `http://localhost:8000`

## API Documentation

Once the application is running, you can access:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI Schema**: `http://localhost:8000/openapi.json`

## Testing

Run the test suite with:

```bash
pytest
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request
