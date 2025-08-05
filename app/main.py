import logging
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from app.config import settings
from app.api.endpoints import flights, health
from app.core.gemini import GeminiAnalyzer

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger(__name__)

def create_application() -> FastAPI:
    """Create and configure the FastAPI application"""
    # Initialize FastAPI app
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="Flight data analysis and insights powered by AI",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, replace with specific origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Mount static files
    app.mount(
        "/static",
        StaticFiles(directory=settings.STATIC_DIR),
        name="static"
    )
    
    # Initialize templates
    templates = Jinja2Templates(directory=settings.TEMPLATES_DIR)
    
    # Include API routes
    app.include_router(
        flights.router,
        prefix="/api/flights",
        tags=["flights"]
    )
    
    app.include_router(
        health.router,
        prefix="/api/health",
        tags=["health"]
    )
    
    # Add startup event to initialize resources
    @app.on_event("startup")
    async def startup_event():
        """Initialize application services on startup"""
        logger.info("Starting up application...")
        # Initialize Gemini analyzer if API key is available
        if settings.GEMINI_API_KEY:
            try:
                gemini_analyzer = GeminiAnalyzer(settings.GEMINI_API_KEY)
                app.state.gemini_analyzer = gemini_analyzer
                logger.info("Gemini analyzer initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini analyzer: {str(e)}")
    
    # Root endpoint
    @app.get("/", response_class=HTMLResponse)
    async def root(request: Request):
        """Root endpoint that serves the main application page"""
        from app.api.endpoints.flights import MAJOR_AIRPORTS
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "title": settings.PROJECT_NAME,
                "version": settings.VERSION,
                "gemini_available": hasattr(app.state, 'gemini_analyzer'),
                "airports": MAJOR_AIRPORTS
            }
        )
    
    return app

# Create the application instance
app = create_application()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
