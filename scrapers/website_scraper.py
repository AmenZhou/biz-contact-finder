"""
Website scraper for extracting contact page HTML
"""
import logging
import requests
from bs4 import BeautifulSoup
from typing import Optional, List, Dict
from urllib.parse import urljoin, urlparse
from ratelimit import limits, sleep_and_retry
from tenacity import retry, stop_after_attempt, wait_exponential

from config.settings import (
    USER_AGENT,
    REQUEST_TIMEOUT,
    CONTACT_PAGE_KEYWORDS,
    MAX_REQUESTS_PER_SECOND,
    MAX_RETRIES
)

logger = logging.getLogger(__name__)


class WebsiteScraper:
    """Scraper for company websites"""

    def __init__(self):
        """Initialize the website scraper"""
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': USER_AGENT})

    @sleep_and_retry
    @limits(calls=MAX_REQUESTS_PER_SECOND, period=1)
    @retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(min=1, max=10))
    def fetch_page(self, url: str) -> Optional[str]:
        """
        Fetch a webpage with rate limiting and retry logic

        Args:
            url: URL to fetch

        Returns:
            HTML content or None if failed
        """
        try:
            logger.debug(f"Fetching: {url}")
            response = self.session.get(url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
            response.raise_for_status()
            return response.text
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout fetching {url}")
            return None
        except requests.exceptions.HTTPError as e:
            logger.warning(f"HTTP error {e.response.status_code} for {url}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error for {url}: {e}")
            return None

    def find_contact_pages(self, base_url: str, html: str) -> List[str]:
        """
        Find potential contact page URLs from homepage

        Args:
            base_url: Base URL of the website
            html: HTML content of homepage

        Returns:
            List of potential contact page URLs
        """
        soup = BeautifulSoup(html, 'lxml')
        contact_urls = []

        # Find all links
        for link in soup.find_all('a', href=True):
            href = link['href'].lower()
            text = link.get_text().lower()

            # Check if link text or href contains contact keywords
            for keyword in CONTACT_PAGE_KEYWORDS:
                if keyword in href or keyword in text:
                    full_url = urljoin(base_url, link['href'])
                    if full_url not in contact_urls:
                        contact_urls.append(full_url)
                        logger.debug(f"Found potential contact page: {full_url}")

        return contact_urls

    def extract_contact_section(self, html: str) -> str:
        """
        Extract the most relevant contact section from HTML

        Args:
            html: Full HTML content

        Returns:
            Cleaned HTML of contact section
        """
        soup = BeautifulSoup(html, 'lxml')

        # Try to find contact section by common patterns
        contact_section = None

        # Look for sections with contact-related ids or classes
        contact_patterns = ['contact', 'reach', 'get-in-touch', 'footer', 'about']
        for pattern in contact_patterns:
            # Check ids
            section = soup.find(id=lambda x: x and pattern in x.lower())
            if section:
                contact_section = section
                break

            # Check classes
            section = soup.find(class_=lambda x: x and pattern in str(x).lower())
            if section:
                contact_section = section
                break

        # If no specific section found, use footer
        if not contact_section:
            contact_section = soup.find('footer')

        # If still nothing, use the whole body
        if not contact_section:
            contact_section = soup.find('body')

        # Extract text while preserving some structure
        if contact_section:
            # Remove script and style tags
            for script in contact_section(['script', 'style', 'nav', 'header']):
                script.decompose()

            return str(contact_section)

        return html

    def scrape_contact_info(self, website_url: str) -> Optional[Dict]:
        """
        Main method to scrape contact information from a website

        Args:
            website_url: Company website URL

        Returns:
            Dictionary with scraped HTML and metadata
        """
        if not website_url:
            return None

        # Ensure URL has protocol
        if not website_url.startswith(('http://', 'https://')):
            website_url = 'https://' + website_url

        logger.info(f"Scraping website: {website_url}")

        # Fetch homepage
        homepage_html = self.fetch_page(website_url)
        if not homepage_html:
            logger.warning(f"Failed to fetch homepage: {website_url}")
            return None

        # Find contact pages
        contact_pages = self.find_contact_pages(website_url, homepage_html)

        # Try to fetch contact pages
        contact_html = None
        contact_url = website_url

        for page_url in contact_pages[:3]:  # Try first 3 contact pages
            html = self.fetch_page(page_url)
            if html:
                contact_html = html
                contact_url = page_url
                logger.info(f"Found contact page: {page_url}")
                break

        # If no contact page found, use homepage
        if not contact_html:
            logger.info(f"No dedicated contact page found, using homepage")
            contact_html = homepage_html

        # Extract relevant contact section
        contact_section = self.extract_contact_section(contact_html)

        return {
            'url': contact_url,
            'html': contact_section,
            'full_html': contact_html,
            'has_contact_page': len(contact_pages) > 0,
            'contact_page_urls': contact_pages
        }

    def get_domain(self, url: str) -> str:
        """Extract domain from URL"""
        parsed = urlparse(url)
        return parsed.netloc or parsed.path
