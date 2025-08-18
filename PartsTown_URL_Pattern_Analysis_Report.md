# PartsTown Manual URL Pattern Analysis Report

## Executive Summary

This analysis examines PartsTown manual URL patterns across 5 manufacturers and 15 model combinations to understand the taxonomy and generate a reliable approach for constructing manual URLs programmatically.

**Key Findings:**
- 35 manual URLs found across tested combinations
- Clear manufacturer prefix patterns exist but with significant variations
- Model code transformations are inconsistent and manufacturer-specific
- Multiple manual types per model are common (SPM, IOM, PM, WD)
- Some models share manuals or use series-based naming conventions

## Test Cases and Results

### Models Tested

| Manufacturer | Models Tested | Results |
|-------------|---------------|---------|
| Henny Penny | 500, 320, 600 | 500 & 600 found manuals, 320 not found |
| APW Wyott | at-10, m-83, hd-4 | at-10 & m-83 found manuals, hd-4 not found |
| Delfield | 4427n, 4448n, f17 | 4427n & 4448n found manuals, f17 not found |
| Frymaster | mj35, re14, h55 | All models found manuals |
| True | t-23, gdm-49, tuc-27 | All models found manuals |

**Success Rate:** 12/15 models (80%) had manuals found

### Manual Types Found

- **SPM** - Service & Parts Manual
- **IOM** - Installation & Operation Manual  
- **PM** - Parts Manual
- **WD** - Wiring Diagrams
- **SM** - Service Manual

## URL Pattern Analysis

### Basic URL Structure
```
https://www.partstown.com/modelManual/{FILENAME}_{TYPE}.pdf?v={VERSION}
```

### Manufacturer Prefix Patterns

| Manufacturer | Common Prefixes | Examples |
|-------------|----------------|----------|
| Henny Penny | `HEN-` | `HEN-PF500_spm`, `HEN-500-600_pm` |
| APW Wyott | `APW-` | `APW-M-83_iom`, `APW-AT-5_pm` |
| Delfield | `DEL-` | `DEL-4427N_pm`, `DEL-4400SERIES_pm` |
| Frymaster | `FM-` | `FM-MJ35_pm`, `FM-RE14_spm` |
| True | `TRUE-` | `TRUE-T-23_pm`, `TRUE-GDM_iom` |

### Model Code Transformations

#### Pattern Categories

1. **Direct Match**: Model code appears exactly as entered
   - `TRUE-T-23_pm` (true t-23)
   - `FM-MJ35_pm` (frymaster mj35)

2. **Case Conversion**: Model code converted to uppercase
   - `DEL-4427N_pm` (delfield 4427n → 4427N)
   - `APW-M-83_iom` (apw-wyott m-83 → M-83)

3. **Series Grouping**: Multiple models share same manual
   - `HEN-500-600_pm` (used by both 500 and 600 models)
   - `DEL-4400SERIES_pm` (used by 4427n and 4448n)

4. **Product Line Naming**: Model incorporated into product description
   - `FM-Performance-Pro-Series-MJ35-MJ45-Gas-Fryers-English_iom`
   - `FM-Pro-H55-Series-Fryers-English_spm`

5. **Abbreviated Forms**: Model code abbreviated or modified
   - `TRUE-GDM_iom` (true gdm-49 → GDM)
   - `APW-AT-5_pm` (apw-wyott at-10 → AT-5)

## Key Findings

### 1. Manufacturer Prefix Determination

**Consistent Pattern:** All manufacturers use abbreviated company names as prefixes:
- Henny Penny → `HEN-`
- APW Wyott → `APW-` 
- Delfield → `DEL-`
- Frymaster → `FM-`
- True → `TRUE-`

### 2. Model Code Transformations

**Most Complex Aspect:** Model codes undergo various transformations:
- **Case normalization**: Usually uppercase (90% of cases)
- **Hyphen handling**: Some preserve hyphens, others modify them
- **Series consolidation**: Related models often share manuals
- **Product line integration**: Model codes embedded in descriptive names

### 3. Manual Type Suffixes

**Consistent Pattern:** Manual types use standardized suffixes:
- `_spm` - Service & Parts Manual
- `_iom` - Installation & Operation Manual
- `_pm` - Parts Manual
- `_wd` - Wiring Diagrams
- `_sm` - Service Manual

### 4. Special Cases and Variations

1. **Cross-Model References**: Some models reference manuals from other models
   - APW Wyott AT-10 uses M-83 IOM manual
   - APW Wyott AT-10 uses AT-5 parts manual

2. **Series-Based Naming**: Multiple models covered by single series manual
   - Delfield 4400SERIES covers both 4427n and 4448n
   - Frymaster uses "Performance Pro Series" for multiple models

3. **Multiple Manuals Per Type**: Same model may have multiple manuals of same type
   - Frymaster MJ35 has two different IOM manuals
   - Different vintages or product variations

## Recommendations for URL Generation

### Approach 1: Dynamic Scraping (Recommended)
**Best for accuracy and completeness**

```python
def get_manual_urls(manufacturer_uri, model_code):
    """
    Fetch actual manual URLs by scraping the parts page
    """
    # Current fetch_manuals_subprocess.py approach
    # Pros: 100% accurate, finds all available manuals
    # Cons: Slower, requires web scraping, potential blocking
```

### Approach 2: Pattern-Based Generation with Fallback
**Good for performance with accuracy fallback**

```python
def generate_manual_url_candidates(manufacturer_name, model_code):
    """
    Generate likely URL candidates based on observed patterns
    """
    prefix = get_manufacturer_prefix(manufacturer_name)
    model_variants = generate_model_variants(model_code)
    manual_types = ['spm', 'iom', 'pm', 'wd', 'sm']
    
    candidates = []
    for model_variant in model_variants:
        for manual_type in manual_types:
            candidates.append(f"{prefix}{model_variant}_{manual_type}.pdf")
    
    return candidates

def get_manufacturer_prefix(manufacturer_name):
    prefix_map = {
        'henny-penny': 'HEN-',
        'apw-wyott': 'APW-',
        'delfield': 'DEL-',
        'frymaster': 'FM-',
        'true': 'TRUE-'
        # Add more as needed
    }
    return prefix_map.get(manufacturer_name.lower(), 
                         manufacturer_name.upper().replace('-', '').replace(' ', '')[:4] + '-')

def generate_model_variants(model_code):
    """Generate likely model code variants"""
    variants = [
        model_code.upper(),                    # Direct uppercase
        model_code.upper().replace('-', ''),   # Remove hyphens
        model_code.upper().replace('-', '_'),  # Replace hyphens with underscores
        model_code.lower(),                    # Keep original case
        # Add series patterns if detected
    ]
    return list(set(variants))  # Remove duplicates
```

### Approach 3: Hybrid Method (Optimal)
**Combines speed and accuracy**

```python
def get_manuals_hybrid(manufacturer_uri, model_code):
    """
    1. Try pattern-based generation first
    2. Validate URLs exist (HEAD requests)
    3. Fall back to scraping if no patterns work
    """
    
    # Step 1: Generate candidates
    candidates = generate_manual_url_candidates(manufacturer_uri, model_code)
    
    # Step 2: Test candidates
    valid_urls = []
    for candidate in candidates:
        if url_exists(f"https://www.partstown.com/modelManual/{candidate}"):
            valid_urls.append(candidate)
    
    # Step 3: Fallback to scraping if no candidates work
    if not valid_urls:
        valid_urls = fetch_manuals_for_model(manufacturer_uri, model_code)
    
    return valid_urls
```

## Implementation Recommendations

### For Production Systems

1. **Primary Strategy**: Use dynamic scraping (current approach)
   - Most reliable for finding all available manuals
   - Handles edge cases and special naming conventions
   - Can adapt to site changes automatically

2. **Performance Optimization**: Implement caching
   - Cache successful URL patterns by manufacturer
   - Store results for 24-48 hours to reduce scraping frequency
   - Use pattern learning to improve future predictions

3. **Fallback Strategy**: Pattern-based generation
   - Use for rapid responses when scraping fails
   - Implement for manufacturers with consistent patterns
   - Generate multiple candidates and test existence

### URL Generation Algorithm

```python
def get_manual_urls_optimized(manufacturer_uri, model_code):
    """
    Optimized approach combining caching, patterns, and scraping
    """
    
    # Check cache first
    cache_key = f"{manufacturer_uri}_{model_code}"
    if cache_key in manual_cache:
        return manual_cache[cache_key]
    
    # Try pattern-based approach for known manufacturers
    if manufacturer_uri in PATTERN_SUPPORTED_MANUFACTURERS:
        candidates = generate_url_patterns(manufacturer_uri, model_code)
        valid_urls = validate_url_candidates(candidates)
        if valid_urls:
            manual_cache[cache_key] = valid_urls
            return valid_urls
    
    # Fallback to scraping
    scraped_urls = fetch_manuals_for_model(manufacturer_uri, model_code)
    
    # Learn patterns for future use
    if scraped_urls:
        learn_patterns(manufacturer_uri, model_code, scraped_urls)
    
    manual_cache[cache_key] = scraped_urls
    return scraped_urls
```

## Conclusion

PartsTown manual URLs follow a generally predictable pattern but with significant manufacturer-specific variations. The most reliable approach is dynamic scraping with intelligent caching, complemented by pattern-based generation for performance optimization.

**Key Success Factors:**
1. Maintain current scraping approach for accuracy
2. Implement intelligent caching to reduce load
3. Add pattern-based fallback for performance
4. Learn and adapt patterns over time
5. Handle edge cases gracefully

The analysis shows that while patterns exist, the complexity of transformations and special cases makes pure pattern-based URL generation unreliable. A hybrid approach leveraging both scraping and patterns will provide the best balance of accuracy and performance.