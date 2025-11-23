"""
Configuration settings for the company contact scraper
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Keys
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
GOOGLE_PLACES_API_KEY = os.getenv('GOOGLE_PLACES_API_KEY')
HUNTER_API_KEY = os.getenv('HUNTER_API_KEY')

# Rate Limiting
MAX_REQUESTS_PER_SECOND = int(os.getenv('MAX_REQUESTS_PER_SECOND', 1))
REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', 10))

# Logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = 'logs/scraper.log'

# File Paths
INPUT_CSV = 'data/1221_6th.csv'  # All merchants

# Extract prefix from input filename (e.g., "330Madison" from "330Madison.csv")
import os as _os
OUTPUT_PREFIX = _os.path.splitext(_os.path.basename(INPUT_CSV))[0]

OUTPUT_CSV = f'data/{OUTPUT_PREFIX}_merchants.csv'
PROGRESS_FILE = f'data/{OUTPUT_PREFIX}_progress.json'

# OpenAI Settings
OPENAI_MODEL = 'gpt-4o-mini'
OPENAI_MAX_TOKENS = 2000  # Increased for lawyer extraction with full contact details
OPENAI_TEMPERATURE = 0.1  # Low temperature for more consistent outputs

# Output Files
LAWYERS_CSV = f'data/{OUTPUT_PREFIX}_lawyers.csv'  # Separate file for lawyer contacts
BUILDING_CONTACTS_CSV = f'data/{OUTPUT_PREFIX}_building_contacts.csv'  # Building management contacts

# Scraping Settings
USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Contact Info Scraper/1.0'
CONTACT_PAGE_KEYWORDS = ['contact', 'about', 'reach-us', 'get-in-touch']
# Attorney/Law firm specific pages for lawyer contact extraction
ATTORNEY_PAGE_KEYWORDS = ['attorneys', 'lawyers', 'our-team', 'professionals', 'people',
                          'our-attorneys', 'our-lawyers', 'partners', 'associates', 'staff',
                          'practice-areas', 'team', 'bio', 'profile']

# Office building detection keywords
OFFICE_BUILDING_KEYWORDS = [
    'business center', 'office building', 'commercial building', 'office space',
    'property management', 'real estate', 'realty', 'tower', 'plaza', 'center'
]

# Tenant services page keywords for office buildings
TENANT_PAGE_KEYWORDS = ['tenant', 'tenants', 'tenant-services', 'amenities', 'building-services',
                        'property-management', 'leasing', 'building-management', 'community',
                        'concierge', 'services', 'building-team', 'management-team']
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

# Validation Patterns
EMAIL_PATTERN = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
PHONE_PATTERN = r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'

# Data Quality Scoring Weights
QUALITY_WEIGHTS = {
    'website': 30,
    'email': 25,
    'phone': 20,
    'linkedin': 15,
    'contact_person': 10
}
