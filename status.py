"""Write github-feed/status.json for the dashboard (github-feed/index.html).

checked_at only moves forward when something else changed or every 6 h, so the hourly job doesn't
create a commit every hour just for the timestamp."""
import csv, json, os
from datetime import datetime, timedelta
from fetch import get_json

STORE = "https://www.vimmactivewear.com"
FEED_URL = "https://raw.githubusercontent.com/Vimm-Activewear-Br/meta-feed/main/vimm-meta-supplementary-feed.csv"
OUT = "status.json"

def load(p, default):
    return json.load(open(p)) if os.path.exists(p) else default

def build(errors=None, photo_changes=None):
    up = load("state/uploaded.json", {}); attrs = load("state/attrs.json", {})
    plan = load("state/additional_plan.json", {}); extra_done = load("state/additional_uploaded.json", {})
    scope = load("state/products.json", []); excluded = load("state/excluded.json", {})
    not_on_fb = set(load("state/not_on_fb.json", {"ids": []})["ids"])
    rows = list(csv.reader(open("vimm-meta-supplementary-feed.csv")))[2:]
    in_feed = {r[0] for r in rows}
    sf = {str(p["id"]): p for p in get_json(f"{STORE}/products.json?limit=250")["products"]}
    from feed_attrs import kind, labels, color

    products = []
    for p in scope:
        pid = p["id"]; s = sf.get(pid); a = attrs.get(pid)
        if not s: continue
        variants = s["variants"]; avail = sum(v["available"] for v in variants)
        status = ("no_feed" if pid in up and pid not in not_on_fb else
                  "fora_canal" if pid in not_on_fb else "sem_foto")
        linha, momento = labels(a) if a else ("", "")
        products.append({
            "id": pid, "title": s["title"], "kind": kind(s["title"]), "color": color(a) if a else "",
            "linha": linha, "momento": momento, "status": status,
            "image": (up[pid]["url"].split("?")[0] + "?format=pjpg&width=300") if pid in up else
                     (s["images"][0]["src"].split("?")[0] + "?width=300" if s["images"] else ""),
            "extras": len([k for k in plan.get(pid, []) if k in extra_done]),
            "variants": len(variants), "in_stock": avail,
            "link": f"{STORE}/products/{s['handle']}",
        })
    products.sort(key=lambda x: (x["status"] != "sem_foto", x["status"] != "fora_canal", x["kind"], x["title"]))

    alerts = []
    for x in products:
        if x["status"] == "sem_foto": alerts.append({"level": "acao", "text": f"Produto novo sem foto quadrada: {x['title']}. Peça ao Claude: atualiza o feed do Meta."})
        if x["status"] == "fora_canal": alerts.append({"level": "info", "text": f"Fora do canal Facebook & Instagram (não entra no catálogo): {x['title']}"})
    for t in photo_changes or []:
        alerts.append({"level": "acao", "text": f"Fotos alteradas na Shopify: {t}. Peça ao Claude: refaz as fotos quadradas do feed."})
    for e in errors or []:
        alerts.append({"level": "erro", "text": e})

    status = {
        "feed_url": FEED_URL, "rows": len(rows), "products_in_feed": len({x["id"] for x in products if x["status"] == "no_feed"}),
        "variants_in_stock": sum(x["in_stock"] for x in products if x["status"] == "no_feed"),
        "alerts": alerts, "products": products,
        "excluded": [{"title": v["title"], "reason": v["reason"]} for v in excluded.values()],
        "log": [l.rstrip() for l in open("state/auto_refresh.log")][-12:] if os.path.exists("state/auto_refresh.log") else [],
    }
    old = load(OUT, {})
    old_core = {k: v for k, v in old.items() if k not in ("checked_at", "updated_at")}
    now = datetime.now()
    changed = old_core != status
    stale = not old.get("checked_at") or now - datetime.fromisoformat(old["checked_at"]) > timedelta(hours=6)
    status["updated_at"] = now.isoformat(timespec="minutes") if changed else old.get("updated_at", now.isoformat(timespec="minutes"))
    status["checked_at"] = now.isoformat(timespec="minutes") if (changed or stale) else old["checked_at"]
    if changed or stale:
        json.dump(status, open(OUT, "w"), ensure_ascii=False, indent=1)
    return changed

if __name__ == "__main__":
    print("changed" if build() else "same")
