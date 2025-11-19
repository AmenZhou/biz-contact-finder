"""
Main orchestration script for company contact info scraper
"""
import logging
import pandas as pd
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

from utils.logger import setup_logger
from utils.validators import calculate_quality_score
from scrapers.google_places import GooglePlacesScraper
from scrapers.website_scraper import WebsiteScraper
from scrapers.llm_parser import LLMContactParser
from config.settings import INPUT_CSV, OUTPUT_CSV, PROGRESS_FILE

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
            'email_secondary': None,
            'phone': None,
            'phone_secondary': None,
            'linkedin': None,
            'twitter': None,
            'facebook': None,
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
            scraped_data = self.web_scraper.scrape_contact_info(result['website'])

            if scraped_data:
                logger.info(f"✓ Successfully scraped website")

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
                        'email_secondary': contact_info.get('email_secondary'),
                        'linkedin': contact_info.get('linkedin'),
                        'twitter': contact_info.get('twitter'),
                        'facebook': contact_info.get('facebook'),
                        'contact_person': contact_info.get('contact_person'),
                        'contact_title': contact_info.get('contact_title'),
                    })

                    # Use LLM phone if better than Google Places
                    if contact_info.get('phone') and not result['phone']:
                        result['phone'] = contact_info['phone']

                    if contact_info.get('phone_secondary'):
                        result['phone_secondary'] = contact_info['phone_secondary']

                    result['data_source'].append('llm_parser')
                    logger.info(f"✓ LLM parsing successful")
                    logger.info(f"  Email: {result['email']}")
                    logger.info(f"  Phone: {result['phone']}")
                    logger.info(f"  LinkedIn: {result['linkedin']}")
                else:
                    logger.warning("✗ LLM parsing failed")
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
                'name', 'type', 'website', 'email', 'email_secondary',
                'phone', 'phone_secondary', 'address',
                'linkedin', 'twitter', 'facebook',
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

    # For initial testing, process only 5 companies
    # Remove limit parameter to process all companies
    scraper.run(limit=5)  # Change to scraper.run() for full batch


if __name__ == '__main__':
    main()
