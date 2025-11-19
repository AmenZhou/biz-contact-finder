"""
Validation utilities for contact information
"""
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def validate_email(email: Optional[str]) -> bool:
    """
    Validate email format

    Args:
        email: Email address to validate

    Returns:
        True if valid, False otherwise
    """
    if not email:
        return False

    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(email_pattern, email.strip()))


def validate_phone(phone: Optional[str]) -> bool:
    """
    Validate US phone number

    Args:
        phone: Phone number to validate

    Returns:
        True if valid, False otherwise
    """
    if not phone:
        return False

    # Extract digits only
    digits = re.sub(r'\D', '', phone)

    # Valid if 10 digits or 11 digits starting with 1
    return len(digits) == 10 or (len(digits) == 11 and digits[0] == '1')


def validate_url(url: Optional[str]) -> bool:
    """
    Validate URL format

    Args:
        url: URL to validate

    Returns:
        True if valid, False otherwise
    """
    if not url:
        return False

    url_pattern = r'^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    return bool(re.match(url_pattern, url.strip()))


def format_phone(phone: str) -> str:
    """
    Format phone number to (XXX) XXX-XXXX

    Args:
        phone: Raw phone number

    Returns:
        Formatted phone number
    """
    if not phone:
        return ""

    digits = re.sub(r'\D', '', phone)

    if len(digits) == 11 and digits[0] == '1':
        digits = digits[1:]

    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"

    return phone  # Return original if can't format


def calculate_quality_score(contact_data: dict) -> int:
    """
    Calculate data quality score based on available information

    Args:
        contact_data: Dictionary with contact information

    Returns:
        Quality score (0-100)
    """
    from config.settings import QUALITY_WEIGHTS

    score = 0

    if contact_data.get('website'):
        score += QUALITY_WEIGHTS['website']

    if validate_email(contact_data.get('email')):
        score += QUALITY_WEIGHTS['email']

    if validate_phone(contact_data.get('phone')):
        score += QUALITY_WEIGHTS['phone']

    if validate_url(contact_data.get('linkedin')):
        score += QUALITY_WEIGHTS['linkedin']

    if contact_data.get('contact_person'):
        score += QUALITY_WEIGHTS['contact_person']

    return min(score, 100)  # Cap at 100
