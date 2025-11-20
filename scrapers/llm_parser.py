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

        prompt = f"""You are an expert contact information extraction specialist. Your task is to thoroughly extract ALL contact information for the company "{company_name}" from the following HTML content.

HTML Content:
{html}

Extract the following information and return ONLY a valid JSON object with these exact fields (use null for missing values):

{{
  "email": "primary contact email address",
  "email_contact_name": "name of person associated with the primary email (parse from firstname.lastname@ pattern if personal email)",
  "email_contact_title": "job title of person associated with the primary email",
  "email_secondary": "secondary email if available",
  "phone": "phone number in format (XXX) XXX-XXXX",
  "phone_contact_name": "name of person or department associated with this phone",
  "phone_contact_title": "title/role associated with this phone (e.g., Sales, Support, Manager)",
  "phone_secondary": "secondary phone if available",
  "linkedin": "LinkedIn company profile URL",
  "twitter": "Twitter/X handle or URL",
  "facebook": "Facebook page URL",
  "instagram": "Instagram URL or handle",
  "contact_person": "Name of key contact person (marketing, events, or general manager)",
  "contact_title": "Title of key contact person if mentioned",
  "address": "Full physical address if available"
}}

EXTRACTION STRATEGIES - Be thorough:

1. **EMAIL DISCOVERY** (search aggressively):
   - Look for mailto: links in the HTML
   - Check footer sections for email addresses
   - Look for patterns like "email us at", "contact:", "reach us"
   - Check for domain-based emails (info@, contact@, hello@, events@, marketing@, careers@)
   - Look in href attributes and data attributes
   - PREFER these emails in order: events@, marketing@, info@, contact@, hello@

2. **LINKEDIN DISCOVERY**:
   - Search for linkedin.com/company/ URLs
   - Look in social media icon links
   - Check footer social links
   - Look for "in" icons with hrefs

3. **SOCIAL MEDIA**:
   - Check for social media icons/links in header and footer
   - Look for share buttons
   - Search for twitter.com, x.com, facebook.com, instagram.com URLs

4. **CONTACT PERSON**:
   - Look for staff/team pages references
   - Find names with titles like "Manager", "Director", "Owner", "Marketing"
   - Check "About" sections for key personnel

IMPORTANT RULES:
1. Search the ENTIRE HTML thoroughly - emails are often hidden in footers or data attributes
2. Do NOT make up or hallucinate any contact information
3. Format phone numbers consistently as (XXX) XXX-XXXX for US numbers
4. Return ONLY the JSON object, no other text
5. If a field is not found after thorough search, use null
6. Verify that email addresses contain @ and valid domain extensions
7. LinkedIn URLs should contain linkedin.com/company/ or linkedin.com/in/
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
        url_fields = ['linkedin', 'twitter', 'facebook', 'instagram']
        for url_field in url_fields:
            if url_field in contact_info and contact_info[url_field]:
                url = contact_info[url_field].strip()
                # Add https:// if missing
                if not url.startswith('http') and '.' in url:
                    url = 'https://' + url
                    contact_info[url_field] = url

                # Validate URL contains expected domain
                if url_field == 'linkedin' and 'linkedin.com' not in url:
                    contact_info[url_field] = None
                elif url_field == 'twitter' and 'twitter.com' not in url and 'x.com' not in url:
                    contact_info[url_field] = None
                elif url_field == 'facebook' and 'facebook.com' not in url:
                    contact_info[url_field] = None
                elif url_field == 'instagram' and 'instagram.com' not in url:
                    contact_info[url_field] = None

        return contact_info
