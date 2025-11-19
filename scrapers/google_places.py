"""
Google Places API scraper for retrieving company websites and contact info
"""
import logging
import googlemaps
from typing import Optional, Dict
from config.settings import GOOGLE_PLACES_API_KEY, REQUEST_TIMEOUT

logger = logging.getLogger(__name__)


class GooglePlacesScraper:
    """Scraper for Google Places API"""

    def __init__(self, api_key: str = GOOGLE_PLACES_API_KEY):
        """Initialize Google Places client"""
        if not api_key:
            logger.warning("Google Places API key not provided. This scraper will be disabled.")
            self.client = None
        else:
            self.client = googlemaps.Client(key=api_key, timeout=REQUEST_TIMEOUT)

    def search_company(self, company_name: str, address: str = "") -> Optional[Dict]:
        """
        Search for a company using Google Places API

        Args:
            company_name: Name of the company
            address: Optional address to narrow search

        Returns:
            Dictionary with company info or None if not found
        """
        if not self.client:
            logger.debug("Google Places client not initialized")
            return None

        try:
            # Build search query
            query = f"{company_name}"
            if address:
                query += f" {address}"

            # Search for place
            logger.debug(f"Searching Google Places for: {query}")
            places_result = self.client.places(query=query)

            if not places_result.get('results'):
                logger.info(f"No results found for: {company_name}")
                return None

            # Get first result (most relevant)
            place = places_result['results'][0]
            place_id = place.get('place_id')

            # Get detailed information
            details = self.client.place(place_id=place_id)
            result = details.get('result', {})

            # Extract relevant info
            company_info = {
                'name': result.get('name'),
                'website': result.get('website'),
                'phone': result.get('formatted_phone_number') or result.get('international_phone_number'),
                'address': result.get('formatted_address'),
                'rating': result.get('rating'),
                'business_status': result.get('business_status'),
                'place_id': place_id,
                'types': result.get('types', []),
                'url': result.get('url')  # Google Maps URL
            }

            logger.info(f"Found place info for {company_name}: {company_info.get('website', 'No website')}")
            return company_info

        except googlemaps.exceptions.ApiError as e:
            logger.error(f"Google Places API error for {company_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error searching for {company_name}: {e}")
            return None

    def get_website(self, company_name: str, address: str = "") -> Optional[str]:
        """
        Quick method to just get the website URL

        Args:
            company_name: Name of the company
            address: Optional address

        Returns:
            Website URL or None
        """
        company_info = self.search_company(company_name, address)
        if company_info:
            return company_info.get('website')
        return None
