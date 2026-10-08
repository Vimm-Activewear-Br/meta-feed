"""Extra Meta fields per product, from state/attrs.json (Shopify: type, tags, theme.sibling_color,
custom.material_e_cuidados, custom.aviso_cor). Every field always gets a value: an empty cell in a
supplementary feed could clear what the Shopify channel sent."""
import json, re

A = json.load(open("state/attrs.json"))

CAT_ACTIVEWEAR = "Apparel & Accessories > Clothing > Activewear"   # Google 5322, same as the Shopify metafield
CAT_OUTFIT_SET = "Apparel & Accessories > Clothing > Outfit Sets"  # conjuntos: Shopify says only "Bundles"

def kind(title):
    t = title.lower()
    if t.startswith(("conjunto", "kit")): return "conjunto"
    if t.startswith("bermuda"): return "bermuda"
    if t.startswith(("top", "top-blusa")): return "top"
    if t.startswith("macaquinho"): return "macaquinho"
    return "acessorio"

PRODUCT_TYPE = {
    "conjunto": "Roupas esportivas > Conjuntos de compressão",
    "bermuda": "Roupas esportivas > Bermudas de compressão",
    "top": "Roupas esportivas > Tops de compressão",
    "macaquinho": "Roupas esportivas > Macaquinhos de triathlon",
    "acessorio": "Roupas esportivas > Acessórios",
}

def material(text):
    # first "NN% fibra" pairs of the body fabric, e.g. "70% poliamida, 30% elastano"
    body = (text or "").split("forro")[0]
    pairs = re.findall(r"(\d+)\s*%\s*([A-Za-zÀ-ú]+)", body)
    return ", ".join(f"{n}% {f.lower()}" for n, f in pairs[:3]) or "Poliamida e elastano"

def color(a):
    if a.get("color"): return a["color"]
    known = ["chocolate", "amora", "preto", "preta", "marinho", "branco", "bordô", "grafite", "oliva", "bege", "uva", "marrom"]
    found = [w for w in a["title"].lower().split() if w in known]
    return found[-1].capitalize() if found else "Multicolorido"

def labels(a):
    tags = {t.strip().upper() for t in a["tags"]}
    linha = "edicao_limitada" if "limitada" in (a.get("aviso") or "") else "perene"
    if "NOVIDADE" in tags: momento = "novidade"
    elif {"ÚLTIMAS PEÇAS", "BADGE: POUCAS UNIDADES"} & tags: momento = "ultimas_pecas"
    elif "PRÉ-LANÇAMENTO" in tags: momento = "pre_lancamento"
    else: momento = "regular"
    return linha, momento

FIELDS = ["color", "size", "gender", "age_group", "material", "google_product_category", "product_type",
          "is_outfit_set", "size_system", "custom_label_1", "custom_label_2", "custom_label_3", "custom_label_4"]

def row_extra(pid, variant):
    a = A[pid]; k = kind(a["title"]); linha, momento = labels(a)
    size = variant.get("title") or ""
    if size.lower() in ("default title", ""): size = "Único"
    return [color(a), size, "female", "adult", material(a.get("material")),
            CAT_OUTFIT_SET if k == "conjunto" else CAT_ACTIVEWEAR, PRODUCT_TYPE[k],
            "Yes" if k == "conjunto" else "No", "BR",
            color(a).lower(), k, linha, momento]
