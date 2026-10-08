"""Rebuild state/products.json: every storefront product that passes state/rules.json and isn't in Bazar.

Rules (any one excludes the product): listed in exclude_ids, in the Bazar collection (state/bazar.json),
cheapest variant below min_price (catches R$0 / R$1 test items), a test-like word in the title, or a
blocked tag. Variants priced below min_price are also dropped by build_feed.py. Writes state/excluded.json."""
import json
from fetch import get_json

STORE = "https://www.vimmactivewear.com"
R = json.load(open("state/rules.json"))
bazar = set(json.load(open("state/bazar.json"))["ids"])

def storefront():
    out, page = [], 1
    while True:
        ps = get_json(f"{STORE}/products.json?limit=250&page={page}")["products"]
        if not ps: return out
        out += ps; page += 1

def why_excluded(p):
    pid, title = str(p["id"]), p["title"].lower()
    tags = {t.strip().lower() for t in (p["tags"] if isinstance(p["tags"], list) else p["tags"].split(","))}
    if pid in R["exclude_ids"]: return "lista de exclusão"
    if pid in bazar: return "Bazar"
    if min(float(v["price"]) for v in p["variants"]) < R["min_price"]: return f"preço abaixo de R$ {R['min_price']}"
    if any(k in title for k in R["title_keywords"]): return "título de teste"
    if tags & set(R["exclude_tags"]): return "tag de exclusão"
    return None

keep, excluded = [], {}
for p in storefront():
    reason = why_excluded(p)
    if reason: excluded[str(p["id"])] = {"title": p["title"], "reason": reason}; continue
    keep.append({"id": str(p["id"]), "title": p["title"],
                 "media": [{"mid": str(i["id"]), "url": i["src"], "w": i["width"], "h": i["height"]} for i in p["images"]]})
json.dump(keep, open("state/products.json", "w"), ensure_ascii=False)
json.dump(excluded, open("state/excluded.json", "w"), ensure_ascii=False, indent=1)
print(len(keep), "products in feed scope;", len(excluded), "excluded:")
for e in excluded.values(): print("  -", e["title"], "→", e["reason"])
