"""Square the clean extra photos of each in-scope product for additional_image_link.

For every product in state/products.json (minus not_on_fb), every photo except the one used as the
main image: skip GIFs, keep it only if both side margins are plain backdrop (same test as the main
image), then extend the backdrop to 1080x1080. Photos with text overlays are fine if the margins are
clean. Identical source photos shared between products are squared and uploaded once.
Writes out_add/<key>.jpg, state/additional_todo.json (keys not uploaded yet) and state/review_add.jpg."""
import json, os, subprocess, hashlib
import numpy as np
from PIL import Image, ImageDraw
from edges import score
from square import squarify

THRESHOLD, MAX_EXTRA = 0.002, 20
P = json.load(open("state/products.json"))
up = json.load(open("state/uploaded.json"))
not_on_fb = set(json.load(open("state/not_on_fb.json"))["ids"])
done = json.load(open("state/additional_uploaded.json")) if os.path.exists("state/additional_uploaded.json") else {}

def thumb(path):
    return np.asarray(Image.open(path).convert("L").resize((64, 64)), dtype=np.float32)

def is_main(k, pid):  # the photo already used as the main square image
    return np.abs(thumb(f"out_add/{k}.jpg") - thumb(f"out/{pid}.jpg")).mean() < 4

def key(url):  # same photo reused across products → same key
    return hashlib.md5(url.split("?")[0].split("/")[-1].encode()).hexdigest()[:12]

plan, todo, tiles = {}, set(), []
for p in P:
    if p["id"] in not_on_fb or p["id"] not in up: continue
    main_src = up[p["id"]].get("source_media_id")
    keys = []
    for m in p["media"]:
        if ".gif" in m["url"].lower() or m["mid"] == main_src: continue
        k = key(m["url"]); f = f"src2/{k}.jpg"
        if not os.path.exists(f):
            subprocess.run(["curl", "-s", "-o", f, m["url"].split("?")[0] + "?width=1440"], check=True)
        if m["w"] != m["h"] and max(score(f)) > THRESHOLD: continue
        if not os.path.exists(f"out_add/{k}.jpg"):
            squarify(f, f"out_add/{k}.jpg")
        if is_main(k, p["id"]): continue
        if k not in done and k not in todo:
            todo.add(k)
            t = Image.open(f"out_add/{k}.jpg").resize((200, 200)); ImageDraw.Draw(t).text((3, 3), k[:6], fill=(0, 0, 0))
            tiles.append(t)
        keys.append(k)
    plan[p["id"]] = keys[:MAX_EXTRA]
json.dump(plan, open("state/additional_plan.json", "w"), indent=1)
json.dump(sorted(todo), open("state/additional_todo.json", "w"))
if tiles:
    cols = 15; S = Image.new("RGB", (cols * 200, ((len(tiles) + cols - 1) // cols) * 200), "white")
    for i, t in enumerate(tiles): S.paste(t, ((i % cols) * 200, (i // cols) * 200))
    S.save("state/review_add.jpg", quality=85)
n = [len(v) for v in plan.values()]
print(f"{len(plan)} products, {sum(n)} extra images ({len(todo)} new files to upload); per product min {min(n)} / max {max(n)}")
for pid, v in plan.items():
    if len(v) == 0: print("  no clean extra photo:", next(p["title"] for p in P if p["id"] == pid))
