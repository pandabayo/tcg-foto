import os
import re
import warnings

warnings.filterwarnings("ignore", category=UserWarning)

import easyocr

reader = easyocr.Reader(['it', 'en'], gpu=False)

MAPPA_SET = {
    'SVI': 'Scarlet & Violet', 'PAL': 'Paldea Evolved', 'OBF': 'Obsidian Flames',
    'MEW': 'Pokémon 151', '151': 'Pokémon 151', 'PAR': 'Paradox Rift',
    'PAF': 'Paldean Fates', 'TEF': 'Temporal Forces', 'TWM': 'Twilight Masquerade',
    'SFA': 'Shrouded Fable', 'SCR': 'Stellar Crown', 'SSP': 'Surging Sparks',
    'PRE': 'Prismatic Evolutions', 'SVP': 'SV Black Star Promo'
}

def estrai_testo_immagine(image_path):
    try:
        results = reader.readtext(image_path, detail=0)
        return " ".join(results)
    except Exception as e:
        print(f"Errore lettura OCR su {image_path}: {e}")
        return ""

def parse_numero_set(testo):
    match_num = re.search(r'(\d{1,3}/\d{1,3})', testo)
    numero = match_num.group(1) if match_num else "001/001"
    
    set_codice = "UNK"
    for cod in MAPPA_SET.keys():
        if cod in testo:
            set_codice = cod
            break
            
    return numero, set_codice

def pulisci_nome(testo):
    parole = re.findall(r'[a-zA-Z]{3,}', testo)
    for p in parole:
        p_upper = p.upper()
        if p_upper not in ["POKEMON", "CARD", "BASIC", "STAGE", "TRAINER", "ENERGY", "ALLENATORE", "STRUMENTO", "AIUTO"]:
            return p.capitalize()
    return "Pokemon"

def process_card(image_path):
    testo_completo = estrai_testo_immagine(image_path)
    
    numero, set_code = parse_numero_set(testo_completo)
    nome = pulisci_nome(testo_completo)
    lingua = "ITA"
    set_esteso = f"{MAPPA_SET.get(set_code, set_code)} ({set_code})"

    title = f"{nome} {numero} Pokémon TCG {lingua}"[:100]

    description = f"""🎴 Vendo carta Pokémon TCG {nome} {numero} in {lingua} originale.

✨ Carta Pokémon singola dell'espansione {set_esteso}, ideale per collezionisti e giocatori Pokémon TCG.

📋 Dettagli:
Nome: {nome}
Numero: {numero}
Espansione: {set_esteso}
Lingua: {lingua}
Condizioni: Ottime Condizioni

📸 Riceverai esattamente ciò che vedi in foto. Le foto sono parte integrante della descrizione.
📦 La carta verrà spedita protetta con sleeve e/o supporto rigido per garantirne la massima sicurezza durante il trasporto.
🚚 Spedizione generalmente effettuata entro 24h lavorative.
🛒 Consulta il mio armadio per altre carte Pokémon e annunci simili.
💥 Acquistando più articoli puoi creare un set e ottenere sconti dedicati.

#PokemonTCG #Pokemon #{nome.replace(' ', '')} #CartaPokemon #CartePokemon #{set_code}"""

    return {
        "nome": nome,
        "title": title,
        "description": description,
        "set": set_code,
        "numero": numero,
        "lingua": lingua
    }

if __name__ == "__main__":
    print("Modulo ocr_tcg_processor pronto per l'integrazione.")