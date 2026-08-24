#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import csv, os, json, datetime, re
from urllib.parse import quote

BASE = os.path.dirname(os.path.abspath(__file__))
STAGE = os.path.join(BASE, "_stage_git")
GH = "https://raw.githubusercontent.com/pandabayo/tcg-foto/main/_stage_git"

HEADER = ["id","title","description","brand_id","brand","color1_id","color2_id","isbn","is_unisex","catalog_id","size_id","status_id","package_size_id","item_attributes","video_game_rating_id","measurement_length","measurement_width","price","currency"]+["photo_%d"%i for i in range(1,21)]+["sku","restock_enabled","restock_quantity","location","messages_enabled","accept_offers_enabled","minimum_offer_price","counter_offer_price","purchase_price"]

def clean_filename(s):
    if not s: return ""
    cleaned = re.sub(r'[\\/*?:"<>|]', '_', str(s))
    return cleaned.strip()

def build_csv():
    map_path = os.path.join(BASE, "_lotto_map.json")
    if not os.path.exists(map_path):
        print("Errore: _lotto_map.json non trovato. Esegui prima _prep_lotto.py")
        return

    prices = {}
    price_path = os.path.join(BASE, "_prezzi-cardtrader.csv")
    if os.path.exists(price_path):
        with open(price_path, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                val = r.get("prezzo_vinted")
                prices[r["key"]] = val if val is not None else "1.00"

    with open(map_path, encoding="utf-8") as f:
        lotto_map = json.load(f)
        
    rows = []
    for item in lotto_map:
        key = item["key"]
        
        raw_slug = item.get("slug") or item.get("sku") or item.get("key")
        clean_slug = clean_filename(raw_slug)
        
        if item.get("is_flat"):
            final_price = "1.00"
        else:
            final_price = prices.get(key)
            if final_price is None:
                final_price = "1.00"
        
        raw_p1 = item.get("photo_1") or f"{clean_slug}-FRONTE.jpg"
        raw_p2 = item.get("photo_2") or f"{clean_slug}-RETRO.jpg"
        
        p1 = f"{GH}/{quote(raw_p1)}" if not raw_p1.startswith("http") else raw_p1
        p2 = f"{GH}/{quote(raw_p2)}" if not raw_p2.startswith("http") else raw_p2
        
        r = {k: "" for k in HEADER}
        r["title"] = item.get("title", "")
        r["description"] = item.get("description", "")
        r["price"] = final_price
        r["currency"] = "EUR"
        r["sku"] = clean_slug
        r["catalog_id"] = "4875"
        r["brand_id"] = "191646"
        r["brand"] = "Pokémon"
        r["status_id"] = "2"
        r["package_size_id"] = "1"
        r["color1_id"] = "15"
        r["photo_1"] = p1
        r["photo_2"] = p2
        rows.append(r)

    today = datetime.date.today().strftime("%Y %m %d")
    out_csv = os.path.join(BASE, f"{today}_Pokemon_{len(rows)}.csv")
    
    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=HEADER)
        w.writeheader()
        w.writerows(rows)

    print(f"File generato con successo: {out_csv} ({len(rows)} inserzioni)")

if __name__ == "__main__":
    build_csv()