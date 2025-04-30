import aiohttp
import asyncio
import requests
from typing import Dict, Optional
from config import (
    COINGECKO_API_BASE, DEXSCREENER_API_BASE, 
    MOCK_COINGECKO_API_BASE, MOCK_DEXSCREENER_API_BASE,
    DEV_MODE
)

class TokenMetrics:
    def __init__(self):
        # Use mock APIs in development mode
        self.coingecko_base = MOCK_COINGECKO_API_BASE if DEV_MODE else COINGECKO_API_BASE
        self.dexscreener_base = MOCK_DEXSCREENER_API_BASE if DEV_MODE else DEXSCREENER_API_BASE
        self.timeout = aiohttp.ClientTimeout(total=30)  # Increased to 30 seconds
        self.max_retries = 3  # Add retry count
        print(f"CoinGecko API base URL: {self.coingecko_base} (DEV_MODE: {DEV_MODE})")
        print(f"DexScreener API base URL: {self.dexscreener_base} (DEV_MODE: {DEV_MODE})")

    async def _make_request(self, url: str, params: Dict = None, method: str = "GET") -> Dict:
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

    async def get_coingecko_metrics(self, address: str, chain: str) -> Optional[Dict]:
        """
        Get token metrics from CoinGecko
        """
        try:
            # Map chain names to CoinGecko IDs
            chain_map = {
                "ETH": "ethereum",
                "BSC": "binance-smart-chain",
                "FTM": "fantom",
                "AVAX": "avalanche",
                "CRO": "cronos",
                "ARBI": "arbitrum-one",
                "POLY": "polygon-pos",
                "BASE": "base",
                "SOL": "solana",
                "SONIC": "sonic"
            }
            
            chain_id = chain_map.get(chain.upper())
            if not chain_id:
                print(f"Unsupported chain for CoinGecko: {chain}")
                return None

            url = f"{self.coingecko_base}/simple/token_price/{chain_id}"
            params = {
                "contract_addresses": address,
                "vs_currencies": "usd",
                "include_market_cap": "true",
                "include_24hr_vol": "true",
                "include_24hr_change": "true"
            }
            
            print(f"Requesting CoinGecko metrics for {address} on {chain}")
            
            try:
                data = await self._make_request(url, params)
                
                if address.lower() in data:
                    return data[address.lower()]
                print(f"Address not found in CoinGecko response, got: {data}")
                return None
            except Exception as e:
                print(f"CoinGecko request failed: {e}")
                return None
        except Exception as e:
            print(f"Error getting CoinGecko metrics: {e}")
            return None

    async def get_dexscreener_metrics(self, address: str, chain: str) -> Optional[Dict]:
        """
        Get token metrics from DexScreener
        """
        try:
            # Map chain names to DexScreener format if needed
            chain_map = {
                "ETH": "ethereum",
                "BSC": "bsc",
                "FTM": "fantom",
                "AVAX": "avalanche",
                "CRO": "cronos",
                "ARBI": "arbitrum",
                "POLY": "polygon",
                "BASE": "base",
                "SOL": "solana",
                "SONIC": "sonic"
            }
            
            chain_id = chain_map.get(chain.upper(), chain.lower())
            
            url = f"{self.dexscreener_base}/dex/tokens/{chain_id}/{address}"
            print(f"Requesting DexScreener metrics for {address} on {chain}")
            
            try:
                data = await self._make_request(url)
                
                if "pairs" in data and len(data["pairs"]) > 0:
                    pair = data["pairs"][0]
                    return {
                        "price": pair.get("priceUsd"),
                        "market_cap": pair.get("marketCap"),
                        "volume_24h": pair.get("volume24h"),
                        "price_change_24h": pair.get("priceChange24h")
                    }
                print(f"No pairs found in DexScreener response: {data}")
                return None
            except Exception as e:
                print(f"DexScreener request failed: {e}")
                return None
        except Exception as e:
            print(f"Error getting DexScreener metrics: {e}")
            return None

    async def get_combined_metrics(self, address: str, chain: str) -> Dict:
        """
        Get combined metrics from both sources
        """
        try:
            # Try DexScreener first, then fall back to CoinGecko
            dexscreener_data = await self.get_dexscreener_metrics(address, chain)
            
            if dexscreener_data and dexscreener_data.get("price"):
                print(f"Using DexScreener data for {address} on {chain}")
                return dexscreener_data
            
            coingecko_data = await self.get_coingecko_metrics(address, chain)
            
            if coingecko_data and coingecko_data.get("usd"):
                print(f"Using CoinGecko data for {address} on {chain}")
                return {
                    "price": coingecko_data.get("usd"),
                    "market_cap": coingecko_data.get("usd_market_cap"),
                    "volume_24h": coingecko_data.get("usd_24h_vol"),
                    "price_change_24h": coingecko_data.get("usd_24h_change")
                }
                
            print(f"No metrics found for {address} on {chain}")
            return {
                "price": None,
                "market_cap": None,
                "volume_24h": None,
                "price_change_24h": None
            }
        except Exception as e:
            print(f"Error in get_combined_metrics: {e}")
            return {
                "price": None,
                "market_cap": None,
                "volume_24h": None,
                "price_change_24h": None
            } 