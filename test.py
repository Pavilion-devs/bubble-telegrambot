import requests

# Test if requests can connect
try:
    response = requests.get("https://api-legacy.bubblemaps.io/map-availability", 
                          params={"token": "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984", "chain": "eth"})
    print(f"Response status: {response.status_code}")
    print(f"Response text: {response.text}")
except Exception as e:
    print(f"Error: {e}")