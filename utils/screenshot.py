from playwright.async_api import async_playwright
import asyncio
from typing import Optional, Tuple, Set, Dict, Any
import os
import base64
import requests
import json
from io import BytesIO
from config import SCREENSHOT_WIDTH, SCREENSHOT_HEIGHT, SCREENSHOT_TIMEOUT, DEV_MODE, BUBBLEMAPS_API_BASE, BUBBLEMAPS_API_KEY
from utils.image_helper import optimize_image_for_telegram, create_token_visualization_image
from PIL import Image
import io
import time

# Valid chain identifiers according to Bubblemaps documentation
VALID_CHAINS: Set[str] = {'eth', 'bsc', 'ftm', 'avax', 'cro', 'arbi', 'poly', 'base', 'sol', 'sonic'}

# Rate limiting settings
API_REQUEST_INTERVAL = 1.0  # Seconds between requests
LAST_API_REQUEST_TIME = 0.0

class ScreenshotGenerator:
    def __init__(self):
        self.width = SCREENSHOT_WIDTH
        self.height = SCREENSHOT_HEIGHT
        self.timeout = SCREENSHOT_TIMEOUT
        self.max_retries = 2
        self.api_key = BUBBLEMAPS_API_KEY  # Get API key from config

    async def capture_bubble_map(self, url: str, iframe_url: Optional[str] = None) -> Optional[bytes]:
        """
        Capture a visualization of the bubble map
        
        Args:
            url: The regular Bubblemaps URL
            iframe_url: The iframe URL (if available)
        """
        # In development mode, return a mock screenshot
        if DEV_MODE:
            return self._get_mock_screenshot()
            
        try:
            # Extract token address and chain from URL
            token_parts = url.split('/')
            if len(token_parts) >= 4:
                chain = token_parts[-3].lower()
                address = token_parts[-1].split('?')[0]  # Remove any query parameters
                
                # Validate the chain
                if chain not in VALID_CHAINS:
                    print(f"Invalid chain identifier: {chain}. Must be one of: {', '.join(sorted(VALID_CHAINS))}")
                    return self._get_mock_screenshot()
                    
                print(f"Extracted token: {address} on chain: {chain}")
                
                # PRIORITY METHOD 1: Use map-data API to get visualization data
                try:
                    print(f"Fetching map data for {address} on {chain}")
                    map_data = await self._get_map_data(address, chain)
                    
                    if map_data:
                        # Generate visualization from map data
                        print("Successfully fetched map data, generating visualization")
                        token_name = map_data.get("full_name", "")
                        token_symbol = map_data.get("symbol", "")
                        
                        # Use map data to generate custom visualization
                        image = await self._generate_visualization_from_map_data(map_data)
                        if image:
                            print("Successfully generated visualization from map data")
                            return optimize_image_for_telegram(image)
                except Exception as e:
                    print(f"Map data visualization failed: {e}")
                
                # Get token metadata for better fallback images
                token_name, token_symbol = await self._get_token_metadata(address, chain)
                
                # PRIORITY METHOD 2: Try Playwright with better handling
                try:
                    capture_url = iframe_url if iframe_url else url
                    print(f"Trying Playwright screenshot of URL: {capture_url}")
                    
                    playwright_image = await self._capture_with_playwright(capture_url)
                    if playwright_image:
                        print("Successfully captured with Playwright!")
                        return optimize_image_for_telegram(playwright_image)
                except Exception as e:
                    print(f"Playwright capture failed: {e}")
                
                # FINAL FALLBACK: Create a nice fallback image with token info
                print("All visualization methods failed, creating enhanced fallback image")
                return create_token_visualization_image(token_name, token_symbol, address)
            
            # If we failed to extract token info from URL, use the default fallback
            return self._get_mock_screenshot()
            
        except Exception as e:
            print(f"Error capturing visualization: {e}")
            # Return mock screenshot on error
            return self._get_mock_screenshot()

    async def _get_map_data(self, address: str, chain: str) -> Optional[Dict[str, Any]]:
        """
        Get map data from the Bubblemaps API with proper authentication and rate limiting
        """
        # Respect rate limits
        self._wait_for_rate_limit()
        
        # Build request
        map_data_url = f"{BUBBLEMAPS_API_BASE}/map-data"
        params = {
            "token": address,
            "chain": chain.lower(),
        }
        
        # Add API key if available
        headers = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        
        for attempt in range(self.max_retries):
            try:
                response = requests.get(
                    map_data_url, 
                    params=params, 
                    headers=headers,
                    timeout=15
                )
                
                # Handle different status codes
                if response.status_code == 200:
                    print("Successfully fetched map data")
                    return response.json()
                elif response.status_code == 401:
                    # Unauthorized - map not computed yet and no API key or invalid API key
                    print(f"Map data not available (401): Map not computed or API key required")
                    return None
                elif response.status_code == 429:
                    # Rate limited - wait and retry
                    retry_after = int(response.headers.get("Retry-After", "5"))
                    print(f"Rate limited, waiting {retry_after} seconds")
                    await asyncio.sleep(retry_after)
                    continue
                else:
                    print(f"Failed to fetch map data: Status {response.status_code}")
                    return None
                    
            except Exception as e:
                print(f"Error fetching map data (attempt {attempt+1}): {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2)
                    
        return None
        
    def _wait_for_rate_limit(self):
        """Handle rate limiting between API requests"""
        global LAST_API_REQUEST_TIME
        current_time = time.time()
        time_since_last_request = current_time - LAST_API_REQUEST_TIME
        
        if time_since_last_request < API_REQUEST_INTERVAL:
            sleep_time = API_REQUEST_INTERVAL - time_since_last_request
            print(f"Rate limiting: Waiting {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
            
        LAST_API_REQUEST_TIME = time.time()

    async def _generate_visualization_from_map_data(self, map_data: Dict[str, Any]) -> Optional[bytes]:
        """Generate a visualization from map data"""
        try:
            from utils.visualization import generate_bubble_visualization
            # This would be your custom visualization generator
            return generate_bubble_visualization(map_data, width=self.width, height=self.height)
        except ImportError:
            # If visualization module not available, create a basic visualization
            try:
                # Extract key information
                token_name = map_data.get("full_name", "Unknown Token")
                token_symbol = map_data.get("symbol", "")
                token_address = map_data.get("token_address", "")
                nodes = map_data.get("nodes", [])
                
                # Create a simple visualization with top holders
                from PIL import Image, ImageDraw, ImageFont
                
                # Create a base image
                img = Image.new('RGB', (self.width, self.height), color=(240, 240, 250))
                draw = ImageDraw.Draw(img)
                
                # Add title
                try:
                    font_title = ImageFont.truetype("arial.ttf", 24)
                    font_normal = ImageFont.truetype("arial.ttf", 16)
                except:
                    # Fallback if font not available
                    font_title = ImageFont.load_default()
                    font_normal = ImageFont.load_default()
                
                title = f"{token_name} ({token_symbol})"
                draw.text((20, 20), title, fill=(50, 50, 150), font=font_title)
                draw.text((20, 60), f"Address: {token_address}", fill=(80, 80, 80), font=font_normal)
                
                # Display top holders
                y_pos = 100
                draw.text((20, y_pos), "Top Holders:", fill=(50, 50, 150), font=font_normal)
                y_pos += 30
                
                # Show up to 10 top holders
                for i, node in enumerate(nodes[:10]):
                    if i >= 10:
                        break
                    
                    address = node.get("address", "")
                    name = node.get("name", address)
                    percentage = node.get("percentage", 0)
                    
                    holder_text = f"{i+1}. {name[:30]}... ({percentage:.2f}%)"
                    draw.text((30, y_pos), holder_text, fill=(60, 60, 60), font=font_normal)
                    y_pos += 25
                
                # Add update time
                update_time = map_data.get("dt_update", "")
                if update_time:
                    draw.text((20, self.height - 40), f"Last Updated: {update_time}", 
                              fill=(120, 120, 120), font=font_normal)
                
                # Convert to bytes
                output = BytesIO()
                img.save(output, format='PNG')
                output.seek(0)
                return output.getvalue()
                
            except Exception as e:
                print(f"Error creating basic visualization: {e}")
                return None

    async def _capture_with_playwright(self, url: str) -> Optional[bytes]:
        """Use Playwright to capture a screenshot"""
        for attempt in range(self.max_retries):
            try:
                async with async_playwright() as p:
                    # Use headless Chrome with default settings
                    browser = await p.chromium.launch(headless=True)
                    context = await browser.new_context(
                        viewport={"width": self.width, "height": self.height},
                        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
                    )
                    
                    page = await context.new_page()
                    
                    # Set a shorter timeout for initial navigation
                    page_timeout = 30000  # 30 seconds
                    
                    try:
                        # Navigate to the URL and wait for the page to be ready
                        print(f"Navigating to {url}")
                        await page.goto(url, wait_until="domcontentloaded", timeout=page_timeout)
                        
                        # Wait for network to be idle (no requests for 500ms)
                        print("Waiting for network idle")
                        await page.wait_for_load_state("networkidle", timeout=page_timeout)
                        
                        # Wait for any canvas/svg elements that might contain the visualization
                        print("Waiting for visualization elements")
                        selectors = [
                            "canvas",
                            "svg",
                            ".visualization-container",  # Common class for viz containers
                            "#bubble-map",  # Possible ID for the map
                            "[data-testid='bubble-map']"  # Data attribute for testing
                        ]
                        
                        for selector in selectors:
                            try:
                                await page.wait_for_selector(selector, timeout=5000)
                                print(f"Found element: {selector}")
                                break
                            except:
                                continue
                        
                        # Give the visualization a moment to render
                        print("Waiting for final render")
                        await asyncio.sleep(2)
                        
                        # Check if we got a 404 page
                        if await self._is_error_page(page):
                            print(f"Error page detected at URL: {url}")
                            await browser.close()
                            return None
                        
                        # Take screenshot with clip to ensure exact dimensions
                        print("Taking screenshot")
                        screenshot = await page.screenshot(
                            timeout=10000,  # 10 second timeout for screenshot
                            clip={
                                "x": 0,
                                "y": 0,
                                "width": self.width,
                                "height": self.height
                            }
                        )
                        
                        await browser.close()
                        
                        # Validate screenshot data
                        try:
                            with Image.open(io.BytesIO(screenshot)) as img:
                                if img.format in ['PNG', 'JPEG']:
                                    print("Successfully captured and validated screenshot")
                                    return screenshot
                        except Exception as e:
                            print(f"Invalid screenshot data: {e}")
                            
                    except Exception as e:
                        print(f"Error during page navigation/screenshot: {e}")
                        # Continue to retry
                        
            except Exception as e:
                print(f"Playwright screenshot attempt {attempt+1} failed: {e}")
                if attempt < self.max_retries - 1:
                    print(f"Retrying screenshot capture...")
                    await asyncio.sleep(2)  # Wait before retry
        
        print("All Playwright attempts failed")
        return None
    
    def _svg_to_png(self, svg_data: bytes) -> Optional[bytes]:
        """Convert SVG data to PNG"""
        try:
            print(f"Converting SVG of size {len(svg_data)} bytes to PNG")
            
            # Try to clean/validate SVG data
            try:
                from defusedxml import ElementTree
                # Parse and re-serialize to clean the XML
                tree = ElementTree.fromstring(svg_data)
                from io import StringIO
                cleaned_svg = StringIO()
                ElementTree.ElementTree(tree).write(cleaned_svg, encoding='unicode', xml_declaration=True)
                svg_data = cleaned_svg.getvalue().encode('utf-8')
                print("Successfully cleaned SVG data")
            except Exception as e:
                print(f"Failed to clean SVG data: {e}")
            
            # First try CairoSVG
            try:
                from cairosvg import svg2png
                print("Using CairoSVG for conversion")
                png_data = svg2png(bytestring=svg_data, 
                                 output_width=self.width, 
                                 output_height=self.height,
                                 background_color='white',  # Add white background
                                 unsafe=False)  # Ensure safe processing
                if png_data:
                    # Validate PNG data
                    try:
                        with Image.open(io.BytesIO(png_data)) as img:
                            if img.format == 'PNG':
                                print(f"Successfully converted SVG to PNG (size: {len(png_data)} bytes)")
                                return png_data
                    except Exception as e:
                        print(f"Invalid PNG data from CairoSVG: {e}")
            except ImportError:
                print("CairoSVG not installed, trying alternative method")
            except Exception as e:
                print(f"CairoSVG conversion failed: {e}")
            
            # Try alternative method using Pillow and rsvg
            try:
                import rsvg
                print("Using rsvg for conversion")
                svg = rsvg.Handle(data=svg_data)
                img = Image.new('RGBA', (self.width, self.height), (255, 255, 255, 255))
                svg.render_cairo(img)
                
                # Convert to bytes
                output = io.BytesIO()
                img.save(output, format='PNG')
                output.seek(0)
                png_data = output.getvalue()
                
                # Validate PNG data
                try:
                    with Image.open(io.BytesIO(png_data)) as img:
                        if img.format == 'PNG':
                            print(f"Successfully converted SVG to PNG using rsvg (size: {len(png_data)} bytes)")
                            return png_data
                except Exception as e:
                    print(f"Invalid PNG data from rsvg: {e}")
            except ImportError:
                print("rsvg not available")
            except Exception as e:
                print(f"rsvg conversion failed: {e}")
            
            print("No SVG conversion methods available or all methods failed")
            return None
            
        except Exception as e:
            print(f"Error converting SVG to PNG: {e}")
            return None
    
    async def _get_token_metadata(self, address: str, chain: str) -> Tuple[str, str]:
        """Get token name and symbol for better fallback images"""
        token_name = ""
        token_symbol = ""
        
        try:
            # Try to get metadata from Bubblemaps API using requests (which works)
            metadata_url = f"{BUBBLEMAPS_API_BASE}/map-metadata"
            params = {"token": address, "chain": chain.lower()}
            
            response = requests.get(metadata_url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if "full_name" in data:
                    token_name = data["full_name"]
                if "symbol" in data:
                    token_symbol = data["symbol"]
        except Exception as e:
            print(f"Error getting token metadata: {e}")
        
        return token_name, token_symbol

    async def _is_error_page(self, page):
        """Check if the current page is an error page"""
        try:
            # Check for common 404 indicators
            title = await page.title()
            if "404" in title or "Error" in title or "Not Found" in title:
                return True
                
            # Check for specific text on the page
            content = await page.content()
            if "404" in content and ("not found" in content.lower() or "doesn't exist" in content.lower()):
                return True
                
            return False
        except:
            return False

    def _get_mock_screenshot(self) -> bytes:
        """Return a mock/placeholder screenshot"""
        try:
            # Use dummyimage.com which generates valid images
            placeholder_url = "https://dummyimage.com/600x400/4287f5/ffffff.png&text=Bubblemaps+Visualization"
            response = requests.get(placeholder_url, timeout=10)
            if response.status_code == 200:
                print("Downloaded placeholder image from dummyimage.com")
                return response.content
        except Exception as e:
            print(f"Failed to download placeholder: {e}")
            
        # Hard-coded fallback - create a simple colored image
        try:
            from PIL import Image, ImageDraw
            
            # Create a simple colored image
            img = Image.new('RGB', (600, 400), color=(66, 135, 245))
            draw = ImageDraw.Draw(img)
            
            # Add text
            draw.text((300, 200), "Bubblemaps Visualization", fill=(255, 255, 255))
            
            # Convert to bytes
            output = BytesIO()
            img.save(output, format='JPEG', quality=85)
            output.seek(0)
            return output.getvalue()
        except Exception as e:
            print(f"Error creating image: {e}")
            
        # Last resort, return a minimal valid image
        return base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAlgAAAJYCAIAAAAxBA+LAAAACXBIWXMAAAsTAAALEwEA"
            "mpwYAAAGdElEQVR4nO3XMQEAIAzAMMC/5+GiHDQKenXPzAKAJN8OAIArQwgQZggBwgwhQ"
            "JghBAgzhABhhhAgzBAChBlCgDBDCBBmCAHCDCFAmCEECDOEAGGGECDMEAKEGUKAMEMIEG"
            "YIAcIMIUCYIQQIM4QAYYYQIMwQAoQZQoAwQwgQZggBwgwhQJghBAgzhABhhhAgzBACh"
            "BlCgDBDCBBmCAHCDCFAmCEECDOEAGGGECDMEAKEGUKAMEMIEGYIAcIMIUCYIQQIM4QAY"
            "YYQIMwQAoQZQoAwQwgQZggBwgwhQJghBAgzhABhhhAgzBAChBlCgDBDCBBmCAHCDCFAm"
            "CEECDOEAGGGECDMEAKEGUKAMEMIEGYIAcIMIUCYIQQIM4QAYYYQIMwQAoQZQoAwQwgQZg"
            "gBwgwhQJghBAgzhABhhhAgzBACh"
        )

    async def capture_token_page(self, url: str, iframe_url: Optional[str] = None) -> Optional[bytes]:
        """
        Capture a screenshot of the full token page
        
        Args:
            url: The regular Bubblemaps URL
            iframe_url: The iframe URL (if available)
        """
        # This is essentially the same as capture_bubble_map, so we'll reuse it
        return await self.capture_bubble_map(url, iframe_url) 