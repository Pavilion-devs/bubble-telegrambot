from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import uvicorn
from typing import Dict, List, Optional, Any
import random

app = FastAPI(title="Bubblemaps Mock API")

# Sample data for mock responses
MOCK_TOKENS = {
    # ETH tokens
    "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984": {  # UNI token
        "name": "Uniswap",
        "symbol": "UNI",
        "chain": "eth",
        "score": 71.83,
        "price": 7.25,
        "market_cap": 3640000000,
        "volume_24h": 98500000,
        "price_change_24h": 2.5,
        "in_cexs": 7.23,
        "in_contracts": 16.82
    },
    # BSC tokens
    "0x0e09fabb73bd3ade0a17ecc321fd13a19e81ce82": {  # CAKE token
        "name": "PancakeSwap",
        "symbol": "CAKE",
        "chain": "bsc",
        "score": 65.2,
        "price": 3.12,
        "market_cap": 1240000000,
        "volume_24h": 43200000,
        "price_change_24h": -1.2,
        "in_cexs": 12.4,
        "in_contracts": 28.9
    }
}

def generate_mock_holders(token_info: Dict) -> List[Dict]:
    """Generate mock holder data for a token"""
    num_holders = random.randint(10, 20)
    holders = []
    
    # Create some large holders
    total_percent = 0
    for i in range(5):
        percent = random.uniform(5, 15)
        total_percent += percent
        
        holders.append({
            "address": f"0x{''.join(random.choices('0123456789abcdef', k=40))}",
            "amount": random.uniform(1000000, 10000000),
            "percentage": percent,
            "is_contract": random.choice([True, False]),
            "name": f"{'Whale' if i < 2 else 'Contract' if i < 4 else 'Exchange'} #{i+1}"
        })
    
    # Create some smaller holders
    remaining_percent = 100 - total_percent
    for i in range(5, num_holders):
        percent = remaining_percent / (num_holders - 5) * (0.8 + random.random() * 0.4)
        
        holders.append({
            "address": f"0x{''.join(random.choices('0123456789abcdef', k=40))}",
            "amount": random.uniform(10000, 1000000),
            "percentage": percent,
            "is_contract": random.choice([True, False]),
            "name": f"Holder #{i+1}"
        })
    
    return holders

@app.get("/")
def read_root():
    return {"status": "OK", "message": "Bubblemaps Mock API is running"}

# Mock Bubblemaps Map Data API
@app.get("/map-data")
def get_map_data(token: str, chain: str):
    token_key = token.lower()
    
    if token_key not in MOCK_TOKENS or MOCK_TOKENS[token_key]["chain"] != chain.lower():
        return {"status": "KO", "message": "Data not available for this token"}
    
    token_info = MOCK_TOKENS[token_key]
    holders = generate_mock_holders(token_info)
    
    # Generate mock links between holders
    links = []
    for i in range(min(20, len(holders) * 2)):
        source = random.randint(0, len(holders) - 1)
        target = random.randint(0, len(holders) - 1)
        if source != target:
            links.append({
                "source": source,
                "target": target,
                "forward": random.uniform(100, 5000),
                "backward": random.uniform(0, 1000)
            })
    
    return {
        "version": 5,
        "chain": chain,
        "token_address": token,
        "dt_update": "2024-06-17 22:17:27.576443+00:00",
        "full_name": token_info["name"],
        "symbol": token_info["symbol"],
        "is_X721": False,
        "nodes": holders,
        "links": links,
        "token_links": []
    }

# Mock Bubblemaps Map Metadata API
@app.get("/map-metadata")
def get_map_metadata(token: str, chain: str):
    token_key = token.lower()
    
    if token_key not in MOCK_TOKENS or MOCK_TOKENS[token_key]["chain"] != chain.lower():
        return {"status": "KO", "message": "Data not available for this token"}
    
    token_info = MOCK_TOKENS[token_key]
    
    return {
        "decentralisation_score": token_info["score"],
        "identified_supply": {
            "percent_in_cexs": token_info["in_cexs"],
            "percent_in_contracts": token_info["in_contracts"]
        },
        "dt_update": "2024-06-17 22:17:27.576443+00:00",
        "ts_update": 1718662647,
        "status": "OK"
    }

# Mock CoinGecko API
@app.get("/coingecko/api/v3/simple/token_price/{chain_id}")
def get_coingecko_price(
    chain_id: str,
    contract_addresses: str = Query(...),
    vs_currencies: str = Query("usd"),
    include_market_cap: str = Query("false"),
    include_24hr_vol: str = Query("false"),
    include_24hr_change: str = Query("false")
):
    token_key = contract_addresses.lower()
    
    if token_key not in MOCK_TOKENS:
        return {}
    
    token_info = MOCK_TOKENS[token_key]
    
    # Check chain matches
    chain_map = {
        "ethereum": "eth",
        "binance-smart-chain": "bsc",
        "fantom": "ftm",
        "avalanche": "avax",
        "cronos": "cro",
        "arbitrum-one": "arbi",
        "polygon-pos": "poly",
        "base": "base",
        "solana": "sol",
        "sonic": "sonic"
    }
    
    if chain_map.get(chain_id) != token_info["chain"]:
        return {}
    
    response = {
        token_key: {
            "usd": token_info["price"]
        }
    }
    
    if include_market_cap == "true":
        response[token_key]["usd_market_cap"] = token_info["market_cap"]
    
    if include_24hr_vol == "true":
        response[token_key]["usd_24h_vol"] = token_info["volume_24h"]
    
    if include_24hr_change == "true":
        response[token_key]["usd_24h_change"] = token_info["price_change_24h"]
    
    return response

# Mock DexScreener API
@app.get("/dexscreener/latest/dex/tokens/{chain_id}/{address}")
def get_dexscreener_data(chain_id: str, address: str):
    token_key = address.lower()
    
    if token_key not in MOCK_TOKENS:
        return {"pairs": []}
    
    token_info = MOCK_TOKENS[token_key]
    
    # Check chain matches
    chain_map = {
        "ethereum": "eth",
        "bsc": "bsc",
        "fantom": "ftm",
        "avalanche": "avax",
        "cronos": "cro",
        "arbitrum": "arbi",
        "polygon": "poly",
        "base": "base",
        "solana": "sol",
        "sonic": "sonic"
    }
    
    if chain_map.get(chain_id) != token_info["chain"]:
        return {"pairs": []}
    
    return {
        "pairs": [
            {
                "chainId": chain_id,
                "dexId": "pancakeswap" if token_info["chain"] == "bsc" else "uniswap",
                "pairAddress": f"0x{''.join(random.choices('0123456789abcdef', k=40))}",
                "baseToken": {
                    "address": token_key,
                    "name": token_info["name"],
                    "symbol": token_info["symbol"]
                },
                "priceUsd": token_info["price"],
                "priceChange24h": token_info["price_change_24h"],
                "volume24h": token_info["volume_24h"],
                "marketCap": token_info["market_cap"]
            }
        ]
    }

# Run the mock server
if __name__ == "__main__":
    uvicorn.run("mock_api:app", host="127.0.0.1", port=8000, reload=True) 