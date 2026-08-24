# _prep_lotto.py - CORRETTO
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, json, csv, re, shutil

try:
    import ocr_tcg_processor as ocr
except ImportError:
    ocr = None

BASE = os.path.dirname(os.path.abspath(__file__))
STAGE = os.path.join(BASE, "_stage_git")
os.makedirs(STAGE, exist_ok=True)

DIR_SCANSIONI = os.path.join(BASE, "0. Scansioni")
DIR_FLAT1EUR = os.path.join(BASE, "Flat1Eur")

os.makedirs(DIR_SCANSIONI, exist_ok=True)
os.makedirs(DIR_FLAT1EUR, exist_ok=True)

def sort_scan_files(filename):
    match = re.search(r'\((\d+)\)', filename)
    return int(match.group(1)) if match else 0

def get_sorted_scans(directory):
    if not os.path.exists(directory):
        return []
    exts = ('.jpg', '.jpeg', '.png', '.webp')
    files = [f for f in os.listdir(directory) if f.lower().endswith(exts)]
    files.sort(key=sort_scan_files)
    return files

def clean_filename(s):
    if not s: return ""
    cleaned = re.sub(r'[\\/*?:"<>|]', '_', str(s))
    return cleaned.strip()

def extract_card_data(image_path):
    """Estrai dati dalla carta usando OCR"""
    if not ocr:
        return {}
    try:
        return ocr.process_card(image_path)
    except Exception as e:
        print(f"Errore OCR su {image_path}: {e}")
        return {}

def process_folder(folder_path, is_flat_1eur=False):
    scan_files = get_sorted_scans(folder_path)
    if not scan_files:
        return [], []

    if len(scan_files) % 2 != 0:
        print(f"ATTENZIONE [{os.path.basename(folder_path)}]: {len(scan_files)} immagini (dispari).")

    items = []
    prezzi_req = []
    pair_index = 1

    for i in range(0, len(scan_files), 2):
        fronte_name = scan_files[i]
        retro_name = scan_files[i+1] if (i+1) < len(scan_files) else None

        fronte_path = os.path.join(folder_path, fronte_name)
        retro_path = os.path.join(folder_path, retro_name) if retro_name else None

        # Estrai dati OCR
        card_data = extract_card_data(fronte_path) if not is_flat_1eur else {}

        prefix = "Pokemon" if not is_flat_1eur else "Flat1Eur"
        nome = card_data.get("nome", f"Card_{pair_index}")
        numero = card_data.get("numero", f"{pair_index:03d}/001")
        set_name = card_data.get("set", "UNK")
        lingua = card_data.get("lingua", "ITA")
        rarita = card_data.get("rarita", "Comune")
        finitura = card_data.get("finitura", "base")

        raw_key = f"{prefix}|{nome}|{numero}|{set_name}|{lingua}|{pair_index}"
        clean_slug = clean_filename(f"{prefix}_{nome}_{clean_filename(numero)}_{set_name}_{lingua}_{pair_index}")

        target_fronte = f"{clean_slug}-FRONTE.jpg"
        target_retro = f"{clean_slug}-RETRO.jpg"

        shutil.copy2(fronte_path, os.path.join(STAGE, target_fronte))
        if retro_path:
            shutil.copy2(retro_path, os.path.join(STAGE, target_retro))

        item_entry = {
            "key": raw_key,
            "slug": clean_slug,
            "sku": clean_slug,
            "title": f"{nome} {numero} Pokémon TCG {lingua}",
            "description": f"Carta Pokémon {nome} {numero} - {set_name}",
            "photo_1": target_fronte,
            "photo_2": target_retro,
            "is_flat": is_flat_1eur,
            "nome": nome,
            "numero": numero,
            "set": set_name,
            "lingua": lingua,
            "rarita": rarita,
            "finitura": finitura
        }
        items.append(item_entry)

        if not is_flat_1eur:
            prezzi_req.append({
                "key": raw_key,
                "nome": nome,
                "set": set_name,
                "numero": numero,
                "lingua": lingua
            })

        pair_index += 1

    return items, prezzi_req

def prep_lotto():
    print("Recupero scansioni da '0. Scansioni'...")
    scans_items, prezzi_req = process_folder(DIR_SCANSIONI, is_flat_1eur=False)
    
    print("Recupero carte da 'Flat1Eur'...")
    flat_items, _ = process_folder(DIR_FLAT1EUR, is_flat_1eur=True)

    all_items = scans_items + flat_items

    if not all_items:
        print("Nessuna immagine trovata.")
        return

    map_out = os.path.join(BASE, "_lotto_map.json")
    with open(map_out, "w", encoding="utf-8") as f:
        json.dump(all_items, f, ensure_ascii=False, indent=2)

    req_out = os.path.join(BASE, "_prezzi-da-recuperare.csv")
    with open(req_out, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["key", "nome", "set", "numero", "lingua"])
        writer.writeheader()
        writer.writerows(prezzi_req)

    print(f"Completato: {len(scans_items)} standard, {len(flat_items)} flat 1€.")

if __name__ == "__main__":
    prep_lotto()