#!/usr/bin/env python3

import subprocess
import json

script = '''
import asyncio
import sys
import os
sys.path.append("../API Scraper V2")
from interactive_scraper import PartsTownExplorer

async def main():
    explorer = PartsTownExplorer()
    models = await explorer.get_models_for_manufacturer("hardt", "PT_CAT321892")
    return models

result = asyncio.run(main())
import json
print(json.dumps(result))
'''

result = subprocess.run(['python3', '-c', script], capture_output=True, text=True, timeout=60)

# Extract JSON from output
output = result.stdout
print("Raw output preview:", output[:200])

start = output.rfind('[')
if start != -1:
    json_str = output[start:]
    try:
        models = json.loads(json_str)
        print(f'Found {len(models)} models')
        if models:
            print('First model:', models[0])
    except:
        print("Failed to parse JSON")
        print("JSON string:", json_str[:200])
else:
    print("No JSON found in output")