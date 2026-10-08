"""Build the Meta supplementary feed CSV from state/uploaded.json + live storefront variants.

One row per variant (Meta content ID = Shopify variant ID). Bazar products are left out and every
row gets custom_label_0 = LABEL, so a Meta product set "custom_label_0 = vimm_feed AND in stock"
shows only in-stock, non-Bazar items (a supplementary feed can't remove items from the catalog).
Scope = state/products.json, written by refresh_products.py from state/rules.json."""
import json, csv
from fetch import get_json
from short_desc import short_description
from feed_attrs import FIELDS, row_extra

STORE = "https://www.vimmactivewear.com"
LABEL = "vimm_feed"

def storefront():
    out, page = {}, 1
    while True:
        ps = get_json(f"{STORE}/products.json?limit=250&page={page}")["products"]
        if not ps: return out
        out.update({str(p["id"]): p for p in ps}); page += 1

def image_link(url):
    # Shopify's CDN answers with WebP when the client accepts it, and Meta rejects non-JPEG/PNG images.
    # format=pjpg forces a (progressive) JPEG whatever the Accept header says.
    return url.split("?")[0] + "?format=pjpg"

up = json.load(open("state/uploaded.json")); S = storefront()
scope = {p["id"] for p in json.load(open("state/products.json"))}
min_price = json.load(open("state/rules.json"))["min_price"]
not_on_fb = set(json.load(open("state/not_on_fb.json"))["ids"])  # not in the Meta catalog → rows would only error
# Extra square photos per product (additional.py → state/additional_plan.json), only ones already in Shopify Files
plan = json.load(open("state/additional_plan.json"))
extra_done = json.load(open("state/additional_uploaded.json"))
def additional_links(pid):
    return ",".join(image_link(extra_done[k]) for k in plan.get(pid, []) if k in extra_done)

rows = []
for pid, u in up.items():
    s = S.get(pid)
    if not s: print("skip (not on storefront):", u["title"]); continue
    if pid not in scope: continue  # excluded by rules / Bazar (see state/excluded.json)
    if pid in not_on_fb: print("skip (not on Facebook & Instagram channel):", u["title"]); continue
    for v in s["variants"]:
        if float(v["price"]) < min_price: continue
        rows.append([str(v["id"]), image_link(u["url"]), additional_links(pid), short_description(s["title"]), LABEL]
                    + row_extra(pid, v))

# Same layout as Meta's catalog template: a "#" comment row, then field names, then data.
COMMENTS = ["# Obrigatório | A unique content ID for the item.",
            "# Opcional | The URL for the main image of your item.",
            "# Opcional | List of additional image urls for the item.",
            "# Opcional | Short description of the item.",
            "# Opcional | Label used to filter items into product sets."] + [f"# Opcional | {f}" for f in FIELDS]
with open("vimm-meta-supplementary-feed.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(COMMENTS)
    w.writerow(["id", "image_link", "additional_image_link", "short_description", "custom_label_0"] + FIELDS); w.writerows(rows)
print(len(rows), "variant rows")
