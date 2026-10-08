"""Storefront JSON with retries: Shopify sometimes answers 429/503 to plain scripts."""
import json, time, urllib.request

def get_json(url, tries=5):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception:
            if i == tries - 1: raise
            time.sleep(10 * (i + 1))
