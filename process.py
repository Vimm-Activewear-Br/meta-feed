"""Download, pick and square images for products in state/products.json that aren't in state/uploaded.json yet.

Pick rule: first image (in Shopify order) whose left/right margins are plain backdrop,
so extending the backdrop sideways looks natural. state/overrides.json forces an image
index for a product. Writes out/<product_id>.jpg, state/picks.json and state/review.jpg.
"""
import json, os, subprocess
from PIL import Image, ImageDraw
from edges import score
from square import squarify

THRESHOLD = 0.002
P = json.load(open("state/products.json"))
done = json.load(open("state/uploaded.json")) if os.path.exists("state/uploaded.json") else {}
over = json.load(open("state/overrides.json")) if os.path.exists("state/overrides.json") else {}
todo = [p for p in P if p["id"] not in done or p["id"] in over and over[p["id"]] != done[p["id"]]["source_index"]]
picks, tiles = {}, []
for p in todo:
    p["media"] = [m for m in p["media"] if ".gif" not in m["url"].lower()]  # GIF covers can't be squared
    for i, m in enumerate(p["media"]):
        f = f"src/{p['id']}_{i}.jpg"
        if not os.path.exists(f):
            subprocess.run(["curl", "-s", "-o", f, m["url"].split("?")[0] + "?width=1440"], check=True)
    if p["id"] in over:
        i = over[p["id"]]
    else:
        sq = [i for i, m in enumerate(p["media"]) if m["w"] == m["h"]]  # already square: use as is
        i = sq[0] if sq else next((i for i in range(len(p["media"])) if max(score(f"src/{p['id']}_{i}.jpg")) <= THRESHOLD), None)
    if i is None:
        print("NO CLEAN IMAGE, needs an override:", p["id"], p["title"]); continue
    picks[p["id"]] = {"index": i, "mid": p["media"][i]["mid"]}
    squarify(f"src/{p['id']}_{i}.jpg", f"out/{p['id']}.jpg")
    t = Image.open(f"out/{p['id']}.jpg").resize((300, 300))
    ImageDraw.Draw(t).text((4, 4), f"{p['id']} #{i}", fill=(0, 0, 0)); tiles.append(t)
json.dump(picks, open("state/picks.json", "w"))
if tiles:
    S = Image.new("RGB", (min(len(tiles), 9) * 300, ((len(tiles) + 8) // 9) * 300), "white")
    for k, t in enumerate(tiles): S.paste(t, ((k % 9) * 300, (k // 9) * 300))
    S.save("state/review.jpg", quality=88)
print(f"{len(picks)} new square images in out/ — check state/review.jpg")
