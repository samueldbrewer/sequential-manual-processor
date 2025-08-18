#!/usr/bin/env python3
"""
Generate all potential manual links for a model
Based on the pattern: /modelManual/{MANUFACTURER_PREFIX}-{MODEL_CODE}_{TYPE}.pdf
"""

def get_manufacturer_prefix(manufacturer_name):
    """Get the manufacturer prefix from the name"""
    # Common manufacturer prefixes based on what we've seen
    prefix_map = {
        'henny-penny': 'HEN',
        'apw-wyott': 'APW',
        'accutemp': 'ACC',
        'delfield': 'DEL',
        'frymaster': 'FRY',
        'vulcan': 'VUL',
        'hobart': 'HOB',
        'wells': 'WEL',
        'star': 'STA',
        'true': 'TRU',
        'beverage-air': 'BEV',
        'alto-shaam': 'ALT',
        'garland': 'GAR',
        'pitco': 'PIT',
        'blodgett': 'BLO',
        'cleveland': 'CLE',
        'lincoln': 'LIN',
        'middleby': 'MID',
        'rational': 'RAT',
        'southbend': 'SOU',
    }
    
    # Try to get from map, otherwise use first 3 letters uppercase
    manufacturer_lower = manufacturer_name.lower()
    if manufacturer_lower in prefix_map:
        return prefix_map[manufacturer_lower]
    else:
        # Take first 3 letters and uppercase
        clean_name = ''.join(c for c in manufacturer_name if c.isalnum())
        return clean_name[:3].upper() if clean_name else 'UNK'

def generate_manual_links(manufacturer_uri, model_code, manufacturer_name=None):
    """Generate all potential manual links for a model"""
    
    # Get manufacturer prefix
    if not manufacturer_name:
        manufacturer_name = manufacturer_uri
    prefix = get_manufacturer_prefix(manufacturer_uri)
    
    # Manual types
    manual_types = [
        ('spm', 'Service & Parts Manual'),
        ('iom', 'Installation & Operation Manual'),
        ('pm', 'Parts Manual'),
        ('wd', 'Wiring Diagrams'),
        ('sm', 'Service Manual')
    ]
    
    manuals = []
    
    # Generate links for each manual type
    for type_code, type_name in manual_types:
        # For Henny Penny, use PF prefix for numeric models
        if manufacturer_uri == 'henny-penny' and model_code.isdigit():
            # Use PF prefix for numeric models
            model_formatted = f'PF{model_code.upper()}'
        else:
            # Use uppercase model code
            model_formatted = model_code.upper()
        
        # Generate the link
        link = f'/modelManual/{prefix}-{model_formatted}_{type_code}.pdf'
        
        manuals.append({
            'type': type_code,
            'title': type_name,
            'link': link,
            'url': link,
            'full_url': f'https://www.partstown.com{link}'
        })
    
    return manuals

if __name__ == "__main__":
    # Test with Henny Penny 500
    manuals = generate_manual_links('henny-penny', '500', 'Henny Penny')
    import json
    print(json.dumps(manuals, indent=2))