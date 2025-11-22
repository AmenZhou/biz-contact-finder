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

import re

from config.settings import (
    USER_AGENT,
    REQUEST_TIMEOUT,
    CONTACT_PAGE_KEYWORDS,
    ATTORNEY_PAGE_KEYWORDS,
    TENANT_PAGE_KEYWORDS,
    MAX_REQUESTS_PER_SECOND,
    MAX_RETRIES
)

logger = logging.getLogger(__name__)

# Try to import playwright for JS rendering
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright not available - JavaScript-rendered pages won't be fully scraped")

# Patterns for extracting contact info directly from HTML
EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
LINKEDIN_PATTERN = re.compile(r'https?://(?:www\.)?linkedin\.com/(?:company|in)/[a-zA-Z0-9_-]+/?')
TWITTER_PATTERN = re.compile(r'https?://(?:www\.)?(?:twitter\.com|x\.com)/[a-zA-Z0-9_]+/?')
FACEBOOK_PATTERN = re.compile(r'https?://(?:www\.)?facebook\.com/[a-zA-Z0-9._-]+/?')
INSTAGRAM_PATTERN = re.compile(r'https?://(?:www\.)?instagram\.com/[a-zA-Z0-9._]+/?')


class WebsiteScraper:
    """Scraper for company websites"""

    def __init__(self):
        """Initialize the website scraper"""
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': USER_AGENT})
        self._playwright = None
        self._browser = None

    def _get_browser(self):
        """Get or create Playwright browser instance"""
        if not PLAYWRIGHT_AVAILABLE:
            return None
        if self._browser is None:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=True)
        return self._browser

    def fetch_page_with_js(self, url: str, timeout: int = 15000) -> Optional[str]:
        """
        Fetch a page with JavaScript rendering using Playwright

        Args:
            url: URL to fetch
            timeout: Timeout in milliseconds

        Returns:
            Rendered HTML content or None if failed
        """
        browser = self._get_browser()
        if not browser:
            logger.warning("Playwright not available, falling back to requests")
            return self.fetch_page(url)

        try:
            logger.debug(f"Fetching with JS rendering: {url}")
            page = browser.new_page()
            page.goto(url, timeout=timeout)
            # Wait for network to be idle (content loaded)
            page.wait_for_load_state('networkidle', timeout=timeout)
            html = page.content()
            page.close()
            return html
        except Exception as e:
            logger.warning(f"Failed to fetch with Playwright: {url} - {e}")
            return None

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

    def find_attorney_pages(self, base_url: str, html: str) -> List[str]:
        """
        Find attorney/lawyer profile pages from law firm websites

        Args:
            base_url: Base URL of the website
            html: HTML content of homepage

        Returns:
            List of potential attorney page URLs
        """
        soup = BeautifulSoup(html, 'lxml')
        attorney_urls = []

        # Find all links
        for link in soup.find_all('a', href=True):
            href = link['href'].lower()
            text = link.get_text().lower()

            # Check if link text or href contains attorney keywords
            for keyword in ATTORNEY_PAGE_KEYWORDS:
                if keyword in href or keyword in text:
                    full_url = urljoin(base_url, link['href'])
                    if full_url not in attorney_urls:
                        attorney_urls.append(full_url)
                        logger.debug(f"Found potential attorney page: {full_url}")

        return attorney_urls

    def find_tenant_pages(self, base_url: str, html: str) -> List[str]:
        """
        Find tenant services/amenities pages from office building websites

        Args:
            base_url: Base URL of the website
            html: HTML content of homepage

        Returns:
            List of potential tenant services page URLs
        """
        soup = BeautifulSoup(html, 'lxml')
        tenant_urls = []

        # Find all links
        for link in soup.find_all('a', href=True):
            href = link['href'].lower()
            text = link.get_text().lower()

            # Check if link text or href contains tenant keywords
            for keyword in TENANT_PAGE_KEYWORDS:
                if keyword in href or keyword in text:
                    full_url = urljoin(base_url, link['href'])
                    if full_url not in tenant_urls:
                        tenant_urls.append(full_url)
                        logger.debug(f"Found potential tenant page: {full_url}")

        return tenant_urls

    def extract_lawyer_profiles(self, html: str, base_url: str = None) -> List[Dict]:
        """
        Extract individual lawyer profile information from HTML

        Args:
            html: HTML content containing lawyer profiles
            base_url: Base URL for resolving relative links

        Returns:
            List of dictionaries with lawyer info (name, title, email, phone, linkedin, profile_url)
        """
        soup = BeautifulSoup(html, 'lxml')
        lawyers = []

        # Method 1: Find profiles by looking at containers with mailto: links
        # This is more reliable as it directly links email to nearby name
        for email_link in soup.find_all('a', href=lambda x: x and 'mailto:' in x):
            email = email_link['href'].replace('mailto:', '').split('?')[0].lower()
            # Skip generic emails
            if any(g in email for g in ['info@', 'contact@', 'support@', 'admin@']):
                continue

            lawyer_info = {
                'name': None,
                'title': None,
                'email': email,
                'phone': None,
                'linkedin': None,
                'profile_url': None
            }

            # Find containing element
            for parent in email_link.parents:
                if parent.name in ['div', 'article', 'section', 'li']:
                    # Find name
                    name_tag = parent.find(['h2', 'h3', 'h4', 'strong', 'b'])
                    if name_tag:
                        lawyer_info['name'] = name_tag.get_text().strip()

                        # Find title
                        for tag in parent.find_all(['h4', 'h5', 'p', 'span']):
                            text = tag.get_text().strip()
                            if text and text != lawyer_info['name'] and len(text) < 50:
                                if any(t in text.lower() for t in ['partner', 'associate', 'counsel', 'attorney']):
                                    lawyer_info['title'] = text
                                    break

                        # Find phone
                        phone_link = parent.find('a', href=lambda x: x and 'tel:' in str(x))
                        if phone_link:
                            phone = phone_link['href'].replace('tel:', '').replace('+1', '')
                            digits = ''.join(filter(str.isdigit, phone))
                            if len(digits) == 10:
                                lawyer_info['phone'] = f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
                            else:
                                lawyer_info['phone'] = phone

                        # Find LinkedIn
                        li_link = parent.find('a', href=lambda x: x and 'linkedin.com/in/' in str(x).lower())
                        if li_link:
                            lawyer_info['linkedin'] = li_link['href']

                        # Find profile URL
                        if base_url:
                            name_link = name_tag.find('a', href=True) or name_tag.find_parent('a', href=True)
                            if name_link:
                                lawyer_info['profile_url'] = urljoin(base_url, name_link['href'])

                        if lawyer_info['name']:
                            lawyers.append(lawyer_info)
                        break

        # If we found lawyers with Method 1, return them
        if lawyers:
            logger.info(f"Found {len(lawyers)} attorneys with email-based extraction")
            return lawyers

        # Method 2: Fallback to class-based patterns
        profile_patterns = [
            {'class_': lambda x: x and any(p in str(x).lower() for p in ['attorney', 'lawyer', 'profile', 'team-member', 'staff', 'person', 'bio'])},
            {'class_': lambda x: x and 'card' in str(x).lower()},
        ]

        profile_elements = []
        for pattern in profile_patterns:
            elements = soup.find_all(['div', 'article', 'li', 'section'], **pattern)
            profile_elements.extend(elements)

        # Deduplicate
        seen_texts = set()
        for element in profile_elements:
            text_content = element.get_text()
            if text_content in seen_texts:
                continue
            seen_texts.add(text_content)

            lawyer_info = {
                'name': None,
                'title': None,
                'email': None,
                'phone': None,
                'linkedin': None,
                'profile_url': None
            }

            # Extract name (usually in h2, h3, h4, or strong tags)
            name_tag = element.find(['h2', 'h3', 'h4', 'strong', 'b'])
            if name_tag:
                lawyer_info['name'] = name_tag.get_text().strip()
                # Check if name is a link to profile page
                name_link = name_tag.find('a', href=True) or name_tag.find_parent('a', href=True)
                if name_link and base_url:
                    lawyer_info['profile_url'] = urljoin(base_url, name_link['href'])

            # Also look for profile link in the element
            if not lawyer_info['profile_url'] and base_url:
                profile_link = element.find('a', href=lambda x: x and any(kw in str(x).lower() for kw in ['bio', 'profile', 'attorney', 'lawyer', 'people', 'professional']))
                if profile_link:
                    lawyer_info['profile_url'] = urljoin(base_url, profile_link['href'])

            # Extract title (often in spans or p tags with specific classes)
            title_patterns = ['title', 'position', 'role', 'designation']
            for pattern in title_patterns:
                title_tag = element.find(class_=lambda x: x and pattern in str(x).lower())
                if title_tag:
                    lawyer_info['title'] = title_tag.get_text().strip()
                    break

            # Extract email from mailto links
            email_link = element.find('a', href=lambda x: x and 'mailto:' in x)
            if email_link:
                email = email_link['href'].replace('mailto:', '').split('?')[0]
                lawyer_info['email'] = email.lower()

            # Also check for emails in text
            if not lawyer_info['email']:
                emails = EMAIL_PATTERN.findall(str(element))
                if emails:
                    lawyer_info['email'] = emails[0].lower()

            # Extract phone from tel links
            phone_link = element.find('a', href=lambda x: x and 'tel:' in x)
            if phone_link:
                lawyer_info['phone'] = phone_link['href'].replace('tel:', '')

            # Extract LinkedIn
            linkedin_link = element.find('a', href=lambda x: x and 'linkedin.com' in str(x).lower())
            if linkedin_link:
                lawyer_info['linkedin'] = linkedin_link['href']

            # Only add if we found at least a name
            if lawyer_info['name']:
                lawyers.append(lawyer_info)

        return lawyers

    def scrape_lawyer_profile_page(self, profile_url: str) -> Dict:
        """
        Scrape individual lawyer profile page for detailed contact info

        Args:
            profile_url: URL of lawyer's bio/profile page

        Returns:
            Dictionary with email, phone, linkedin
        """
        contact_info = {
            'email': None,
            'phone': None,
            'linkedin': None
        }

        html = self.fetch_page(profile_url)
        if not html:
            return contact_info

        soup = BeautifulSoup(html, 'lxml')

        # Extract email from mailto links
        email_link = soup.find('a', href=lambda x: x and 'mailto:' in str(x))
        if email_link:
            email = email_link['href'].replace('mailto:', '').split('?')[0]
            contact_info['email'] = email.lower()

        # Also check for emails in page content
        if not contact_info['email']:
            emails = EMAIL_PATTERN.findall(html)
            # Filter out generic emails
            for email in emails:
                email = email.lower()
                if not any(g in email for g in ['info@', 'contact@', 'support@', 'admin@']):
                    contact_info['email'] = email
                    break

        # Extract phone from tel links
        phone_link = soup.find('a', href=lambda x: x and 'tel:' in str(x))
        if phone_link:
            contact_info['phone'] = phone_link['href'].replace('tel:', '')

        # Extract LinkedIn
        linkedin_link = soup.find('a', href=lambda x: x and 'linkedin.com/in/' in str(x).lower())
        if linkedin_link:
            contact_info['linkedin'] = linkedin_link['href']

        return contact_info

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

    def extract_emails_from_html(self, html: str) -> List[str]:
        """
        Extract email addresses directly from HTML using regex

        Args:
            html: HTML content

        Returns:
            List of unique email addresses found
        """
        emails = EMAIL_PATTERN.findall(html)

        # Filter out common false positives
        filtered_emails = []
        exclude_patterns = ['example.com', 'your-email', 'email@', 'test@', 'sample@',
                          '.png', '.jpg', '.gif', '.css', '.js', 'wixpress', 'sentry']

        for email in emails:
            email = email.lower()
            if not any(pattern in email for pattern in exclude_patterns):
                if email not in filtered_emails:
                    filtered_emails.append(email)

        # Sort by priority (events, marketing, info, contact first)
        priority_prefixes = ['events', 'marketing', 'info', 'contact', 'hello', 'sales']

        def email_priority(email):
            for i, prefix in enumerate(priority_prefixes):
                if email.startswith(prefix):
                    return i
            return len(priority_prefixes)

        filtered_emails.sort(key=email_priority)

        return filtered_emails

    def extract_social_links(self, html: str) -> Dict[str, str]:
        """
        Extract social media links directly from HTML

        Args:
            html: HTML content

        Returns:
            Dictionary with social media URLs
        """
        social_links = {
            'linkedin': None,
            'twitter': None,
            'facebook': None,
            'instagram': None
        }

        # Find LinkedIn
        linkedin_matches = LINKEDIN_PATTERN.findall(html)
        if linkedin_matches:
            social_links['linkedin'] = linkedin_matches[0]

        # Find Twitter/X
        twitter_matches = TWITTER_PATTERN.findall(html)
        if twitter_matches:
            social_links['twitter'] = twitter_matches[0]

        # Find Facebook
        facebook_matches = FACEBOOK_PATTERN.findall(html)
        if facebook_matches:
            # Filter out share links
            for fb_url in facebook_matches:
                if '/sharer' not in fb_url and '/share' not in fb_url:
                    social_links['facebook'] = fb_url
                    break

        # Find Instagram
        instagram_matches = INSTAGRAM_PATTERN.findall(html)
        if instagram_matches:
            social_links['instagram'] = instagram_matches[0]

        return social_links

    def scrape_multiple_pages(self, website_url: str, is_law_firm: bool = False, is_office_building: bool = False) -> Optional[Dict]:
        """
        Scrape multiple pages from a website to find contact info

        Args:
            website_url: Company website URL
            is_law_firm: If True, also scrape attorney/lawyer pages
            is_office_building: If True, also scrape tenant services/amenities pages

        Returns:
            Dictionary with combined HTML from multiple pages
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

        # Also try common paths
        base_parsed = urlparse(website_url)
        base_url = f"{base_parsed.scheme}://{base_parsed.netloc}"
        common_paths = ['/contact', '/contact-us', '/about', '/about-us', '/team', '/our-team']

        for path in common_paths:
            full_url = base_url + path
            if full_url not in contact_pages:
                contact_pages.append(full_url)

        # Find attorney pages if this is a law firm
        attorney_pages = []
        if is_law_firm:
            attorney_pages = self.find_attorney_pages(website_url, homepage_html)
            # Add common law firm paths
            law_firm_paths = ['/attorneys', '/lawyers', '/our-team', '/professionals',
                            '/people', '/our-attorneys', '/our-lawyers', '/partners']
            for path in law_firm_paths:
                full_url = base_url + path
                if full_url not in attorney_pages:
                    attorney_pages.append(full_url)
            logger.info(f"Found {len(attorney_pages)} potential attorney pages")

        # Find tenant pages if this is an office building
        tenant_pages = []
        if is_office_building:
            tenant_pages = self.find_tenant_pages(website_url, homepage_html)
            # Add common office building paths
            building_paths = ['/tenant-services', '/tenants', '/amenities', '/services',
                            '/building-services', '/property-management', '/leasing',
                            '/building-team', '/management', '/concierge']
            for path in building_paths:
                full_url = base_url + path
                if full_url not in tenant_pages:
                    tenant_pages.append(full_url)
            logger.info(f"Found {len(tenant_pages)} potential tenant services pages")

        # Fetch and combine HTML from multiple pages
        combined_html = homepage_html
        fetched_pages = [website_url]

        for page_url in contact_pages[:5]:  # Try first 5 contact pages
            if page_url not in fetched_pages:
                html = self.fetch_page(page_url)
                if html:
                    combined_html += "\n\n<!-- PAGE: {} -->\n\n{}".format(page_url, html)
                    fetched_pages.append(page_url)
                    logger.info(f"Fetched additional page: {page_url}")

        # Fetch attorney pages for law firms
        lawyers = []
        if is_law_firm:
            for page_url in attorney_pages[:5]:  # Try first 5 attorney pages
                if page_url not in fetched_pages:
                    # Use JS rendering for attorney pages (often have JS-loaded content)
                    html = self.fetch_page_with_js(page_url) if PLAYWRIGHT_AVAILABLE else self.fetch_page(page_url)
                    if html:
                        combined_html += "\n\n<!-- ATTORNEY PAGE: {} -->\n\n{}".format(page_url, html)
                        fetched_pages.append(page_url)
                        logger.info(f"Fetched attorney page (JS rendered): {page_url}")
                        # Extract lawyer profiles from this page
                        page_lawyers = self.extract_lawyer_profiles(html, base_url)

                        # Also extract emails directly from this page for each lawyer
                        page_emails = self.extract_emails_from_html(html)
                        soup = BeautifulSoup(html, 'lxml')

                        # Find all mailto links with associated names
                        for link in soup.find_all('a', href=lambda x: x and 'mailto:' in x):
                            email = link['href'].replace('mailto:', '').split('?')[0].lower()
                            # Try to find associated name - check multiple parent levels
                            found = False
                            for parent in link.parents:
                                if parent.name in ['div', 'li', 'article', 'section']:
                                    name_tag = parent.find(['h2', 'h3', 'h4', 'strong', 'b'])
                                    if name_tag:
                                        name = name_tag.get_text().strip()
                                        # Find matching lawyer and add email
                                        for lawyer in page_lawyers:
                                            if lawyer.get('name') and lawyer['name'].lower() == name.lower():
                                                lawyer['email'] = email
                                                found = True
                                                logger.debug(f"Matched email {email} to {name}")
                                                break
                                    if found:
                                        break

                        # Find all tel links with associated names
                        for link in soup.find_all('a', href=lambda x: x and 'tel:' in x):
                            phone = link['href'].replace('tel:', '').replace('+1', '')
                            # Format phone
                            digits = ''.join(filter(str.isdigit, phone))
                            if len(digits) == 10:
                                phone = f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"

                            found = False
                            for parent in link.parents:
                                if parent.name in ['div', 'li', 'article', 'section']:
                                    name_tag = parent.find(['h2', 'h3', 'h4', 'strong', 'b'])
                                    if name_tag:
                                        name = name_tag.get_text().strip()
                                        for lawyer in page_lawyers:
                                            if lawyer.get('name') and lawyer['name'].lower() == name.lower():
                                                lawyer['phone'] = phone
                                                found = True
                                                logger.debug(f"Matched phone {phone} to {name}")
                                                break
                                    if found:
                                        break

                        lawyers.extend(page_lawyers)

            logger.info(f"Extracted {len(lawyers)} lawyer profiles")

            # Scrape individual lawyer profile pages to get contact details
            seen_names = set()
            unique_lawyers = []
            for lawyer in lawyers:
                name = lawyer.get('name', '').lower()
                if name and name not in seen_names:
                    seen_names.add(name)
                    # If we have a profile URL and missing contact info, scrape it
                    if lawyer.get('profile_url') and (not lawyer.get('email') or not lawyer.get('phone')):
                        logger.info(f"Scraping profile page for {lawyer['name']}")
                        profile_info = self.scrape_lawyer_profile_page(lawyer['profile_url'])
                        # Merge contact info
                        if profile_info.get('email') and not lawyer.get('email'):
                            lawyer['email'] = profile_info['email']
                        if profile_info.get('phone') and not lawyer.get('phone'):
                            lawyer['phone'] = profile_info['phone']
                        if profile_info.get('linkedin') and not lawyer.get('linkedin'):
                            lawyer['linkedin'] = profile_info['linkedin']
                    unique_lawyers.append(lawyer)
                    # Limit to 10 lawyers to avoid too many requests
                    if len(unique_lawyers) >= 10:
                        break

            lawyers = unique_lawyers
            logger.info(f"Final lawyer count after dedup and profile scraping: {len(lawyers)}")

        # Fetch tenant services pages for office buildings
        if is_office_building:
            for page_url in tenant_pages[:5]:  # Try first 5 tenant pages
                if page_url not in fetched_pages:
                    html = self.fetch_page(page_url)
                    if html:
                        combined_html += "\n\n<!-- TENANT PAGE: {} -->\n\n{}".format(page_url, html)
                        fetched_pages.append(page_url)
                        logger.info(f"Fetched tenant services page: {page_url}")

        # Extract emails and social links directly
        emails = self.extract_emails_from_html(combined_html)
        social_links = self.extract_social_links(combined_html)

        # Extract relevant contact section for LLM
        contact_section = self.extract_contact_section(combined_html)

        result = {
            'url': website_url,
            'html': contact_section,
            'full_html': combined_html,
            'has_contact_page': len(contact_pages) > 0,
            'contact_page_urls': contact_pages,
            'extracted_emails': emails,
            'extracted_social': social_links,
            'pages_fetched': fetched_pages
        }

        # Add lawyer info if this is a law firm
        if is_law_firm:
            result['attorney_pages'] = attorney_pages
            result['lawyers'] = lawyers

        return result
