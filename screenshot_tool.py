#!/usr/bin/env python3
"""
Bubble Maps Screenshot Tool
---------------------------
This tool helps generate screenshots of Bubble Maps visualizations directly.
It's useful for testing and debugging the screenshot functionality.

Usage:
  python screenshot_tool.py <token_address> <chain>

Example:
  python screenshot_tool.py 0x1f9840a85d5af5bf1d1762f925bdaddc4201f984 eth
"""

import asyncio
import sys
import os
from utils.screenshot import ScreenshotGenerator
from utils.bubblemaps import BubblemapsAPI

async def main():
    if len(sys.argv) < 3:
        print("Usage: python screenshot_tool.py <token_address> <chain>")
        return
    
    address = sys.argv[1]
    chain = sys.argv[2].lower()
    
    # Initialize the APIs
    screenshot_gen = ScreenshotGenerator()
    bubblemaps = BubblemapsAPI()
    
    # Check if the map is available
    print(f"Checking if map is available for {address} on {chain}...")
    map_available = await bubblemaps.check_map_availability(address, chain)
    print(f"Map available: {map_available}")
    
    # Get the URL
    bubble_map_url = bubblemaps.get_bubble_map_url(address, chain)
    iframe_url = None
    if map_available:
        iframe_url = bubblemaps.get_iframe_url(address, chain)
    
    print(f"Bubble map URL: {bubble_map_url}")
    print(f"iframe URL: {iframe_url}")
    
    # Capture the screenshot
    print(f"Attempting to capture screenshot...")
    screenshot = await screenshot_gen.capture_bubble_map(bubble_map_url, iframe_url)
    
    if screenshot:
        # Save to a file
        output_dir = "screenshots"
        os.makedirs(output_dir, exist_ok=True)
        output_file = f"{output_dir}/{chain}_{address}.png"
        
        with open(output_file, 'wb') as f:
            f.write(screenshot)
        
        print(f"Screenshot saved to {output_file}")
        print(f"File size: {len(screenshot) / 1024:.2f} KB")
    else:
        print("Failed to capture screenshot")

if __name__ == "__main__":
    asyncio.run(main()) 