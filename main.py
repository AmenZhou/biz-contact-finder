"""
Main orchestration script for company contact info scraper
"""
import logging
import pandas as pd
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

import re

from utils.logger import setup_logger
from utils.validators import calculate_quality_score
from scrapers.google_places import GooglePlacesScraper
from scrapers.website_scraper import WebsiteScraper
from scrapers.llm_parser import LLMContactParser
from config.settings import INPUT_CSV, OUTPUT_CSV, PROGRESS_FILE


def extract_name_from_email(email: str) -> Optional[str]:
    """
    Extract person name from email address pattern

    Examples:
        john.doe@company.com -> John Doe
        jdoe@company.com -> None (can't determine)
        michael.colacino@jll.com -> Michael Colacino
    """
    if not email or '@' not in email:
        return None

    local_part = email.split('@')[0].lower()

    # Skip generic emails
    generic_prefixes = ['info', 'contact', 'hello', 'support', 'sales', 'admin',
                       'help', 'service', 'care', 'team', 'office', 'hr', 'jobs',
                       'careers', 'press', 'media', 'marketing', 'events']
    if local_part in generic_prefixes:
        return None

    # Try firstname.lastname pattern
    if '.' in local_part:
        parts = local_part.split('.')
        if len(parts) == 2:
            first_name = parts[0].capitalize()
            last_name = parts[1].capitalize()
            # Skip if parts are too short (likely initials)
            if len(parts[0]) > 1 and len(parts[1]) > 1:
                return f"{first_name} {last_name}"

    # Try firstname_lastname pattern
    if '_' in local_part:
        parts = local_part.split('_')
        if len(parts) == 2:
            first_name = parts[0].capitalize()
            last_name = parts[1].capitalize()
            if len(parts[0]) > 1 and len(parts[1]) > 1:
                return f"{first_name} {last_name}"

    return None

# Setup logging
logger = setup_logger()


class ContactInfoScraper:
    """Main orchestration class for scraping contact information"""

    def __init__(self):
        """Initialize all scrapers"""
        logger.info("Initializing Contact Info Scraper")

        self.google_scraper = GooglePlacesScraper()
        self.web_scraper = WebsiteScraper()
        self.llm_parser = LLMContactParser()

        self.progress = self.load_progress()

    def load_progress(self) -> Dict:
        """Load progress from previous runs"""
        if Path(PROGRESS_FILE).exists():
            try:
                with open(PROGRESS_FILE, 'r') as f:
                    progress = json.load(f)
                    logger.info(f"Loaded progress: {len(progress)} companies processed")
                    return progress
            except Exception as e:
                logger.warning(f"Could not load progress file: {e}")
        return {}

    def save_progress(self):
        """Save current progress"""
        try:
            Path(PROGRESS_FILE).parent.mkdir(parents=True, exist_ok=True)
            with open(PROGRESS_FILE, 'w') as f:
                json.dump(self.progress, f, indent=2)
            logger.debug("Progress saved")
        except Exception as e:
            logger.error(f"Failed to save progress: {e}")

    def process_company(self, row: pd.Series) -> Dict:
        """
        Process a single company to extract contact information

        Args:
            row: Pandas series with company data

        Returns:
            Dictionary with enriched contact information
        """
        company_name = row['Name']
        address = row.get('Addr', '')

        logger.info(f"\n{'='*60}")
        logger.info(f"Processing: {company_name}")
        logger.info(f"{'='*60}")

        # Check if already processed
        if company_name in self.progress:
            logger.info(f"Skipping {company_name} (already processed)")
            return self.progress[company_name]

        # Initialize result with original data
        result = {
            'name': company_name,
            'original_phone': row.get('Phone', ''),
            'original_address': address,
            'type': row.get('Type', ''),
            'stars': row.get('Starts', ''),  # Note: typo in original CSV
            'reviews': row.get('Reviews', ''),
            'website': None,
            'email': None,
            'email_contact_name': None,
            'email_contact_title': None,
            'email_secondary': None,
            'phone': None,
            'phone_contact_name': None,
            'phone_contact_title': None,
            'phone_secondary': None,
            'linkedin': None,
            'twitter': None,
            'facebook': None,
            'instagram': None,
            'contact_person': None,
            'contact_title': None,
            'address': address,
            'quality_score': 0,
            'last_updated': datetime.now().isoformat(),
            'data_source': []
        }

        # Step 1: Get website from Google Places
        logger.info("Step 1: Checking Google Places...")
        google_info = self.google_scraper.search_company(company_name, address)
        if google_info:
            result['website'] = google_info.get('website')
            result['phone'] = google_info.get('phone') or result['original_phone']
            result['address'] = google_info.get('address') or address
            result['data_source'].append('google_places')
            logger.info(f"✓ Found website: {result['website']}")
        else:
            logger.info("✗ No Google Places data found")

        # Step 2: Scrape website if available
        if result['website']:
            logger.info(f"Step 2: Scraping website: {result['website']}")
            scraped_data = self.web_scraper.scrape_multiple_pages(result['website'])

            if scraped_data:
                logger.info(f"✓ Successfully scraped website ({len(scraped_data.get('pages_fetched', []))} pages)")

                # Step 3: Parse with LLM
                logger.info("Step 3: Parsing with LLM...")
                contact_info = self.llm_parser.parse_contact_info(
                    scraped_data['html'],
                    company_name
                )

                if contact_info:
                    # Merge LLM results
                    result.update({
                        'email': contact_info.get('email'),
                        'email_contact_name': contact_info.get('email_contact_name'),
                        'email_contact_title': contact_info.get('email_contact_title'),
                        'email_secondary': contact_info.get('email_secondary'),
                        'linkedin': contact_info.get('linkedin'),
                        'twitter': contact_info.get('twitter'),
                        'facebook': contact_info.get('facebook'),
                        'instagram': contact_info.get('instagram'),
                        'contact_person': contact_info.get('contact_person'),
                        'contact_title': contact_info.get('contact_title'),
                    })

                    # Use LLM phone if better than Google Places
                    if contact_info.get('phone') and not result['phone']:
                        result['phone'] = contact_info['phone']
                        result['phone_contact_name'] = contact_info.get('phone_contact_name')
                        result['phone_contact_title'] = contact_info.get('phone_contact_title')

                    if contact_info.get('phone_secondary'):
                        result['phone_secondary'] = contact_info['phone_secondary']

                    result['data_source'].append('llm_parser')
                    logger.info(f"✓ LLM parsing successful")
                else:
                    logger.warning("✗ LLM parsing failed")

                # Step 4: Merge regex-extracted data as backup/supplement
                extracted_emails = scraped_data.get('extracted_emails', [])
                extracted_social = scraped_data.get('extracted_social', {})

                # Use regex-extracted email if LLM didn't find one
                if not result['email'] and extracted_emails:
                    result['email'] = extracted_emails[0]
                    result['data_source'].append('regex_email')
                    logger.info(f"✓ Found email via regex: {result['email']}")

                # Use secondary email from regex if available
                if not result['email_secondary'] and len(extracted_emails) > 1:
                    result['email_secondary'] = extracted_emails[1]

                # Extract name from email pattern if not already set
                if result['email'] and not result['email_contact_name']:
                    extracted_name = extract_name_from_email(result['email'])
                    if extracted_name:
                        result['email_contact_name'] = extracted_name
                        logger.info(f"✓ Extracted name from email: {extracted_name}")

                # Use regex-extracted social links if LLM didn't find them
                for social_key in ['linkedin', 'twitter', 'facebook', 'instagram']:
                    if not result.get(social_key) and extracted_social.get(social_key):
                        result[social_key] = extracted_social[social_key]
                        if 'regex_social' not in result['data_source']:
                            result['data_source'].append('regex_social')

                # Log final results
                if result['email']:
                    contact_info_str = result['email']
                    if result.get('email_contact_name'):
                        contact_info_str += f" ({result['email_contact_name']}"
                        if result.get('email_contact_title'):
                            contact_info_str += f", {result['email_contact_title']}"
                        contact_info_str += ")"
                    logger.info(f"  Email: {contact_info_str}")
                else:
                    logger.info(f"  Email: None")

                if result['phone']:
                    phone_info_str = result['phone']
                    if result.get('phone_contact_name'):
                        phone_info_str += f" ({result['phone_contact_name']}"
                        if result.get('phone_contact_title'):
                            phone_info_str += f", {result['phone_contact_title']}"
                        phone_info_str += ")"
                    logger.info(f"  Phone: {phone_info_str}")
                else:
                    logger.info(f"  Phone: None")

                logger.info(f"  LinkedIn: {result['linkedin']}")
                if result.get('instagram'):
                    logger.info(f"  Instagram: {result['instagram']}")
            else:
                logger.warning("✗ Website scraping failed")
        else:
            logger.info("Step 2-3: Skipped (no website)")

        # Calculate quality score
        result['quality_score'] = calculate_quality_score(result)
        logger.info(f"Quality Score: {result['quality_score']}/100")

        # Save to progress
        self.progress[company_name] = result
        self.save_progress()

        return result

    def run(self, limit: Optional[int] = None):
        """
        Main execution method

        Args:
            limit: Optional limit on number of companies to process (for testing)
        """
        logger.info("Starting Contact Info Scraper")
        logger.info(f"Input file: {INPUT_CSV}")
        logger.info(f"Output file: {OUTPUT_CSV}")

        # Load input CSV
        try:
            df = pd.read_csv(INPUT_CSV)
            logger.info(f"Loaded {len(df)} companies from CSV")
        except Exception as e:
            logger.error(f"Failed to load input CSV: {e}")
            return

        # Apply limit if specified
        if limit:
            df = df.head(limit)
            logger.info(f"Processing limited to {limit} companies")

        # Process each company
        results = []
        for idx, row in df.iterrows():
            try:
                result = self.process_company(row)
                results.append(result)
            except Exception as e:
                logger.error(f"Error processing company at row {idx}: {e}", exc_info=True)
                continue

        # Create output DataFrame
        if results:
            output_df = pd.DataFrame(results)

            # Reorder columns for better readability
            column_order = [
                'name', 'type', 'website',
                'email', 'email_contact_name', 'email_contact_title', 'email_secondary',
                'phone', 'phone_contact_name', 'phone_contact_title', 'phone_secondary',
                'address',
                'linkedin', 'twitter', 'facebook', 'instagram',
                'contact_person', 'contact_title',
                'stars', 'reviews',
                'quality_score', 'data_source', 'last_updated'
            ]

            # Only include columns that exist
            column_order = [col for col in column_order if col in output_df.columns]
            output_df = output_df[column_order]

            # Save to CSV
            try:
                Path(OUTPUT_CSV).parent.mkdir(parents=True, exist_ok=True)
                output_df.to_csv(OUTPUT_CSV, index=False)
                logger.info(f"\n{'='*60}")
                logger.info(f"✓ SUCCESS! Output saved to: {OUTPUT_CSV}")
                logger.info(f"{'='*60}")

                # Print summary statistics
                self.print_summary(output_df)

            except Exception as e:
                logger.error(f"Failed to save output CSV: {e}")
        else:
            logger.warning("No results to save")

    def print_summary(self, df: pd.DataFrame):
        """Print summary statistics"""
        total = len(df)

        logger.info("\n📊 SUMMARY STATISTICS")
        logger.info(f"{'='*60}")
        logger.info(f"Total companies processed: {total}")
        logger.info(f"Companies with website: {df['website'].notna().sum()} ({df['website'].notna().sum()/total*100:.1f}%)")
        logger.info(f"Companies with email: {df['email'].notna().sum()} ({df['email'].notna().sum()/total*100:.1f}%)")
        logger.info(f"Companies with phone: {df['phone'].notna().sum()} ({df['phone'].notna().sum()/total*100:.1f}%)")
        logger.info(f"Companies with LinkedIn: {df['linkedin'].notna().sum()} ({df['linkedin'].notna().sum()/total*100:.1f}%)")
        logger.info(f"Average quality score: {df['quality_score'].mean():.1f}/100")
        logger.info(f"{'='*60}\n")


def main():
    """Entry point"""
    scraper = ContactInfoScraper()

    # Process all companies
    scraper.run()  # Full batch


if __name__ == '__main__':
    main()
