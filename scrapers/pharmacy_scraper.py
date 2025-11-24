"""
Pharmacy scraper using Google Places API to find pharmacies in a specific geographic area
"""
import logging
import googlemaps
from typing import List, Dict, Optional
from config.settings import GOOGLE_PLACES_API_KEY, REQUEST_TIMEOUT

logger = logging.getLogger(__name__)


class PharmacyScraper:
    """Scraper for finding pharmacies in a geographic area using Google Places API"""

    def __init__(self, api_key: str = GOOGLE_PLACES_API_KEY):
        """Initialize Google Places client"""
        if not api_key:
            logger.warning("Google Places API key not provided. This scraper will be disabled.")
            self.client = None
        else:
            self.client = googlemaps.Client(key=api_key, timeout=REQUEST_TIMEOUT)

    def _is_within_bounds(
        self,
        lat: Optional[float],
        lng: Optional[float],
        bounds: Optional[Dict[str, float]]
    ) -> bool:
        """
        Check if coordinates are within specified bounds

        Args:
            lat: Latitude
            lng: Longitude
            bounds: Dictionary with 'north', 'south', 'east', 'west' coordinates

        Returns:
            True if within bounds, False otherwise (or True if bounds not provided)
        """
        if not bounds or lat is None or lng is None:
            return True  # No bounds specified or missing coordinates

        return (
            bounds['south'] <= lat <= bounds['north'] and
            bounds['west'] <= lng <= bounds['east']
        )

    def search_pharmacies_in_area(
        self,
        center_lat: float,
        center_lng: float,
        radius_meters: int = 1000,
        keyword: str = "pharmacy",
        bounds: Optional[Dict[str, float]] = None
    ) -> List[Dict]:
        """
        Search for pharmacies near a center point

        Args:
            center_lat: Latitude of center point
            center_lng: Longitude of center point
            radius_meters: Search radius in meters
            keyword: Search keyword (default: "pharmacy")
            bounds: Optional dictionary with 'north', 'south', 'east', 'west' to filter results

        Returns:
            List of pharmacy dictionaries with details (filtered by bounds if provided)
        """
        if not self.client:
            logger.error("Google Places client not initialized")
            return []

        pharmacies = []

        try:
            # Use nearby search for pharmacies
            location = (center_lat, center_lng)

            logger.info(f"Searching for pharmacies near ({center_lat}, {center_lng}) within {radius_meters}m")

            # Initial search
            results = self.client.places_nearby(
                location=location,
                radius=radius_meters,
                keyword=keyword,
                type='pharmacy'
            )

            # Process results
            pharmacies.extend(self._process_results(results.get('results', []), bounds))

            # Handle pagination - get more results if available
            while results.get('next_page_token'):
                import time
                time.sleep(2)  # Required delay before using next_page_token

                results = self.client.places_nearby(
                    location=location,
                    radius=radius_meters,
                    page_token=results['next_page_token']
                )
                pharmacies.extend(self._process_results(results.get('results', []), bounds))

            # Filter by bounds if provided (in case _process_results didn't have coordinates yet)
            if bounds:
                filtered_pharmacies = []
                for pharmacy in pharmacies:
                    if self._is_within_bounds(
                        pharmacy.get('latitude'),
                        pharmacy.get('longitude'),
                        bounds
                    ):
                        filtered_pharmacies.append(pharmacy)
                pharmacies = filtered_pharmacies
                logger.info(f"Filtered to {len(pharmacies)} pharmacies within bounds")

            logger.info(f"Found {len(pharmacies)} pharmacies")
            return pharmacies

        except googlemaps.exceptions.ApiError as e:
            logger.error(f"Google Places API error: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error searching for pharmacies: {e}")
            return []

    def search_pharmacies_text(
        self,
        query: str,
        location_bias: Optional[tuple] = None,
        bounds: Optional[Dict[str, float]] = None
    ) -> List[Dict]:
        """
        Search for pharmacies using text search

        Args:
            query: Search query (e.g., "pharmacies in Chelsea Manhattan")
            location_bias: Optional (lat, lng) to bias results
            bounds: Optional dictionary with 'north', 'south', 'east', 'west' to filter results

        Returns:
            List of pharmacy dictionaries (filtered by bounds if provided)
        """
        if not self.client:
            logger.error("Google Places client not initialized")
            return []

        pharmacies = []

        try:
            logger.info(f"Text search for: {query}")

            # Text search
            if location_bias:
                results = self.client.places(
                    query=query,
                    location=location_bias,
                    radius=2000
                )
            else:
                results = self.client.places(query=query)

            pharmacies.extend(self._process_results(results.get('results', []), bounds))

            # Handle pagination
            while results.get('next_page_token'):
                import time
                time.sleep(2)

                results = self.client.places(
                    query=query,
                    page_token=results['next_page_token']
                )
                pharmacies.extend(self._process_results(results.get('results', []), bounds))

            # Filter by bounds if provided
            if bounds:
                filtered_pharmacies = []
                for pharmacy in pharmacies:
                    if self._is_within_bounds(
                        pharmacy.get('latitude'),
                        pharmacy.get('longitude'),
                        bounds
                    ):
                        filtered_pharmacies.append(pharmacy)
                pharmacies = filtered_pharmacies
                logger.info(f"Filtered to {len(pharmacies)} pharmacies within bounds")

            logger.info(f"Found {len(pharmacies)} pharmacies via text search")
            return pharmacies

        except Exception as e:
            logger.error(f"Error in text search: {e}")
            return []

    def _process_results(
        self,
        results: List[Dict],
        bounds: Optional[Dict[str, float]] = None
    ) -> List[Dict]:
        """
        Process raw Google Places results and get detailed info

        Args:
            results: List of place results from API
            bounds: Optional dictionary with 'north', 'south', 'east', 'west' to filter results

        Returns:
            List of processed pharmacy dictionaries (filtered by bounds if provided)
        """
        pharmacies = []

        for place in results:
            place_id = place.get('place_id')
            
            # Early bounds check using initial geometry (before API call for details)
            if bounds:
                initial_lat = place.get('geometry', {}).get('location', {}).get('lat')
                initial_lng = place.get('geometry', {}).get('location', {}).get('lng')
                if not self._is_within_bounds(initial_lat, initial_lng, bounds):
                    logger.debug(f"Skipping {place.get('name', place_id)} - outside bounds")
                    continue

            try:
                # Get detailed information
                details = self.client.place(
                    place_id=place_id,
                    fields=[
                        'name', 'formatted_address', 'formatted_phone_number',
                        'website', 'url', 'rating', 'user_ratings_total',
                        'opening_hours', 'business_status', 'geometry',
                        'type', 'price_level'
                    ]
                )

                result = details.get('result', {})

                pharmacy = {
                    'name': result.get('name'),
                    'address': result.get('formatted_address'),
                    'phone': result.get('formatted_phone_number'),
                    'website': result.get('website'),
                    'google_maps_url': result.get('url'),
                    'rating': result.get('rating'),
                    'total_ratings': result.get('user_ratings_total'),
                    'business_status': result.get('business_status'),
                    'place_id': place_id,
                    'latitude': result.get('geometry', {}).get('location', {}).get('lat'),
                    'longitude': result.get('geometry', {}).get('location', {}).get('lng'),
                    'types': ', '.join(result.get('type', result.get('types', []))),
                }
                
                # Final bounds check with detailed coordinates
                if bounds and not self._is_within_bounds(
                    pharmacy.get('latitude'),
                    pharmacy.get('longitude'),
                    bounds
                ):
                    logger.debug(f"Skipping {pharmacy['name']} - outside bounds after details")
                    continue

                # Extract opening hours if available
                opening_hours = result.get('opening_hours', {})
                if opening_hours:
                    pharmacy['is_open_now'] = opening_hours.get('open_now')
                    weekday_text = opening_hours.get('weekday_text', [])
                    pharmacy['hours'] = ' | '.join(weekday_text) if weekday_text else None
                else:
                    pharmacy['is_open_now'] = None
                    pharmacy['hours'] = None

                pharmacies.append(pharmacy)
                logger.debug(f"Processed: {pharmacy['name']}")

            except Exception as e:
                logger.warning(f"Error getting details for place {place_id}: {e}")
                # Add basic info even if details fail
                pharmacies.append({
                    'name': place.get('name'),
                    'address': place.get('vicinity'),
                    'place_id': place_id,
                    'rating': place.get('rating'),
                    'phone': None,
                    'website': None,
                    'google_maps_url': None,
                    'total_ratings': place.get('user_ratings_total'),
                    'business_status': place.get('business_status'),
                    'latitude': place.get('geometry', {}).get('location', {}).get('lat'),
                    'longitude': place.get('geometry', {}).get('location', {}).get('lng'),
                    'types': ', '.join(place.get('types', [])),
                    'is_open_now': None,
                    'hours': None
                })

        return pharmacies

    def search_area_grid(
        self,
        bounds: Dict[str, float],
        grid_size: int = 3,
        keyword: str = "pharmacy"
    ) -> List[Dict]:
        """
        Search an area using a grid pattern to ensure full coverage

        Args:
            bounds: Dictionary with 'north', 'south', 'east', 'west' coordinates
            grid_size: Number of grid points per dimension
            keyword: Search keyword

        Returns:
            Deduplicated list of pharmacies found (all within bounds)
        """
        if not self.client:
            return []

        all_pharmacies = {}

        # Calculate grid points
        lat_step = (bounds['north'] - bounds['south']) / grid_size
        lng_step = (bounds['east'] - bounds['west']) / grid_size

        # Calculate radius to cover each grid cell (with overlap)
        # Using the diagonal of a grid cell as diameter
        import math
        cell_diagonal_km = math.sqrt(lat_step**2 + lng_step**2) * 111  # ~111km per degree
        radius_meters = int(cell_diagonal_km * 1000 / 2 * 1.5)  # 1.5x for overlap

        logger.info(f"Searching {grid_size}x{grid_size} grid with {radius_meters}m radius per point")
        logger.info(f"Boundaries: N={bounds['north']}, S={bounds['south']}, E={bounds['east']}, W={bounds['west']}")

        for i in range(grid_size):
            for j in range(grid_size):
                center_lat = bounds['south'] + (i + 0.5) * lat_step
                center_lng = bounds['west'] + (j + 0.5) * lng_step

                pharmacies = self.search_pharmacies_in_area(
                    center_lat=center_lat,
                    center_lng=center_lng,
                    radius_meters=radius_meters,
                    keyword=keyword,
                    bounds=bounds  # Pass bounds to filter results early
                )

                # Deduplicate by place_id
                for pharmacy in pharmacies:
                    place_id = pharmacy.get('place_id')
                    if place_id and place_id not in all_pharmacies:
                        all_pharmacies[place_id] = pharmacy

        result = list(all_pharmacies.values())
        logger.info(f"Total unique pharmacies found within bounds: {len(result)}")
        return result
