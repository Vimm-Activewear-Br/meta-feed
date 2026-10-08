"""short_description for the Meta feed, built from the product title. Phrases come from the site copy.
Meta flagged Flexify's 80-char phrase as 'Valor muito extenso', so everything here stays <= MAX."""
MAX = 60

def short_description(title):
    t = title.lower()
    if t.startswith("conjunto"):
        if "manguito" in t: s = "Conjunto de compressão com manguito para qualquer treino."
        elif "6 bolsos" in t: s = "Conjunto com top-blusa de 6 bolsos para treino e prova."
        elif "nadador" in t: s = "Conjunto com top nadador com bolso e alta sustentação."
        else: s = "Conjunto com top-blusa de alta sustentação e compressão."
    elif t.startswith("bermuda"):
        s = ("Bermuda curtinha" if "curtinha" in t else "Bermuda") + " de compressão para treinar sem calcinha."
    elif t.startswith("top-blusa"):
        s = "Top-blusa com 6 bolsos nas costas e alta sustentação." if "6 bolsos" in t else "Top-blusa com top embutido e alta sustentação."
    elif t.startswith("top nadador"):
        s = "Top nadador com bolso nas costas e alta sustentação." if "bolso" in t else "Top nadador de compressão com alta sustentação."
    elif t.startswith("manguito"): s = "Manguito leve para usar com os conjuntos Vimm."
    elif t.startswith("garrafinha"): s = "Garrafinha de 350ml que cabe nos bolsos dos tops Vimm."
    elif t.startswith("kit 2 bermudas"): s = "Monte seu kit com 2 bermudas de compressão."
    elif t.startswith("macaquinho"): s = "Macaquinho de triathlon feito para o corpo da mulher."
    elif t.startswith("envelope"): s = "Envelope para presente Vimm."
    else: s = title
    assert len(s) <= MAX, (len(s), s)
    return s
