from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime

class FlightBase(BaseModel):
    """Base model for flight data"""
    airline: str
    flight_number: Optional[str] = None
    departure_airport: str
    arrival_airport: str
    departure_time: str
    arrival_time: str
    duration: str
    duration_minutes: Optional[int] = None
    price: float
    stops: int = 0
    aircraft: Optional[str] = None
    cabin_class: Optional[str] = "Economy"
    source: Optional[str] = "scraper"

class FlightCreate(FlightBase):
    """Model for creating new flight records"""
    pass

class FlightUpdate(BaseModel):
    """Model for updating flight records"""
    price: Optional[float] = None
    departure_time: Optional[str] = None
    arrival_time: Optional[str] = None
    status: Optional[str] = None

class FlightInDB(FlightBase):
    """Database model for flights"""
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class FlightSearchParams(BaseModel):
    """Parameters for searching flights"""
    departure: str = Field(..., description="IATA code of departure airport")
    destination: str = Field(..., description="IATA code of destination airport")
    date: str = Field(..., description="Departure date in YYYY-MM-DD format")

    @field_validator('date')
    @classmethod
    def validate_date_format(cls, v):
        try:
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format")
        return v

class FlightResponse(BaseModel):
    """Response model for flight data"""
    success: bool
    data: List[FlightInDB]
    total: int
    page: int = 1
    size: int = 10
    message: Optional[str] = None
