import logging
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime, timedelta
import pandas as pd
import traceback

from app.config import settings
from app.models.flight import FlightSearchParams, FlightResponse, FlightBase
from app.models.analysis import AnalysisRequest, AnalysisResponse
from app.core.flight_scraper import FlightScraper
from app.core.gemini import GeminiAnalyzer

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()

# List of major airports for the dropdown
MAJOR_AIRPORTS = [
    {"code": "SYD", "name": "Sydney Airport", "city": "Sydney", "country": "Australia"},
    {"code": "MEL", "name": "Melbourne Airport", "city": "Melbourne", "country": "Australia"},
    {"code": "BNE", "name": "Brisbane Airport", "city": "Brisbane", "country": "Australia"},
    {"code": "ADL", "name": "Adelaide Airport", "city": "Adelaide", "country": "Australia"},
    {"code": "PER", "name": "Perth Airport", "city": "Perth", "country": "Australia"},
    {"code": "LAX", "name": "Los Angeles International", "city": "Los Angeles", "country": "USA"},
    {"code": "JFK", "name": "John F. Kennedy International", "city": "New York", "country": "USA"},
    {"code": "LHR", "name": "Heathrow Airport", "city": "London", "country": "UK"},
    {"code": "CDG", "name": "Charles de Gaulle", "city": "Paris", "country": "France"},
    {"code": "DXB", "name": "Dubai International", "city": "Dubai", "country": "UAE"}
]

@router.get("/airports", response_model=List[Dict[str, str]])
async def get_airports():
    """Get list of major airports"""
    return MAJOR_AIRPORTS



from fastapi import Body, Query, Form

@router.post("/search", response_model=FlightResponse)
async def search_flights(
    params: Optional[FlightSearchParams] = Body(None),
    departure: Optional[str] = Form(None),
    destination: Optional[str] = Form(None),
    date: Optional[str] = Form(None)
):
    """Search for flights between two locations on a specific date (JSON or form)."""
    # Determine source of params
    if params is None:
        if not (departure and destination and date):
            raise HTTPException(status_code=422, detail="Missing required flight search parameters")
        params = FlightSearchParams(departure=departure, destination=destination, date=date)
    """Search for flights between two locations on a specific date"""

    """
    Search for flights between two locations on a specific date
    
    Args:
        params: Flight search parameters
        
    Returns:
        FlightResponse with list of flights and metadata
    """
    try:
        logger.info(f"Searching flights: {params.departure} -> {params.destination} on {params.date}")
        
        # Initialize flight scraper
        scraper = FlightScraper()
        
        # Scrape flight data
        flights_data, debug_info = await scraper.scrape_google_flights(params)
        
        if not flights_data:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"detail": "No flights found for the specified criteria"}
            )
        
        # Convert to FlightBase models
        flights = [FlightBase(**flight) for flight in flights_data]
        
        return {
            "success": True,
            "data": flights,
            "total": len(flights),
            "page": 1,
            "size": len(flights),
            "message": f"Found {len(flights)} flights"
        }
        
    except Exception as e:
        logger.error(f"Error searching flights: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching flights: {str(e)}"
        )

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_flights(
    request: Request,
    analysis_request: AnalysisRequest,
    use_ai: bool = True
):
    """
    Analyze flight data with optional AI-powered insights
    
    Args:
        analysis_request: Flight data to analyze
        use_ai: Whether to use Gemini AI for analysis
        
    Returns:
        AnalysisResponse with insights and enhanced data
    """
    try:
        logger.info(f"Analyzing {len(analysis_request.flights)} flights (AI: {use_ai})")
        
        if not analysis_request.flights:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No flight data provided for analysis"
            )
        
        response = None
        
        # Use Gemini for AI-powered analysis if available and requested
        if use_ai and hasattr(request.app.state, 'gemini_analyzer'):
            try:
                response = await request.app.state.gemini_analyzer.analyze_flights(
                    analysis_request.flights
                )
                
                # Save analysis results to files
                file_paths = request.app.state.gemini_analyzer.save_analysis_to_files(response)
                logger.info(f"Analysis results saved to {file_paths}")
                
                # Add file paths to response
                if response.enhanced_data:
                    response.metrics["analysis_files"] = file_paths
                
            except Exception as e:
                logger.error(f"AI analysis failed: {str(e)}\n{traceback.format_exc()}")
                if not response:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="AI analysis service is currently unavailable"
                    )
        
        # Fallback to basic analysis if AI is not available or failed
        if not response:
            response = await _perform_basic_analysis(analysis_request.flights)
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing flights: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing flights: {str(e)}"
        )

async def _perform_basic_analysis(flights: List[Dict[str, Any]]) -> AnalysisResponse:
    """Perform basic flight analysis without AI"""
    import pandas as pd
    
    df = pd.DataFrame(flights)
    
    # Basic metrics
    price_stats = {
        'min': float(df['price'].min()),
        'max': float(df['price'].max()),
        'average': float(df['price'].mean()),
        'median': float(df['price'].median())
    }
    
    # Basic insights
    cheapest = df.loc[df['price'].idxmin()].to_dict()
    fastest = df.loc[df['duration_minutes'].idxmin()].to_dict() if 'duration_minutes' in df.columns else {}
    
    insights = {
        'summary': 'Basic flight analysis (AI not available)',
        'key_findings': [
            f"Found {len(df)} flights with prices from ${price_stats['min']:.2f} to ${price_stats['max']:.2f}",
            f"Average price: ${price_stats['average']:.2f}",
        ],
        'price_analysis': {
            'overall': price_stats
        },
        'airline_comparison': [],
        'best_value_flights': [],
        'cheapest_flights': [cheapest] if cheapest else [],
        'fastest_flights': [fastest] if fastest else [],
        'booking_recommendations': [
            "Consider booking in advance for better prices",
            "Check multiple airlines for the best deals"
        ]
    }
    
    return AnalysisResponse(
        success=True,
        insights=FlightInsights(**insights),
        enhanced_data=flights,
        metrics={
            'total_flights_analyzed': len(df),
            'price_range': {'min': price_stats['min'], 'max': price_stats['max'], 'average': price_stats['average']},
            'note': 'Basic analysis performed (AI not available)'
        }
    )

# Web interface endpoints
@router.get("/search-form", response_class=HTMLResponse)
async def search_form(request: Request):
    """Render the flight search form"""
    templates = settings.TEMPLATES_DIR
    return templates.TemplateResponse(
        "search.html",
        {
            "request": request,
            "airports": MAJOR_AIRPORTS,
            "default_date": (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        }
    )

@router.get("/results", response_class=HTMLResponse)
async def results_page(
    request: Request,
    departure: str,
    destination: str,
    date: str,
    use_ai: bool = True
):
    """Render the flight results page"""
    templates = settings.TEMPLATES_DIR
    
    try:
        # Search for flights
        search_params = FlightSearchParams(
            departure=departure,
            destination=destination,
            date=date
        )
        
        # Get flight data
        flight_data = await search_flights(search_params)
        
        # Analyze flights
        analysis_request = AnalysisRequest(flights=flight_data["data"])
        analysis = await analyze_flights(request, analysis_request, use_ai=use_ai)
        
        return templates.TemplateResponse(
            "results.html",
            {
                "request": request,
                "flights": flight_data["data"],
                "analysis": analysis.dict(),
                "search_params": search_params.dict(),
                "use_ai": use_ai
            }
        )
        
    except HTTPException as e:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error": str(e.detail),
                "status_code": e.status_code
            },
            status_code=e.status_code
        )
    except Exception as e:
        logger.error(f"Error in results page: {str(e)}\n{traceback.format_exc()}")
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error": "An unexpected error occurred",
                "status_code": 500
            },
            status_code=500
        )
