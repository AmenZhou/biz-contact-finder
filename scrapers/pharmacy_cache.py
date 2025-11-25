"""
Pharmacy data caching system for cost optimization.
Caches pharmacy search results for 30 days to avoid redundant API calls.
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple


class PharmacyCache:
    """Cache system for pharmacy search results."""

    def __init__(self, cache_file: str = 'data/pharmacy_cache.json', ttl_days: int = 30):
        """
        Initialize the pharmacy cache.

        Args:
            cache_file: Path to the cache JSON file
            ttl_days: Time-to-live in days (default: 30)
        """
        self.cache_file = Path(cache_file)
        self.ttl_days = ttl_days
        self.cache_data = self._load_cache()

    def _load_cache(self) -> Dict:
        """Load cache from file."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Failed to load cache file: {e}")
                return {'version': '1.0', 'entries': {}}
        return {'version': '1.0', 'entries': {}}

    def _save_cache(self):
        """Save cache to file."""
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.cache_data, f, indent=2, ensure_ascii=False)

    def _generate_key(self, search_type: str, **params) -> str:
        """
        Generate a unique cache key for a search.

        Args:
            search_type: Type of search ('grid', 'text', 'nearby')
            **params: Search parameters (lat, lng, bounds, query, etc.)

        Returns:
            Unique hash key for the search
        """
        # Sort params for consistent hashing
        params_str = json.dumps(params, sort_keys=True)
        key_string = f"{search_type}:{params_str}"
        return hashlib.md5(key_string.encode()).hexdigest()

    def _is_expired(self, timestamp: str) -> bool:
        """Check if a cache entry is expired."""
        try:
            cached_time = datetime.fromisoformat(timestamp)
            expiry_time = cached_time + timedelta(days=self.ttl_days)
            return datetime.now() > expiry_time
        except (ValueError, TypeError):
            return True  # Invalid timestamp, consider expired

    def get(self, search_type: str, **params) -> Optional[List[Dict]]:
        """
        Get cached results for a search.

        Args:
            search_type: Type of search ('grid', 'text', 'nearby')
            **params: Search parameters

        Returns:
            Cached pharmacy list if found and not expired, None otherwise
        """
        key = self._generate_key(search_type, **params)
        entry = self.cache_data['entries'].get(key)

        if not entry:
            return None

        if self._is_expired(entry['timestamp']):
            # Remove expired entry
            del self.cache_data['entries'][key]
            self._save_cache()
            return None

        return entry['pharmacies']

    def set(self, search_type: str, pharmacies: List[Dict], **params):
        """
        Cache results for a search.

        Args:
            search_type: Type of search ('grid', 'text', 'nearby')
            pharmacies: List of pharmacy dictionaries
            **params: Search parameters
        """
        key = self._generate_key(search_type, **params)

        self.cache_data['entries'][key] = {
            'timestamp': datetime.now().isoformat(),
            'search_type': search_type,
            'params': params,
            'pharmacies': pharmacies,
            'count': len(pharmacies)
        }

        self._save_cache()

    def get_district_results(self, district_num: int) -> Optional[Tuple[List[Dict], datetime]]:
        """
        Get all cached results for a specific district.

        Args:
            district_num: District number

        Returns:
            Tuple of (pharmacies list, cache timestamp) if found, None otherwise
        """
        district_key = f"district_{district_num}"

        for key, entry in self.cache_data['entries'].items():
            if entry.get('params', {}).get('district_num') == district_num:
                if not self._is_expired(entry['timestamp']):
                    timestamp = datetime.fromisoformat(entry['timestamp'])
                    return entry['pharmacies'], timestamp

        return None

    def cache_district(self, district_num: int, pharmacies: List[Dict]):
        """
        Cache all results for a district.

        Args:
            district_num: District number
            pharmacies: Complete list of pharmacies for the district
        """
        key = f"district_{district_num}_complete"

        self.cache_data['entries'][key] = {
            'timestamp': datetime.now().isoformat(),
            'search_type': 'district_complete',
            'params': {'district_num': district_num},
            'pharmacies': pharmacies,
            'count': len(pharmacies)
        }

        self._save_cache()

    def invalidate_district(self, district_num: int):
        """
        Invalidate (remove) all cache entries for a district.

        Args:
            district_num: District number
        """
        keys_to_remove = []

        for key, entry in self.cache_data['entries'].items():
            if entry.get('params', {}).get('district_num') == district_num:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del self.cache_data['entries'][key]

        if keys_to_remove:
            self._save_cache()
            print(f"Invalidated {len(keys_to_remove)} cache entries for district {district_num}")

    def clear_expired(self):
        """Remove all expired cache entries."""
        expired_keys = []

        for key, entry in self.cache_data['entries'].items():
            if self._is_expired(entry['timestamp']):
                expired_keys.append(key)

        for key in expired_keys:
            del self.cache_data['entries'][key]

        if expired_keys:
            self._save_cache()
            print(f"Cleared {len(expired_keys)} expired cache entries")

    def clear_all(self):
        """Clear all cache entries."""
        count = len(self.cache_data['entries'])
        self.cache_data['entries'] = {}
        self._save_cache()
        print(f"Cleared all {count} cache entries")

    def get_stats(self) -> Dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        total_entries = len(self.cache_data['entries'])
        expired_count = sum(1 for entry in self.cache_data['entries'].values()
                           if self._is_expired(entry['timestamp']))
        valid_count = total_entries - expired_count

        total_pharmacies = sum(entry['count'] for entry in self.cache_data['entries'].values())

        oldest_entry = None
        newest_entry = None

        for entry in self.cache_data['entries'].values():
            timestamp = entry['timestamp']
            if oldest_entry is None or timestamp < oldest_entry:
                oldest_entry = timestamp
            if newest_entry is None or timestamp > newest_entry:
                newest_entry = timestamp

        return {
            'total_entries': total_entries,
            'valid_entries': valid_count,
            'expired_entries': expired_count,
            'total_pharmacies_cached': total_pharmacies,
            'oldest_entry': oldest_entry,
            'newest_entry': newest_entry,
            'ttl_days': self.ttl_days,
            'cache_file': str(self.cache_file)
        }

    def print_stats(self):
        """Print cache statistics."""
        stats = self.get_stats()

        print("="*60)
        print("PHARMACY CACHE STATISTICS")
        print("="*60)
        print(f"Cache file: {stats['cache_file']}")
        print(f"TTL: {stats['ttl_days']} days")
        print(f"\nEntries:")
        print(f"  Total: {stats['total_entries']}")
        print(f"  Valid: {stats['valid_entries']}")
        print(f"  Expired: {stats['expired_entries']}")
        print(f"\nCached pharmacies: {stats['total_pharmacies_cached']}")

        if stats['oldest_entry']:
            print(f"\nOldest entry: {stats['oldest_entry']}")
        if stats['newest_entry']:
            print(f"Newest entry: {stats['newest_entry']}")
        print("="*60)


if __name__ == '__main__':
    # Example usage and testing
    cache = PharmacyCache()
    cache.print_stats()

    # Optional: Clear expired entries
    # cache.clear_expired()
