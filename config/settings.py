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
INPUT_CSV = 'data/330Madison.csv'
OUTPUT_CSV = 'data/output_enriched.csv'
PROGRESS_FILE = 'data/progress.json'

# OpenAI Settings
OPENAI_MODEL = 'gpt-4o-mini'
OPENAI_MAX_TOKENS = 500
OPENAI_TEMPERATURE = 0.1  # Low temperature for more consistent outputs

# Scraping Settings
USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Contact Info Scraper/1.0'
CONTACT_PAGE_KEYWORDS = ['contact', 'about', 'reach-us', 'get-in-touch']
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
