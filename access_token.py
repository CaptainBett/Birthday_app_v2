import requests
from requests.auth import HTTPBasicAuth
import time

# Safaricom sandbox endpoints
OAUTH_URL = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
CONSUMER_KEY = "ppXNpH38Cx0aibOUGqeLVZRo3ApKu9DipJHO9Cn9TeOirAgR"
CONSUMER_SECRET = "AN1PkOA5v57yoiBbcqmNtreS7EmmqDReelAnyZvM4qmcGGJRM2UMRX0dfBYybYUt"

_token_cache = {}
CACHE_TTL = 3600  # seconds

def get_mpesa_token():
    now = time.time()
    if _token_cache and now < _token_cache.get("expires_at", 0):
        return _token_cache["token"]

    resp = requests.get(
        OAUTH_URL,
        auth=HTTPBasicAuth(CONSUMER_KEY, CONSUMER_SECRET)
    )
    resp.raise_for_status()
    data = resp.json()
    token = data["access_token"]

    _token_cache["token"] = token
    _token_cache["expires_at"] = now + CACHE_TTL
    return token
