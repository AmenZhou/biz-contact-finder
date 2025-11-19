"""
LLM-based parser for extracting structured contact information from HTML
"""
import logging
import json
from typing import Optional, Dict
from openai import OpenAI

from config.settings import (
    OPENAI_API_KEY,
    OPENAI_MODEL,
    OPENAI_MAX_TOKENS,
    OPENAI_TEMPERATURE
)

logger = logging.getLogger(__name__)


class LLMContactParser:
    """Parser using OpenAI GPT-4o-mini to extract contact info from HTML"""

    def __init__(self, api_key: str = OPENAI_API_KEY):
        """Initialize OpenAI client"""
        if not api_key:
            raise ValueError("OpenAI API key is required")
        self.client = OpenAI(api_key=api_key)
        self.model = OPENAI_MODEL

    def create_extraction_prompt(self, html: str, company_name: str) -> str:
        """
        Create a prompt for extracting contact information

        Args:
            html: HTML content to parse
            company_name: Name of the company

        Returns:
            Formatted prompt string
        """
        # Truncate HTML if too long (GPT-4o-mini has 128k context but we want to keep costs low)
        max_html_length = 8000
        if len(html) > max_html_length:
            html = html[:max_html_length] + "..."

        prompt = f"""You are a contact information extraction specialist. Extract contact information for the company "{company_name}" from the following HTML content.

HTML Content:
{html}

Extract the following information and return ONLY a valid JSON object with these exact fields (use null for missing values):

{{
  "email": "primary contact email address",
  "email_secondary": "secondary email if available",
  "phone": "phone number in format (XXX) XXX-XXXX",
  "phone_secondary": "secondary phone if available",
  "linkedin": "LinkedIn company profile URL",
  "twitter": "Twitter/X handle or URL",
  "facebook": "Facebook page URL",
  "contact_person": "Name of contact person if mentioned",
  "contact_title": "Title of contact person if mentioned",
  "address": "Full physical address if available"
}}

IMPORTANT RULES:
1. Only extract information that is clearly visible in the HTML
2. Do NOT make up or hallucinate any contact information
3. For emails, prefer general contact emails (info@, contact@, hello@) over personal emails
4. Format phone numbers consistently as (XXX) XXX-XXXX for US numbers
5. Return ONLY the JSON object, no other text
6. If a field is not found, use null (not empty string)
7. Verify that email addresses and URLs are properly formatted
"""
        return prompt

    def parse_contact_info(self, html: str, company_name: str) -> Optional[Dict]:
        """
        Parse contact information from HTML using GPT-4o-mini

        Args:
            html: HTML content
            company_name: Name of the company

        Returns:
            Dictionary with extracted contact info or None if failed
        """
        try:
            logger.info(f"Parsing contact info for {company_name} using {self.model}")

            prompt = self.create_extraction_prompt(html, company_name)

            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a precise contact information extractor. Return only valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=OPENAI_TEMPERATURE,
                max_tokens=OPENAI_MAX_TOKENS,
                response_format={"type": "json_object"}  # Ensures JSON output
            )

            # Parse response
            content = response.choices[0].message.content
            contact_info = json.loads(content)

            logger.info(f"Successfully extracted contact info for {company_name}")
            logger.debug(f"Extracted: {contact_info}")

            # Validate and clean up
            contact_info = self.validate_contact_info(contact_info)

            return contact_info

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response for {company_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing contact info for {company_name}: {e}")
            return None

    def validate_contact_info(self, contact_info: Dict) -> Dict:
        """
        Validate and clean extracted contact information

        Args:
            contact_info: Raw extracted data

        Returns:
            Validated and cleaned contact info
        """
        import re

        # Email validation pattern
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

        # Clean email fields
        for email_field in ['email', 'email_secondary']:
            if email_field in contact_info and contact_info[email_field]:
                email = contact_info[email_field].strip()
                if not re.match(email_pattern, email):
                    logger.warning(f"Invalid email format: {email}")
                    contact_info[email_field] = None
                else:
                    contact_info[email_field] = email.lower()

        # Clean phone numbers
        for phone_field in ['phone', 'phone_secondary']:
            if phone_field in contact_info and contact_info[phone_field]:
                phone = contact_info[phone_field].strip()
                # Keep only digits
                digits = re.sub(r'\D', '', phone)
                if len(digits) == 10:
                    # Format as (XXX) XXX-XXXX
                    contact_info[phone_field] = f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
                elif len(digits) == 11 and digits[0] == '1':
                    # Remove leading 1 and format
                    contact_info[phone_field] = f"({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
                else:
                    # Keep original if can't parse
                    contact_info[phone_field] = phone

        # Validate URLs
        url_fields = ['linkedin', 'twitter', 'facebook']
        for url_field in url_fields:
            if url_field in contact_info and contact_info[url_field]:
                url = contact_info[url_field].strip()
                if not url.startswith('http'):
                    # Try to fix common issues
                    if url_field == 'linkedin' and 'linkedin.com' not in url:
                        contact_info[url_field] = None
                    elif url_field == 'twitter' and 'twitter.com' not in url and 'x.com' not in url:
                        contact_info[url_field] = None
                    elif url_field == 'facebook' and 'facebook.com' not in url:
                        contact_info[url_field] = None

        return contact_info
