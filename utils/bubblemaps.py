import aiohttp
import asyncio
import requests
from typing import Dict, Optional, List
from config import BUBBLEMAPS_API_BASE, MOCK_BUBBLEMAPS_API_BASE, DEV_MODE

class BubblemapsAPI:
    def __init__(self):
        # Use mock API in development mode
        self.base_url = MOCK_BUBBLEMAPS_API_BASE if DEV_MODE else BUBBLEMAPS_API_BASE
        self.timeout = aiohttp.ClientTimeout(total=30)  # Increased timeout to 30 seconds
        self.max_retries = 3  # Add retry count
        print(f"Bubblemaps API base URL: {self.base_url} (DEV_MODE: {DEV_MODE})")

    async def _make_request(self, url: str, params: Dict, method: str = "GET") -> Dict:
        """
        Make an HTTP request with retry logic and fallback to requests library
        """
        retries = 0
        last_exception = None
        
        while retries < self.max_retries:
            try:
                async with aiohttp.ClientSession(timeout=self.timeout) as session:
                    print(f"Calling {url} with params: {params} (attempt {retries+1}/{self.max_retries})")
                    
                    if method.upper() == "GET":
                        async with session.get(url, params=params) as response:
                            if response.status == 200:
                                return await response.json()
                            else:
                                print(f"Request failed with status: {response.status}")
                                response_text = await response.text()
                                print(f"Response: {response_text[:200]}")  # Log first 200 chars
                                raise Exception(f"HTTP Error: {response.status}")
                    else:
                        # Add support for other methods if needed
                        raise NotImplementedError(f"Method {method} not implemented")
            
            except asyncio.TimeoutError:
                print(f"Request timed out (attempt {retries+1}/{self.max_retries})")
                last_exception = Exception("Request timed out")
            except aiohttp.ClientConnectorError as e:
                print(f"Connection error: {e} (attempt {retries+1}/{self.max_retries})")
                last_exception = e
                
                # If we get connection error related to "No route to host", try requests library
                if "No route to host" in str(e) and retries == self.max_retries - 1:
                    print(f"Trying fallback with requests library...")
                    try:
                        # Use requests library as fallback
                        response = requests.get(url, params=params, timeout=30)
                        if response.status_code == 200:
                            print(f"Fallback successful with requests library")
                            return response.json()
                        else:
                            print(f"Fallback request failed with status: {response.status_code}")
                    except Exception as req_err:
                        print(f"Fallback request also failed: {req_err}")
                
            except Exception as e:
                print(f"Request error: {e} (attempt {retries+1}/{self.max_retries})")
                last_exception = e
            
            retries += 1
            if retries < self.max_retries:
                # Exponential backoff: 1s, 2s, 4s, etc.
                wait_time = 2 ** (retries - 1)
                print(f"Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
        
        # All retries failed, try one last attempt with requests
        print("All aiohttp attempts failed, trying requests as last resort...")
        try:
            response = requests.get(url, params=params, timeout=30)
            if response.status_code == 200:
                print("Requests fallback succeeded!")
                return response.json()
            else:
                print(f"Requests fallback failed with status code: {response.status_code}")
        except Exception as e:
            print(f"Requests fallback error: {e}")
        
        # If we get here, both approaches failed
        raise last_exception or Exception("Request failed after multiple attempts")

    async def get_map_data(self, address: str, chain: str) -> Dict:
        """
        Get token map data from Bubblemaps API
        """
        try:
            # Query parameters as shown in the documentation
            params = {
                "token": address,
                "chain": chain.lower()
            }
            
            url = f"{self.base_url}/map-data"
            print(f"Requesting map data for {address} on {chain}")
            
            data = await self._make_request(url, params)
            
            if "nodes" in data:
                return data
            elif "status" in data and data["status"] == "KO":
                print(f"Bubblemaps API error: {data.get('message', 'Unknown error')}")
                raise Exception(f"API Error: {data.get('message', 'Unknown error')}")
            else:
                print(f"Unexpected response format: {data}")
                raise Exception("Unexpected response format")
        except Exception as e:
            print(f"Error getting map data: {e}")
            # Return minimal structure to prevent downstream errors
            return {
                "nodes": [],
                "links": [],
                "token_links": []
            }

    async def get_map_metadata(self, address: str, chain: str) -> Dict:
        """
        Get token map metadata from Bubblemaps API
        """
        try:
            # Query parameters as shown in the documentation
            params = {
                "token": address,
                "chain": chain.lower()
            }
            
            url = f"{self.base_url}/map-metadata"
            print(f"Requesting map metadata for {address} on {chain}")
            
            data = await self._make_request(url, params)
            
            if "status" in data and data["status"] == "OK":
                return data
            else:
                error_msg = data.get("message", "Unknown error")
                print(f"Map metadata API error: {error_msg}")
                raise Exception(f"API Error: {error_msg}")
            
        except Exception as e:
            print(f"Error getting map metadata: {e}")
            # Return minimal structure to prevent downstream errors
            return {
                "status": "KO",
                "decentralisation_score": None,
                "identified_supply": {
                    "percent_in_cexs": 0,
                    "percent_in_contracts": 0
                }
            }
            
    async def check_map_availability(self, address: str, chain: str) -> bool:
        """
        Check if a bubble map is available and ready to display
        """
        try:
            # Use the map-availability endpoint
            params = {
                "token": address,
                "chain": chain.lower()
            }
            
            # If in development mode, assume it's available
            if DEV_MODE:
                return True
            
            url = f"{self.base_url}/map-availability"
            print(f"Checking map availability for {address} on {chain}")
            
            try:
                data = await self._make_request(url, params)
                
                if "status" in data and data["status"] == "OK":
                    return data.get("availability", False)
                else:
                    print(f"Map availability check failed: {data.get('message', 'Unknown error')}")
                    return False
            except Exception as e:
                print(f"Map availability check exception: {e}")
                # Important: For availability check only, we can safely return False on error
                return False
                
        except Exception as e:
            print(f"Error checking map availability: {e}")
            return False

    async def get_decentralization_score(self, address: str, chain: str) -> Optional[float]:
        """
        Get token decentralization score
        """
        try:
            data = await self.get_map_metadata(address, chain)
            return data.get("decentralisation_score")
        except Exception as e:
            print(f"Error getting decentralization score: {e}")
            return None

    async def get_holder_data(self, address: str, chain: str) -> Dict:
        """
        Get token holder data
        """
        try:
            map_data = await self.get_map_data(address, chain)
            nodes = map_data.get("nodes", [])
            
            # Process top holders
            top_holders = []
            for node in nodes:
                if "address" in node and "percentage" in node:
                    holder = {
                        "address": node["address"],
                        "amount": node.get("amount", 0),
                        "percentage": node.get("percentage", 0),
                        "is_contract": node.get("is_contract", False),
                        "name": node.get("name", "Unknown")
                    }
                    top_holders.append(holder)

            # Get supply distribution from metadata
            try:
                metadata = await self.get_map_metadata(address, chain)
                supply_info = metadata.get("identified_supply", {})
            except Exception:
                supply_info = {}

            return {
                "top_holders": top_holders,
                "total_holders": len(nodes),
                "supply_distribution": {
                    "in_cexs": supply_info.get("percent_in_cexs", 0),
                    "in_contracts": supply_info.get("percent_in_contracts", 0)
                }
            }
        except Exception as e:
            print(f"Error getting holder data: {e}")
            return {
                "top_holders": [],
                "total_holders": 0,
                "supply_distribution": {
                    "in_cexs": 0,
                    "in_contracts": 0
                }
            }

    def get_bubble_map_url(self, address: str, chain: str) -> str:
        """
        Get the URL for the bubble map visualization
        """
        # Use the same format as the app URL for consistency
        return f"https://app.bubblemaps.io/{chain.lower()}/token/{address}"
        
    def get_iframe_url(self, address: str, chain: str) -> str:
        """
        Get the URL for the bubble map iframe
        Uses the iframe format from documentation
        """
        # Adding params to disable scroll zoom and use small text for better viewing in Telegram
        return f"https://app.bubblemaps.io/{chain.lower()}/token/{address}?prevent_scroll_zoom&small_text" 