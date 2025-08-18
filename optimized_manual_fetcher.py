#!/usr/bin/env python3
"""
Optimized PartsTown Manual URL Fetcher
Based on pattern analysis of manufacturer naming conventions

This implementation combines pattern-based URL generation with fallback scraping
for optimal performance and reliability.
"""

import re
import time
import json
import requests
from typing import List, Dict, Tuple, Optional
from fetch_manuals_subprocess import fetch_manuals_for_model

class PartsTownManualFetcher:
    """
    Optimized manual fetcher combining patterns and scraping
    """
    
    def __init__(self, cache_ttl_hours: int = 24):
        self.cache = {}
        self.cache_ttl = cache_ttl_hours * 3600  # Convert to seconds
        self.pattern_cache = {}
        
        # Manufacturer prefix patterns discovered from analysis
        self.manufacturer_prefixes = {
            'henny-penny': 'HEN-',
            'apw-wyott': 'APW-',
            'delfield': 'DEL-',
            'frymaster': 'FM-',
            'true': 'TRUE-',
            # Add more as discovered
        }
        
        # Manual type suffixes
        self.manual_types = ['spm', 'iom', 'pm', 'wd', 'sm']
        
        # Known pattern templates by manufacturer
        self.pattern_templates = {
            'true': [
                '{prefix}{model}_{type}',           # TRUE-T-23_pm
                '{prefix}{model_abbrev}_{type}',    # TRUE-GDM_iom (gdm-49 -> GDM)
                '{prefix}TSSUSeries_{type}',        # TRUE-TSSUSeries_pm
                '{prefix}TFP-TPP-TWT-TPP_{type}',   # TRUE-TFP-TPP-TWT-TPP_iom
            ],
            'henny-penny': [
                '{prefix}PF{model}_{type}',         # HEN-PF500_spm
                '{prefix}{model}-600_{type}',       # HEN-500-600_pm
            ],
            'delfield': [
                '{prefix}{model}_{type}',           # DEL-4427N_pm
                '{prefix}4400SERIES_{type}',        # DEL-4400SERIES_pm
                '{prefix}4400series_{type}',        # DEL-4400series_iom (case variation)
                '{prefix}400-4000SERIES_{type}',    # DEL-400-4000SERIES_wd
            ],
            'frymaster': [
                '{prefix}{model}_{type}',           # FM-MJ35_pm
                '{prefix}{model_upper}_{type}',     # FM-RE14_spm
                '{prefix}{model_series}_wd',        # FM-MJ35-40-45-50_wd
                '{prefix}Performance-Pro-Series-{model}-*_{type}',  # Complex patterns
                '{prefix}Pro-{model_upper}-Series-*_{type}',
                '{prefix}{model_upper}-Series-*_{type}',
            ],
            'apw-wyott': [
                '{prefix}{model}_{type}',           # APW-M-83_pm
                '{prefix}{model_variant}_{type}',   # APW-AT-5_pm (at-10 -> AT-5)
            ]
        }
    
    def get_manuals(self, manufacturer_uri: str, model_code: str) -> List[Dict]:
        """
        Get manual URLs using optimized approach
        
        Args:
            manufacturer_uri: Manufacturer URI slug
            model_code: Model code
            
        Returns:
            List of manual dictionaries with type, title, and link
        """
        cache_key = f"{manufacturer_uri}_{model_code}"
        
        # Check cache first
        if self._is_cached(cache_key):
            print(f"Cache hit for {cache_key}")
            return self.cache[cache_key]['data']
        
        manuals = []
        
        # Try pattern-based approach first for known manufacturers
        if manufacturer_uri in self.manufacturer_prefixes:
            print(f"Trying pattern-based approach for {manufacturer_uri}")
            manuals = self._fetch_using_patterns(manufacturer_uri, model_code)
            
            if manuals:
                print(f"Pattern-based approach found {len(manuals)} manuals")
                self._cache_result(cache_key, manuals)
                return manuals
        
        # Fallback to scraping
        print(f"Falling back to scraping for {manufacturer_uri} {model_code}")
        manuals = fetch_manuals_for_model(manufacturer_uri, model_code)
        
        # Learn patterns from scraped results for future optimization
        if manuals:
            self._learn_patterns(manufacturer_uri, model_code, manuals)
        
        self._cache_result(cache_key, manuals)
        return manuals
    
    def _fetch_using_patterns(self, manufacturer_uri: str, model_code: str) -> List[Dict]:
        """
        Generate URL candidates using patterns and validate them
        """
        candidates = self._generate_url_candidates(manufacturer_uri, model_code)
        valid_manuals = []
        
        for candidate_url, manual_type in candidates:
            if self._url_exists(candidate_url):
                valid_manuals.append({
                    'type': manual_type,
                    'title': self._get_manual_title(manual_type),
                    'link': candidate_url,
                    'text': 'View Manual'
                })
        
        return valid_manuals
    
    def _generate_url_candidates(self, manufacturer_uri: str, model_code: str) -> List[Tuple[str, str]]:
        """
        Generate URL candidates based on discovered patterns
        """
        candidates = []
        prefix = self.manufacturer_prefixes.get(manufacturer_uri, '')
        
        if not prefix or manufacturer_uri not in self.pattern_templates:
            return candidates
        
        templates = self.pattern_templates[manufacturer_uri]
        model_variants = self._generate_model_variants(model_code)
        
        for template in templates:
            for manual_type in self.manual_types:
                for variant_name, variant_value in model_variants.items():
                    try:
                        # Handle wildcard patterns
                        if '*' in template:
                            # Skip wildcard patterns for now - too complex for simple generation
                            continue
                        
                        filename = template.format(
                            prefix=prefix,
                            model=variant_value,
                            model_upper=variant_value.upper(),
                            model_abbrev=self._abbreviate_model(variant_value),
                            model_series=self._get_series_variant(variant_value),
                            model_variant=self._get_model_variant(manufacturer_uri, variant_value),
                            type=manual_type
                        )
                        
                        url = f"/modelManual/{filename}.pdf"
                        candidates.append((url, manual_type))
                        
                    except (KeyError, ValueError):
                        # Template formatting failed, skip this combination
                        continue
        
        return list(set(candidates))  # Remove duplicates
    
    def _generate_model_variants(self, model_code: str) -> Dict[str, str]:
        """
        Generate different model code variants
        """
        variants = {
            'original': model_code,
            'upper': model_code.upper(),
            'lower': model_code.lower(),
            'no_hyphens': model_code.replace('-', ''),
            'no_hyphens_upper': model_code.replace('-', '').upper(),
            'underscores': model_code.replace('-', '_').upper(),
        }
        
        # Remove numeric suffixes for abbreviations
        if re.search(r'\d', model_code):
            alpha_part = re.sub(r'\d+.*', '', model_code).upper()
            if alpha_part:
                variants['alpha_only'] = alpha_part
        
        return variants
    
    def _abbreviate_model(self, model_code: str) -> str:
        """
        Create abbreviated version of model code
        Examples: gdm-49 -> GDM, t-23 -> T
        """
        # Extract alphabetic part before numbers
        match = re.match(r'([a-zA-Z]+)', model_code)
        if match:
            return match.group(1).upper()
        return model_code.upper()
    
    def _get_series_variant(self, model_code: str) -> str:
        """
        Generate series-based variant
        Example: mj35 -> MJ35-40-45-50
        """
        # This would need manufacturer-specific logic
        # For now, return uppercase version
        return model_code.upper()
    
    def _get_model_variant(self, manufacturer_uri: str, model_code: str) -> str:
        """
        Get manufacturer-specific model variant
        Example: APW at-10 -> AT-5
        """
        # Specific cases found in analysis
        if manufacturer_uri == 'apw-wyott' and model_code.lower() == 'at-10':
            return 'AT-5'
        
        return model_code.upper()
    
    def _url_exists(self, url: str) -> bool:
        """
        Check if a manual URL exists by making HEAD request
        """
        try:
            full_url = f"https://www.partstown.com{url}"
            response = requests.head(full_url, timeout=10, allow_redirects=True)
            return response.status_code == 200
        except requests.RequestException:
            return False
    
    def _get_manual_title(self, manual_type: str) -> str:
        """
        Get display title for manual type
        """
        titles = {
            'spm': 'Service & Parts Manual',
            'iom': 'Installation & Operation Manual',
            'pm': 'Parts Manual',
            'wd': 'Wiring Diagrams',
            'sm': 'Service Manual'
        }
        return titles.get(manual_type, 'Manual')
    
    def _is_cached(self, cache_key: str) -> bool:
        """
        Check if result is in cache and not expired
        """
        if cache_key not in self.cache:
            return False
        
        cached_time = self.cache[cache_key]['timestamp']
        return (time.time() - cached_time) < self.cache_ttl
    
    def _cache_result(self, cache_key: str, manuals: List[Dict]):
        """
        Cache the result with timestamp
        """
        self.cache[cache_key] = {
            'data': manuals,
            'timestamp': time.time()
        }
    
    def _learn_patterns(self, manufacturer_uri: str, model_code: str, manuals: List[Dict]):
        """
        Learn patterns from successful scraping results
        """
        if manufacturer_uri not in self.pattern_cache:
            self.pattern_cache[manufacturer_uri] = {}
        
        for manual in manuals:
            url = manual.get('link', '')
            if '/modelManual/' in url:
                filename = url.split('/modelManual/')[1].split('?')[0]  # Remove version param
                filename_no_ext = filename.replace('.pdf', '')
                
                # Store pattern for future analysis
                pattern_key = f"{model_code}_{manual['type']}"
                self.pattern_cache[manufacturer_uri][pattern_key] = filename_no_ext
        
        # Optionally save to file for persistence
        self._save_pattern_cache()
    
    def _save_pattern_cache(self):
        """
        Save learned patterns to file
        """
        try:
            with open('learned_patterns.json', 'w') as f:
                json.dump(self.pattern_cache, f, indent=2)
        except Exception as e:
            print(f"Failed to save pattern cache: {e}")
    
    def get_cache_stats(self) -> Dict:
        """
        Get cache statistics
        """
        return {
            'cache_size': len(self.cache),
            'pattern_cache_size': len(self.pattern_cache),
            'manufacturers_with_patterns': len(self.manufacturer_prefixes)
        }


def test_optimized_fetcher():
    """
    Test the optimized fetcher with our analysis cases
    """
    fetcher = PartsTownManualFetcher()
    
    test_cases = [
        ("true", "t-23"),
        ("frymaster", "mj35"),
        ("delfield", "4427n"),
        ("henny-penny", "500"),
        ("apw-wyott", "m-83")
    ]
    
    print("Testing Optimized Manual Fetcher")
    print("=" * 50)
    
    for manufacturer, model in test_cases:
        print(f"\nTesting {manufacturer} / {model}")
        print("-" * 30)
        
        start_time = time.time()
        manuals = fetcher.get_manuals(manufacturer, model)
        elapsed = time.time() - start_time
        
        print(f"Found {len(manuals)} manuals in {elapsed:.2f}s")
        for manual in manuals:
            print(f"  - {manual['type']}: {manual['link']}")
    
    print(f"\nCache Stats: {fetcher.get_cache_stats()}")


if __name__ == "__main__":
    test_optimized_fetcher()