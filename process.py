"""Main image = ALWAYS photo 1 on Shopify (first non-GIF image), squared by square.py.

Rule from Mariana (2026-10-13): the feed's main image is the product's photo 1, no automatic choice.
For each product in state/products.json whose photo 1 differs from what uploaded.json records
(`source_file`), it squares photo 1 into out/<productId>.jpg and lists it in state/main_todo.json
(upload as meta-sq-<productId>-<imageId>.jpg). Writes state/review.jpg for a visual check."""
import json, os, subprocess, hashlib
import numpy as np
from PIL import Image, ImageDraw
from square import squarify

P = json.load(open("state/products.json"))
up = json.load(open("state/uploaded.json")) if os.path.exists("state/uploaded.json") else {}
os.makedirs("src2", exist_ok=True); os.makedirs("out", exist_ok=True)

def thumb(path):
    return np.asarray(Image.open(path).convert("L").resize((64, 64)), dtype=np.float32)

todo, tiles = {}, []
for p in P:
    photos = [m for m in p["media"] if ".gif" not in m["url"].lower()]
    if not photos: continue
    m = photos[0]; name = m["url"].split("?")[0].rsplit("/", 1)[-1]
    rec = up.get(p["id"], {})
    if rec.get("source_file") == name: continue
    src = f"src2/{hashlib.md5(name.encode()).hexdigest()[:12]}.jpg"
    if not os.path.exists(src):
        subprocess.run(["curl", "-s", "-o", src, m["url"].split("?")[0] + "?width=1440"], check=True)
    new = f"out/{p['id']}.new.jpg"
    if m["w"] == m["h"]:
        Image.open(src).convert("RGB").resize((1080, 1080), Image.LANCZOS).save(new, quality=92)
    else:
        squarify(src, new, anchor="pad" if p["title"].lower().startswith("top") else None)
    old = f"out/{p['id']}.jpg"
    if rec and os.path.exists(old) and np.abs(thumb(old) - thumb(new)).mean() < 4:
        rec["source_file"] = name; os.remove(new)           # already photo 1, just record it
        continue
    os.replace(new, old)
    todo[p["id"]] = {"mid": m["mid"], "source_file": name, "title": p["title"]}
    t = Image.open(old).resize((240, 240)); ImageDraw.Draw(t).text((4, 4), p["title"][:38], fill=(0, 0, 0)); tiles.append(t)

json.dump(up, open("state/uploaded.json", "w"), indent=1, ensure_ascii=False)
json.dump(todo, open("state/main_todo.json", "w"), indent=1, ensure_ascii=False)
if tiles:
    cols = 8; S = Image.new("RGB", (cols * 240, ((len(tiles) + cols - 1) // cols) * 240), "white")
    for i, t in enumerate(tiles): S.paste(t, ((i % cols) * 240, (i // cols) * 240))
    S.save("state/review.jpg", quality=88)
print(f"{len(todo)} main images to upload (photo 1); review state/review.jpg")
