#!/usr/bin/env python3
"""
CLI tool for managing the pharmacy cache.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.pharmacy_cache import PharmacyCache


def main():
    """Main CLI function."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Manage pharmacy cache for cost optimization',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show cache statistics
  python scripts/manage_cache.py stats

  # Clear expired entries
  python scripts/manage_cache.py clean

  # Clear all cache
  python scripts/manage_cache.py clear

  # Invalidate a specific district
  python scripts/manage_cache.py invalidate --district 5
        """
    )

    parser.add_argument(
        'action',
        choices=['stats', 'clean', 'clear', 'invalidate'],
        help='Action to perform'
    )

    parser.add_argument(
        '--district',
        type=int,
        help='District number (for invalidate action)'
    )

    parser.add_argument(
        '--cache-file',
        default='data/pharmacy_cache.json',
        help='Path to cache file (default: data/pharmacy_cache.json)'
    )

    parser.add_argument(
        '--ttl',
        type=int,
        default=30,
        help='Cache TTL in days (default: 30)'
    )

    args = parser.parse_args()

    # Initialize cache
    cache = PharmacyCache(cache_file=args.cache_file, ttl_days=args.ttl)

    # Perform action
    if args.action == 'stats':
        cache.print_stats()

    elif args.action == 'clean':
        print("Cleaning expired cache entries...")
        cache.clear_expired()
        print("\nCache stats after cleaning:")
        cache.print_stats()

    elif args.action == 'clear':
        confirm = input("Are you sure you want to clear ALL cache entries? (yes/no): ")
        if confirm.lower() == 'yes':
            cache.clear_all()
            print("\nCache cleared successfully")
            cache.print_stats()
        else:
            print("Cancelled")

    elif args.action == 'invalidate':
        if args.district is None:
            print("Error: --district required for invalidate action")
            sys.exit(1)

        print(f"Invalidating cache for district {args.district}...")
        cache.invalidate_district(args.district)
        print("\nCache stats after invalidation:")
        cache.print_stats()


if __name__ == '__main__':
    main()
