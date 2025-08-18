#!/usr/bin/env python3
"""
Remove cache files with empty model arrays to restore app functionality.
This will allow the app to show 404 for missing manufacturers rather than empty lists.
"""

import json
import os

# Cache directories
CACHE_DIR = os.path.join(os.path.dirname(__file__), 'cache')
MODELS_CACHE_DIR = os.path.join(CACHE_DIR, 'models')

def find_and_remove_empty_cache_files():
    """Find and remove cache files with empty model arrays"""
    empty_files = []
    removed_count = 0
    
    # Check all cache files
    for filename in os.listdir(MODELS_CACHE_DIR):
        if filename.endswith('.json'):
            filepath = os.path.join(MODELS_CACHE_DIR, filename)
            
            with open(filepath, 'r') as f:
                data = json.load(f)
                
            # Check if models array is empty
            if len(data.get('models', [])) == 0:
                empty_files.append({
                    'file': filename,
                    'manufacturer': data.get('manufacturer', {}).get('name', 'Unknown'),
                    'source': data.get('source', 'unknown')
                })
                
                # Only remove if it was created by the complete_cache_script
                if data.get('source') == 'complete_cache_script':
                    os.remove(filepath)
                    removed_count += 1
    
    return empty_files, removed_count

def main():
    print("=" * 60)
    print("REMOVE EMPTY CACHE FILES")
    print("=" * 60)
    
    empty_files, removed = find_and_remove_empty_cache_files()
    
    print(f"\n📊 Found {len(empty_files)} empty cache files")
    print(f"🗑️  Removed {removed} files created by complete_cache_script")
    
    if removed > 0:
        print("\n✅ Empty cache files removed!")
        print("   The app will now show 404 errors for these manufacturers")
        print("   instead of empty model lists.")
        
        # Update cache timestamp
        timestamp_file = os.path.join(CACHE_DIR, 'cache_timestamp.json')
        if os.path.exists(timestamp_file):
            with open(timestamp_file, 'r') as f:
                timestamp_data = json.load(f)
            
            # Count remaining cache files
            remaining = len([f for f in os.listdir(MODELS_CACHE_DIR) if f.endswith('.json')])
            
            timestamp_data['total_models_cached'] = remaining
            timestamp_data['cache_completion'] = f"{(remaining / 489) * 100:.1f}%"
            timestamp_data['note'] = "Removed empty cache files"
            
            with open(timestamp_file, 'w') as f:
                json.dump(timestamp_data, f, indent=2)
            
            print(f"\n📈 Cache coverage: {remaining}/489 ({(remaining / 489) * 100:.1f}%)")
    
    # Show first 10 removed
    if removed > 0:
        print("\n🔍 First 10 removed manufacturers:")
        for i, item in enumerate(empty_files[:10]):
            if item['source'] == 'complete_cache_script':
                print(f"   - {item['manufacturer']} ({item['file']})")
        
        if removed > 10:
            print(f"   ... and {removed - 10} more")

if __name__ == "__main__":
    main()