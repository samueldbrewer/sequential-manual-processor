#!/usr/bin/env python3

import subprocess
import json
import os

# Run the scraper in a subprocess
script = """
import asyncio
import sys
import os
sys.path.append('../API Scraper V2')
from interactive_scraper import PartsTownExplorer

async def main():
    explorer = PartsTownExplorer()
    models = await explorer.get_models_for_manufacturer('hardt', 'PT_CAT321892')
    return models

result = asyncio.run(main())
import json
print(json.dumps(result))
"""

try:
    result = subprocess.run(
        ['python3', '-c', script],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=os.path.dirname(__file__)
    )
    
    print("Return code:", result.returncode)
    print("\nSTDOUT Length:", len(result.stdout))
    print("STDOUT Preview:", result.stdout[:500])
    print("\nSTDERR:", result.stderr[:500] if result.stderr else "None")
    
    if result.returncode == 0:
        # Extract JSON from output (might have debug messages)
        output = result.stdout
        # Find the JSON array in the output
        try:
            # Look for JSON array starting with [
            start = output.rfind('[')
            print(f"\nFound '[' at position: {start}")
            if start != -1:
                json_str = output[start:]
                print(f"JSON string length: {len(json_str)}")
                print(f"JSON string preview: {json_str[:200]}")
                models = json.loads(json_str)
                print(f"\nSuccessfully parsed {len(models)} models")
                if models:
                    print("First model:", models[0])
        except Exception as e:
            print(f"Error parsing JSON: {e}")
    else:
        print(f"Error getting models: {result.stderr}")
        
except Exception as e:
    print(f"Exception getting models: {e}")