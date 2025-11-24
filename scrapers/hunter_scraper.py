"""
Hunter.io API scraper for retrieving company size and employee information
Also includes LinkedIn company page scraping as fallback
"""
import logging
import requests
import json
import re
from typing import Optional, Dict
from urllib.parse import urlparse
from openai import OpenAI
from config.settings import HUNTER_API_KEY, REQUEST_TIMEOUT, OPENAI_API_KEY, OPENAI_MODEL, OPENAI_TEMPERATURE

logger = logging.getLogger(__name__)

# Try to import playwright for JS rendering
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright not available for LinkedIn scraping")


class HunterScraper:
    """Scraper for Hunter.io API to get company information"""

    def __init__(self, api_key: str = HUNTER_API_KEY):
        """Initialize Hunter.io client"""
        self.api_key = api_key
        self.base_url = "https://api.hunter.io/v2"
        self._playwright = None
        self._browser = None

        # Initialize OpenAI client for LLM parsing
        if OPENAI_API_KEY:
            self.openai_client = OpenAI(api_key=OPENAI_API_KEY)
        else:
            self.openai_client = None

        if not api_key:
            logger.warning("Hunter API key not provided. Will use LinkedIn fallback for company size.")

    def _get_browser(self):
        """Get or create Playwright browser instance"""
        if not PLAYWRIGHT_AVAILABLE:
            return None
        if self._browser is None:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=True)
        return self._browser

    def close(self):
        """Close browser resources"""
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()

    def get_company_info(self, website: str) -> Optional[Dict]:
        """
        Get company information including employee count from Hunter.io

        Args:
            website: Company website URL

        Returns:
            Dictionary with company info or None if not found
        """
        if not self.api_key:
            logger.debug("Hunter API key not configured")
            return None

        if not website:
            return None

        try:
            # Extract domain from website URL
            domain = self._extract_domain(website)
            if not domain:
                logger.debug(f"Could not extract domain from: {website}")
                return None

            # Call Hunter.io Domain Search API
            url = f"{self.base_url}/domain-search"
            params = {
                'domain': domain,
                'api_key': self.api_key
            }

            logger.debug(f"Querying Hunter.io for domain: {domain}")
            response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)

            if response.status_code == 401:
                logger.error("Hunter API key is invalid")
                return None
            elif response.status_code == 429:
                logger.warning("Hunter API rate limit exceeded")
                return None
            elif response.status_code != 200:
                logger.debug(f"Hunter API returned status {response.status_code} for {domain}")
                return None

            data = response.json()

            if data.get('errors'):
                logger.debug(f"Hunter API error: {data['errors']}")
                return None

            # Extract company data
            company_data = data.get('data', {})

            # Map employee count to size ranges
            organization = company_data.get('organization')
            company_size = None

            if organization:
                # Hunter.io returns organization info with headcount
                headcount = organization.get('headcount')
                if headcount:
                    company_size = self._map_headcount_to_range(headcount)

            # Also check for 'company' field in some responses
            if not company_size:
                headcount = company_data.get('headcount')
                if headcount:
                    company_size = self._map_headcount_to_range(headcount)

            result = {
                'domain': domain,
                'company_size': company_size,
                'company_type': organization.get('industry') if organization else None,
                'organization_name': organization.get('name') if organization else None,
            }

            if company_size:
                logger.info(f"✓ Found company size for {domain}: {company_size}")
            else:
                logger.debug(f"No company size found for {domain}")

            return result

        except requests.exceptions.Timeout:
            logger.warning(f"Timeout querying Hunter.io for {website}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error querying Hunter.io: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error querying Hunter.io for {website}: {e}")
            return None

    def _extract_domain(self, url: str) -> Optional[str]:
        """
        Extract domain from URL

        Args:
            url: Full URL

        Returns:
            Domain string or None
        """
        try:
            # Add scheme if missing
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url

            parsed = urlparse(url)
            domain = parsed.netloc

            # Remove www. prefix
            if domain.startswith('www.'):
                domain = domain[4:]

            return domain if domain else None
        except Exception:
            return None

    def _map_headcount_to_range(self, headcount) -> str:
        """
        Map headcount number or range to standardized size categories

        Args:
            headcount: Employee count (can be int, string, or range string)

        Returns:
            Standardized size range string
        """
        try:
            # Handle string ranges like "11-50" or "1-10"
            if isinstance(headcount, str):
                if '-' in headcount:
                    # Parse range and use upper bound
                    parts = headcount.split('-')
                    count = int(parts[1].replace(',', '').replace('+', '').strip())
                elif '+' in headcount:
                    count = int(headcount.replace(',', '').replace('+', '').strip())
                else:
                    count = int(headcount.replace(',', '').strip())
            else:
                count = int(headcount)

            # Map to ranges
            if count <= 10:
                return "1-10"
            elif count <= 50:
                return "11-50"
            elif count <= 200:
                return "51-200"
            elif count <= 500:
                return "201-500"
            elif count <= 1000:
                return "501-1000"
            else:
                return "1001+"

        except (ValueError, TypeError):
            # If we can't parse, return the original if it's a string
            if isinstance(headcount, str):
                return headcount
            return None

    def get_company_size_from_linkedin(self, linkedin_url: str) -> Optional[Dict]:
        """
        Get company size from LinkedIn company About page using Playwright + LLM

        Args:
            linkedin_url: LinkedIn company URL (e.g., https://www.linkedin.com/company/company-name/)

        Returns:
            Dictionary with company_size and company_type or None if failed
        """
        if not linkedin_url:
            return None

        if not PLAYWRIGHT_AVAILABLE:
            logger.warning("Playwright not available for LinkedIn scraping")
            return None

        if not self.openai_client:
            logger.warning("OpenAI client not available for LinkedIn parsing")
            return None

        # Ensure we're hitting the About page
        if '/about' not in linkedin_url:
            # Clean up URL and add /about
            linkedin_url = linkedin_url.rstrip('/')
            linkedin_url = linkedin_url + '/about/'

        try:
            logger.info(f"Fetching LinkedIn company page: {linkedin_url}")
            browser = self._get_browser()
            if not browser:
                return None

            page = browser.new_page()

            # Set a realistic user agent
            page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })

            # Navigate to LinkedIn page
            page.goto(linkedin_url, timeout=15000, wait_until='domcontentloaded')

            # Wait a bit for dynamic content but don't wait for full network idle
            # LinkedIn pages can take forever to fully load
            import time
            time.sleep(2)

            # Get page content
            html = page.content()
            page.close()

            # Check if we hit an auth wall
            if 'authwall' in html.lower() or 'join now' in html.lower():
                logger.warning("LinkedIn auth wall detected - cannot access company data without login")
                return None

            if not html or len(html) < 1000:
                logger.warning(f"LinkedIn page returned minimal content - may be blocked")
                return None

            # Use LLM to extract company size from the page
            result = self._parse_linkedin_with_llm(html)

            if result and result.get('company_size'):
                logger.info(f"✓ Found company size from LinkedIn: {result['company_size']}")
            else:
                logger.debug("No company size found on LinkedIn page")

            return result

        except Exception as e:
            logger.warning(f"Failed to fetch LinkedIn page: {e}")
            return None

    def _parse_linkedin_with_llm(self, html: str) -> Optional[Dict]:
        """
        Parse LinkedIn company page HTML with LLM to extract company size

        Args:
            html: HTML content of LinkedIn company About page

        Returns:
            Dictionary with company_size and company_type
        """
        if not self.openai_client:
            return None

        # Truncate HTML to save tokens
        if len(html) > 15000:
            html = html[:15000]

        prompt = f"""Extract company information from this LinkedIn company About page HTML.

HTML Content:
{html}

Extract and return ONLY a valid JSON object with these fields:

{{
  "company_size": "employee count range (e.g., '11-50', '51-200', '201-500', '501-1000', '1001-5000', '5001-10000', '10001+')",
  "company_type": "industry or company type (e.g., 'Legal Services', 'Real Estate', 'Technology')"
}}

IMPORTANT:
1. Look for text like "11-50 employees", "Company size", or employee count ranges
2. Look for "Industry" field for company_type
3. LinkedIn typically shows ranges like: 1-10, 11-50, 51-200, 201-500, 501-1000, 1001-5000, 5001-10000, 10001+
4. Return null for fields not found
5. Return ONLY the JSON object, no other text
"""

        try:
            response = self.openai_client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a data extractor. Return only valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=OPENAI_TEMPERATURE,
                max_tokens=200,
                response_format={"type": "json_object"}
            )

            content = response.choices[0].message.content
            result = json.loads(content)

            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response for LinkedIn: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing LinkedIn with LLM: {e}")
            return None
