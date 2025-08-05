import os
import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import google.generativeai as genai
from pathlib import Path

from app.config import settings
from app.models.analysis import AnalysisRequest, AnalysisResponse, FlightInsights, PriceAnalysis, AirlineAnalysis, FlightRecommendation

logger = logging.getLogger(__name__)

class GeminiAnalyzer:
    """Class for analyzing flight data using Google's Gemini AI"""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Gemini analyzer with an optional API key"""
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = None
        
        if self.api_key:
            self._initialize_model()
    
    def _initialize_model(self):
        """Initialize the Gemini model with the API key"""
        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-pro')
            logger.info("Successfully initialized Gemini model")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini model: {str(e)}")
            raise
    
    async def analyze_flights(self, flights: List[Dict[str, Any]], **kwargs) -> AnalysisResponse:
        """
        Analyze flight data using Gemini AI
        
        Args:
            flights: List of flight dictionaries to analyze
            **kwargs: Additional parameters for the analysis
            
        Returns:
            AnalysisResponse with insights and enhanced data
        """
        if not self.model:
            raise ValueError("Gemini model not initialized. Please provide a valid API key.")
        
        try:
            # Prepare the analysis request
            analysis_request = AnalysisRequest(flights=flights, **kwargs)
            
            # Generate the prompt for Gemini
            prompt = self._create_analysis_prompt(analysis_request)
            
            # Get response from Gemini
            logger.info("Sending request to Gemini for flight analysis...")
            response = await self.model.generate_content_async(prompt)
            
            # Process the response
            return self._process_gemini_response(response.text, analysis_request)
            
        except Exception as e:
            logger.error(f"Error analyzing flights with Gemini: {str(e)}")
            raise
    
    def _create_analysis_prompt(self, request: AnalysisRequest) -> str:
        """Create a detailed prompt for Gemini based on the analysis request"""
        prompt = """You are a senior data analyst specializing in flight data. Your task is to analyze the following flight data and provide comprehensive insights and structured output.

        FLIGHT DATA TO ANALYZE:
        {data_summary}

        REQUIRED ANALYSIS:
        1. Data Enhancement:
           - Add 'value_score' (0-100) based on price, duration, and stops
           - Add 'recommendation' column: 'Best Value', 'Good Option', or 'Consider Alternatives'
           - Add 'departure_time' and 'arrival_time' if not present
           - Calculate 'price_per_hour' for better comparison
        
        2. Trend Analysis:
           - Price trends by airline
           - Duration vs. Price correlation
           - Stop patterns and their impact on price
           - Best time to book for this route
        
        3. Key Insights:
           - Top 3 best value flights
           - Cheapest vs. fastest options
           - Any price anomalies or outliers
           - Airline performance comparison
        
        4. Traveler Recommendations:
           - Best time to book
           - Airline recommendations
           - Price vs. convenience trade-offs
        
        RETURN FORMAT (JSON):
        {{
            "insights": {{
                "summary": "Overall summary of the flight options",
                "key_findings": ["Key finding 1", "Key finding 2", ...],
                "price_analysis": {{
                    "overall": {{"min": 0, "max": 0, "average": 0, "median": 0}},
                    "by_airline": {{"airline1": {{"min": 0, "max": 0, "average": 0, "median": 0}}}}
                }},
                "airline_comparison": [
                    {{
                        "airline": "Airline Name",
                        "average_price": 0,
                        "average_duration": "0h 0m",
                        "average_value_score": 0,
                        "total_flights": 0,
                        "recommendation": "Recommended/Neutral/Not Recommended"
                    }}
                ],
                "best_value_flights": [],
                "cheapest_flights": [],
                "fastest_flights": [],
                "booking_recommendations": ["Recommendation 1", "Recommendation 2", ...]
            }},
            "enhanced_data": [
                {{
                    "airline": "Airline name",
                    "flight_number": "AB123",
                    "departure_airport": "XXX",
                    "arrival_airport": "YYY",
                    "departure_time": "HH:MM",
                    "arrival_time": "HH:MM",
                    "duration": "Xh Ym",
                    "duration_minutes": 0,
                    "price": 0.0,
                    "price_per_hour": 0.0,
                    "stops": 0,
                    "aircraft": "Boeing 737",
                    "value_score": 0-100,
                    "recommendation": "Best Value/Good Option/Consider Alternatives",
                    "notes": "Any additional notes about this flight"
                }}
            ],
            "metrics": {{
                "total_flights_analyzed": 0,
                "price_range": {{"min": 0, "max": 0, "average": 0}},
                "duration_range": {{"min": "0h 0m", "max": "0h 0m", "average": "0h 0m"}},
                "best_value_flight": {{"airline": "", "price": 0, "duration": ""}},
                "cheapest_flight": {{"airline": "", "price": 0, "duration": ""}},
                "fastest_flight": {{"airline": "", "price": 0, "duration": ""}}
            }}
        }}
        """
        
        # Convert flight data to a clean string representation
        data_summary = "\n".join(
            f"{i+1}. {flight.get('airline', 'Unknown')} - "
            f"${flight.get('price', 0):.2f} - "
            f"{flight.get('duration', 'N/A')} - "
            f"{flight.get('stops', 0)} stops"
            for i, flight in enumerate(request.flights[:10])  # Limit to first 10 flights for the prompt
        )
        
        if len(request.flights) > 10:
            data_summary += f"\n... and {len(request.flights) - 10} more flights"
        
        return prompt.format(data_summary=data_summary)
    
    def _process_gemini_response(self, response_text: str, request: AnalysisRequest) -> AnalysisResponse:
        """Process the response from Gemini and convert it to structured data"""
        try:
            # Try to parse the JSON response
            result = json.loads(response_text)
            
            # Extract insights and enhanced data
            insights_data = result.get('insights', {})
            enhanced_data = result.get('enhanced_data', [])
            metrics = result.get('metrics', {})
            
            # Convert to Pydantic models
            insights = FlightInsights(
                summary=insights_data.get('summary', ''),
                key_findings=insights_data.get('key_findings', []),
                price_analysis={
                    k: PriceAnalysis(**v) 
                    for k, v in insights_data.get('price_analysis', {}).items()
                },
                airline_comparison=[
                    AirlineAnalysis(**airline) 
                    for airline in insights_data.get('airline_comparison', [])
                ],
                best_value_flights=[
                    FlightRecommendation(**flight) 
                    for flight in insights_data.get('best_value_flights', [])
                ],
                cheapest_flights=[
                    FlightRecommendation(**flight) 
                    for flight in insights_data.get('cheapest_flights', [])
                ],
                fastest_flights=[
                    FlightRecommendation(**flight) 
                    for flight in insights_data.get('fastest_flights', [])
                ],
                booking_recommendations=insights_data.get('booking_recommendations', [])
            )
            
            return AnalysisResponse(
                success=True,
                insights=insights,
                enhanced_data=enhanced_data,
                metrics=metrics
            )
            
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse Gemini response as JSON: {str(e)}"
            logger.error(f"{error_msg}\nResponse: {response_text[:500]}...")
            raise ValueError(error_msg) from e
        except Exception as e:
            error_msg = f"Error processing Gemini response: {str(e)}"
            logger.error(f"{error_msg}\n{traceback.format_exc()}")
            raise ValueError(error_msg) from e
    
    def save_analysis_to_files(self, response: AnalysisResponse, output_dir: Path = None) -> Dict[str, str]:
        """Save analysis results to files"""
        if output_dir is None:
            output_dir = settings.BASE_DIR / "analysis_results"
            output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save enhanced data to CSV
        csv_path = output_dir / f"enhanced_flights_{timestamp}.csv"
        enhanced_df = pd.DataFrame(response.enhanced_data)
        enhanced_df.to_csv(csv_path, index=False)
        
        # Save insights to markdown
        md_path = output_dir / f"flight_insights_{timestamp}.md"
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(f"# Flight Analysis Insights\n\n")
            f.write(f"*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
            
            # Summary
            f.write("## Summary\n\n")
            f.write(f"{response.insights.summary}\n\n")
            
            # Key Findings
            if response.insights.key_findings:
                f.write("## Key Findings\n\n")
                for finding in response.insights.key_findings:
                    f.write(f"- {finding}\n")
                f.write("\n")
            
            # Price Analysis
            f.write("## Price Analysis\n\n")
            if 'overall' in response.insights.price_analysis:
                price = response.insights.price_analysis['overall']
                f.write(f"- **Price Range:** ${price.min:.2f} - ${price.max:.2f}\n")
                f.write(f"- **Average Price:** ${price.average:.2f}\n")
                f.write(f"- **Median Price:** ${price.median:.2f}\n\n")
            
            # Airline Comparison
            if response.insights.airline_comparison:
                f.write("## Airline Comparison\n\n")
                for airline in response.insights.airline_comparison:
                    f.write(f"### {airline.airline}\n")
                    f.write(f"- **Avg. Price:** ${airline.average_price:.2f}\n")
                    f.write(f"- **Avg. Duration:** {airline.average_duration}\n")
                    f.write(f"- **Value Score:** {airline.average_value_score:.1f}/100\n")
                    f.write(f"- **Recommendation:** {airline.recommendation}\n\n")
            
            # Recommendations
            if response.insights.booking_recommendations:
                f.write("## Booking Recommendations\n\n")
                for i, rec in enumerate(response.insights.booking_recommendations, 1):
                    f.write(f"{i}. {rec}\n")
                f.write("\n")
        
        return {
            'csv_path': str(csv_path.absolute()),
            'markdown_path': str(md_path.absolute())
        }
