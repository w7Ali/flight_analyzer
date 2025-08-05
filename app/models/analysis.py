from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum

class RecommendationType(str, Enum):
    BEST_VALUE = "Best Value"
    GOOD_OPTION = "Good Option"
    CONSIDER_ALTERNATIVES = "Consider Alternatives"

class FlightRecommendation(BaseModel):
    """Model for flight recommendations"""
    airline: str
    flight_number: Optional[str]
    price: float
    duration: str
    departure_time: str
    arrival_time: str
    stops: int
    recommendation_type: RecommendationType
    value_score: float = Field(..., ge=0, le=100)
    notes: Optional[str] = None

class PriceAnalysis(BaseModel):
    """Model for price analysis"""
    min: float
    max: float
    average: float
    median: float
    currency: str = "USD"

class AirlineAnalysis(BaseModel):
    """Model for airline-specific analysis"""
    airline: str
    average_price: float
    average_duration: str
    average_value_score: float
    total_flights: int
    recommendation: str
    best_flight: Optional[Dict[str, Any]] = None

class FlightInsights(BaseModel):
    """Model for flight insights"""
    summary: str
    key_findings: List[str]
    price_analysis: Dict[str, PriceAnalysis]
    airline_comparison: List[AirlineAnalysis]
    best_value_flights: List[FlightRecommendation]
    cheapest_flights: List[FlightRecommendation]
    fastest_flights: List[FlightRecommendation]
    booking_recommendations: List[str]
    generated_at: datetime = Field(default_factory=datetime.utcnow)

class AnalysisRequest(BaseModel):
    """Request model for flight analysis"""
    flights: List[Dict[str, Any]]
    include_trends: bool = True
    include_airline_analysis: bool = True
    include_recommendations: bool = True

class AnalysisResponse(BaseModel):
    """Response model for flight analysis"""
    success: bool
    insights: FlightInsights
    enhanced_data: List[Dict[str, Any]]
    metrics: Dict[str, Any]
    message: Optional[str] = None
