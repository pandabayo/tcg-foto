# processa_carte.py - CORRETTO
import os
import json
from tcg_text_formatter import componi_annuncio_pokemon

BASE = os.path.dirname(os.path.abspath(__file__))

MAPPA_SET = {
    "BLK": "Black Bolt", "SSP": "Surging Sparks", "MEW": "151",
    "SVI": "Scarlet & Violet", "PAL": "Paldea Evolved", "OBF": "Obsidian Flames",
    "PAR": "Paradox Rift", "PAF": "Paldean Fates", "TEF": "Temporal Forces",
    "TWM": "Twilight Masquerade", "SFA": "Shrouded Fable", "SCR": "Stellar Crown",
    "PRE": "Prismatic Evolutions", "SVP": "SV Black Star Promo", "151": "Pokémon 151",
    "UNK": "Espansione Sconosciuta"
}

def elabora_lotto():
    map_path = os.path.join(BASE, "_lotto_map.json")
    if not os.path.exists(map_path):
        print("File _lotto_map.json non trovato.")
        return

    with open(map_path, "r", encoding="utf-8") as f:
        lotto = json.load(f)

    for item in lotto:
        nome = item.get("nome", "Pokemon")
        numero = item.get("numero", "001/001")
        set_code = item.get("set", "UNK")
        lingua = item.get("lingua", "ITA")
        rarita = item.get("rarita", "Comune")
        finitura = item.get("finitura", "base")

        set_nome = MAPPA_SET.get(set_code, set_code)

        # ✅ PASSA TUTTI I PARAMETRI
        annuncio = componi_annuncio_pokemon(
            nome=nome,
            numero=numero,
            set_nome=set_nome,
            set_codice=set_code,
            lingua_codice=lingua,
            rarita=rarita,
            finitura=finitura,
            categoria="normale"
        )

        item["title"] = annuncio["title"]
        item["description"] = annuncio["description"]

    with open(map_path, "w", encoding="utf-8") as f:
        json.dump(lotto, f, ensure_ascii=False, indent=2)

    print(f"Elaborati {len(lotto)} annunci con dati completi.")

if __name__ == "__main__":
    elabora_lotto()