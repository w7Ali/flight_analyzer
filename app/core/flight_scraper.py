import asyncio
import logging
import traceback
import random
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

from app.config import settings
from app.models.flight import FlightBase, FlightSearchParams

logger = logging.getLogger(__name__)

class FlightScraper:
    """Core class for scraping flight data from various sources"""
    
    def __init__(self, headless: bool = None, timeout: int = None):
        """Initialize the flight scraper"""
        self.headless = headless if headless is not None else settings.PLAYWRIGHT_HEADLESS
        self.timeout = timeout if timeout is not None else settings.PLAYWRIGHT_TIMEOUT
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
        ]
    
    async def _setup_browser(self):
        """Setup Playwright browser with anti-detection measures"""
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--single-process',
                '--disable-gpu'
            ]
        )
        return playwright, browser
    
    async def _create_context(self, browser):
        """Create a new browser context with realistic settings"""
        user_agent = random.choice(self.user_agents)
        context = await browser.new_context(
            user_agent=user_agent,
            viewport={'width': 1366, 'height': 768},
            locale='en-US,en',
            timezone_id='Australia/Sydney',
            permissions=['geolocation']
        )
        
        # Add stealth scripts to avoid detection
        await context.add_init_script("""
        // Overwrite the `languages` property to use a custom getter.
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en'],
        });
        
        // Overwrite the `plugins` property to use a custom getter.
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5],
        });
        
        // Pass the Webdriver test
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
        });
        
        // Mock Chrome runtime
        window.navigator.chrome = {
            runtime: {},
        };
        """)
        
        return context

    async def scrape_google_flights(self, search_params: FlightSearchParams) -> Tuple[List[Dict[str, Any]], str]:
        """
        Scrape flight data from Google Flights
        
        Args:
            search_params: Flight search parameters
            
        Returns:
            Tuple of (list of flight data, debug info)
        """
        url = self._build_google_flights_url(search_params)
        logger.info(f"Scraping Google Flights: {url}")
        
        playwright = None
        browser = None
        
        try:
            playwright, browser = await self._setup_browser()
            context = await self._create_context(browser)
            page = await context.new_page()
            
            # Set headers
            await page.set_extra_http_headers({
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Referer': 'https://www.google.com/',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            })
            
            # Block unnecessary resources
            await self._block_resources(page)
            
            # Set navigation timeout
            page.set_default_navigation_timeout(self.timeout)
            
            # Add random delay to appear more human-like
            await asyncio.sleep(random.uniform(1, 3))
            
            # Navigate to the URL
            response = await page.goto(
                url, 
                timeout=self.timeout,
                wait_until='domcontentloaded',
                referer='https://www.google.com/'
            )
            
            if not response or response.status >= 400:
                error_msg = f"Failed to load page. Status: {getattr(response, 'status', 'No response')}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            # Wait for flight results to load
            await self._wait_for_flight_results(page)
            
            # Extract flight data
            flights = await self._extract_flight_data(page)
            
            # Save debug info
            debug_info = await self._save_debug_info(page, search_params)
            
            return flights, debug_info
            
        except PlaywrightTimeoutError as e:
            error_msg = f"Scraping timed out after {self.timeout}ms: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg) from e
            
        except Exception as e:
            error_msg = f"Error scraping flight data: {str(e)}"
            logger.error(f"{error_msg}\n{traceback.format_exc()}")
            raise Exception(error_msg) from e
            
        finally:
            if browser:
                await browser.close()
            if playwright:
                await playwright.stop()
    
    def _build_google_flights_url(self, search_params: FlightSearchParams) -> str:
        """Construct a basic Google Flights URL from search parameters.

        Google Flights uses a complex encoded URL format, but the generic search
        query variant works reliably without needing the full encoding scheme.
        Example pattern:
        https://www.google.com/travel/flights?q=Flights%20from%20SYD%20to%20DXB%20on%202025-08-05
        """
        dep = search_params.departure.upper()
        dest = search_params.destination.upper()
        date = search_params.date  # already validated YYYY-MM-DD

        # Encode spaces as %20 for a simple query string.
        query = f"Flights from {dep} to {dest} on {date}".replace(" ", "%20")
        return f"https://www.google.com/travel/flights?q={query}"
    
    async def _block_resources(self, page):
        """Block unnecessary resources to speed up scraping"""
        await page.route('**/*.{jpg,jpeg,png,gif,svg,webp,woff,woff2,ttf,eot,mp4,webm,mp3}', 
            lambda route: route.abort() if route.request.resource_type in ('image', 'media', 'font') 
                           else route.continue_()
        )
    
    async def _wait_for_flight_results(self, page):
        """Wait for flight results to load"""
        # Implementation of waiting logic
        pass
    
    async def _extract_flight_data(self, page) -> List[Dict[str, Any]]:
        """Extract flight data from the page"""
        # Implementation of data extraction logic
        pass
    
    async def _save_debug_info(self, page, search_params: FlightSearchParams) -> str:
        """Save debug information (screenshots, HTML, etc.)"""
        debug_dir = settings.BASE_DIR / "debug"
        debug_dir.mkdir(exist_ok=True)
        
        # Save screenshot
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        screenshot_path = debug_dir / f"flight_results_{timestamp}.png"
        await page.screenshot(path=str(screenshot_path))
        
        # Save page content
        content = await page.content()
        content_path = debug_dir / f"page_content_{timestamp}.html"
        with open(content_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return f"Debug info saved to {debug_dir}"
