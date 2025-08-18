#!/usr/bin/env python3

import asyncio
import sys
import os

# Add the scraper to the path
sys.path.append('../API Scraper V2')
from interactive_scraper import PartsTownExplorer

async def main():
    explorer = PartsTownExplorer()
    models = await explorer.get_models_for_manufacturer('3m', 'PT_CAT1050')
    return models

result = asyncio.run(main())
import json
print(json.dumps(result))