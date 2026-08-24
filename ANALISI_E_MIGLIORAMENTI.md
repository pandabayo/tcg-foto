# ANALISI ERRORI E MIGLIORAMENTI — TCG Vinted CSV Pipeline

## PROBLEMI CRITICI IDENTIFICATI

### 1. **ct_prezzi.py — Incompleto e non funzionante**
**Linea 98-101**: La funzione `get_prices()` termina bruscamente:
```python
def get_prices(bp_id, lingua):
    loc = LANG.get((lingua or "").upper(), "it")
    data = api_get("/marketplace/products", {"blueprint_id": bp_id, "language": loc})
    if not data: return {"avg5": "", "min": ""}
    # ❌ TRONCO QUI
```

**Impatto**: Il prezzo non viene mai calcolato; tutte le carte avranno `price` = "1.00"
(fallback del fallback), annullando la pricing strategy.

**Fix**:
```python
def get_prices(bp_id, lingua):
    loc = LANG.get((lingua or "").upper(), "it")
    data = api_get("/marketplace/products", {"blueprint_id": bp_id, "language": loc})
    if not data: 
        return {"avg5": "", "min": ""}
    
    # Deserializza la risposta di CardTrader
    prods = []
    if isinstance(data, dict):
        prods = data.get(str(bp_id), []) or list(data.values())[0] if data else []
    elif isinstance(data, list):
        prods = data
    
    # Filtra: Near Mint, non sigillate, non valutate
    nm_prices = []
    for p in (prods or []):
        props = p.get("properties_hash") or {}
        if props.get("sealed") or p.get("graded"):
            continue
        price_cents = p.get("price_cents")
        if price_cents is None:
            continue
        if props.get("condition") in ("Mint", "Near Mint"):
            nm_prices.append(price_cents)
    
    if not nm_prices:
        return {"avg5": "", "min": ""}
    
    # Media dei 5 più bassi
    nm_prices.sort()
    avg5 = sum(nm_prices[:5]) / len(nm_prices[:5]) / 100.0
    return {
        "avg5": round(avg5, 2),
        "min": round(nm_prices[0] / 100.0, 2)
    }
```

---

### 2. **_build_csv.py — Foto generate male, URL mancanti**

**Linea 43-44**: Costruisce URL solo se non inizia con "http", ma i nomi file sono errati:
```python
raw_p1 = item.get("photo_1") or f"{clean_slug}-FRONTE.jpg"
raw_p2 = item.get("photo_2") or f"{clean_slug}-RETRO.jpg"
p1 = f"{GH}/{quote(raw_p1)}" if not raw_p1.startswith("http") else raw_p1
```

**Problema**: 
- `quote()` codifica `*` e altri caratteri: `Pokemon_Base_001_001_UNK_ITA_1-FRONTE.jpg` 
  diventa `Pokemon_Base_001_001_UNK_ITA_1-FRONTE.jpg` (OK), ma se il nome ha spazi 
  → `quote()` trasforma in `%20`, causando 404 su GitHub.
- Non controlla se il file esiste veramente in `_stage_git/`.
- Non valida l'URL finale.

**Fix**:
```python
def build_csv():
    map_path = os.path.join(BASE, "_lotto_map.json")
    if not os.path.exists(map_path):
        print("Errore: _lotto_map.json non trovato.")
        return

    prices = {}
    price_path = os.path.join(BASE, "_prezzi-cardtrader.csv")
    if os.path.exists(price_path):
        with open(price_path, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                key = r.get("key")
                price = r.get("prezzo_vinted")
                if key and price:
                    prices[key] = price

    with open(map_path, encoding="utf-8") as f:
        lotto_map = json.load(f)
    
    rows = []
    missing_photos = []
    
    for item in lotto_map:
        key = item["key"]
        raw_slug = item.get("slug") or item.get("sku") or item.get("key")
        clean_slug = clean_filename(raw_slug)
        
        # Prezzo: flat1eur → 1.00, altrimenti da CardTrader, fallback 1.00
        if item.get("is_flat"):
            final_price = "1.00"
        else:
            final_price = prices.get(key, "1.00")
        
        # Foto: verificare che esistano in _stage_git/
        p1_name = item.get("photo_1") or f"{clean_slug}-FRONTE.jpg"
        p2_name = item.get("photo_2") or f"{clean_slug}-RETRO.jpg"
        
        p1_path = os.path.join(STAGE, p1_name)
        p2_path = os.path.join(STAGE, p2_name)
        
        if not os.path.exists(p1_path):
            missing_photos.append((key, "FRONTE", p1_name))
        if not os.path.exists(p2_path):
            missing_photos.append((key, "RETRO", p2_name))
        
        # URL GitHub (raw content)
        p1_url = f"{GH}/{p1_name}" if os.path.exists(p1_path) else ""
        p2_url = f"{GH}/{p2_name}" if os.path.exists(p2_path) else ""
        
        r = {k: "" for k in HEADER}
        r["title"] = item.get("title", "")[:100]
        r["description"] = item.get("description", "")[:2000]
        r["price"] = final_price
        r["currency"] = "EUR"
        r["sku"] = clean_slug
        r["catalog_id"] = "4875"
        r["brand_id"] = "191646"
        r["brand"] = "Pokémon"
        r["status_id"] = "2"
        r["package_size_id"] = "1"
        r["color1_id"] = "15"
        r["photo_1"] = p1_url
        r["photo_2"] = p2_url
        rows.append(r)
    
    if missing_photos:
        print(f"\n⚠️  ATTENZIONE: Foto mancanti in _stage_git/:")
        for key, lato, nome in missing_photos:
            print(f"  - {key} ({lato}): {nome}")
    
    today = datetime.date.today().strftime("%Y %m %d")
    out_csv = os.path.join(BASE, f"{today}_Pokemon_{len(rows)}.csv")
    
    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=HEADER)
        w.writeheader()
        w.writerows(rows)

    print(f"✅ CSV generato: {out_csv} ({len(rows)} inserzioni)")
```

---

### 3. **tcg_text_formatter.py — Hashtag duplicati, hashtag non puliti**

**Linea 50-70**: Genera hashtag sporchi:
```python
def genera_hashtags(nome: str, set_codice: str, lingua: str, tipo: str, rarita: str, ...):
    tags = [
        "#PokemonTCG",
        "#Pokemon",
        f"#{pulisci_tag(nome)}",  # "Pikachu" → "#Pikachu" ✓
        ...
    ]
    seen = set()
    tags_unici = [x for x in tags if not (x in seen or seen.add(x))]
    return " ".join(tags_unici)
```

**Problema**:
- `pulisci_tag()` rimuove `'` e `-`, quindi "Pokémon ex" → "PokemonEx", ma poi 
  può perdere la distinzione tra "Pokémon" e "Pokemon".
- Se il nome è vuoto o "Pokemon", aggiunge `#Pokemon` due volte (una da nome, 
  una fissa).
- I set europei (Deu, Fra, Spa) non vengono convertiti in inglese, quindi 
  `#CartaAllenatore` per una carta Deu diventa `#CartaAllenatrice` (scorretta).

**Fix**:
```python
def pulisci_tag(testo: str) -> str:
    """Rimuove tutto tranne lettere, numeri, underscore."""
    return re.sub(r'[^a-zA-Z0-9_]', '', str(testo))

def genera_hashtags(nome: str, set_codice: str, lingua: str, tipo: str, 
                    rarita: str, finitura: str, categoria: str) -> str:
    """Genera hashtag deduplicati e corretti."""
    nome_clean = pulisci_tag(nome)
    set_clean = pulisci_tag(set_codice) if set_codice and set_codice != "NONE" else ""
    tipo_clean = pulisci_tag(tipo) if tipo and tipo != "NONE" else ""
    rarita_clean = pulisci_tag(rarita) if rarita and rarita not in ["Comune", "NONE"] else ""
    lingua_upper = (lingua or "").upper()
    
    tags = [
        "#PokemonTCG",
        "#Pokemon",
    ]
    
    # Nome della carta (senza duplicare "Pokemon")
    if nome_clean and nome_clean.lower() != "pokemon":
        tags.append(f"#{nome_clean}")
    
    # Categoria speciale
    if categoria == "trainer":
        tags.append("#CartaAllenatore")
    
    # Set
    if set_clean:
        tags.append(f"#{set_clean}")
    
    # Tipo energia
    if tipo_clean:
        tags.append(f"#Pokemon{tipo_clean}")
    
    # Rarità
    if rarita_clean:
        tags.append(f"#{rarita_clean}")
    
    # Lingua
    if lingua_upper:
        tags.append(f"#Pokemon{lingua_upper}")
    
    # Finitura
    if finitura and "Reverse" in finitura:
        tags.append("#Reverse")
    
    # Dedup
    seen = set()
    unique_tags = []
    for tag in tags:
        tag_lower = tag.lower()
        if tag_lower not in seen:
            seen.add(tag_lower)
            unique_tags.append(tag)
    
    return " ".join(unique_tags)
```

---

### 4. **_prep_lotto.py — Naming convention confusa, MDO hash mai usato**

**Linea 88-92**: Genera nomi file incoerenti:
```python
raw_key = f"{prefix}|{nome}|{numero}|{set_name}|{lingua}|{pair_index}"
clean_slug = clean_filename(f"{prefix}_{nome}_{clean_filename(numero)}_{clean_filename(set_name)}_{lingua}_{pair_index}")
target_fronte = f"{clean_slug}-FRONTE.jpg"
```

**Problema**:
- Se il numero è "001/189", `clean_filename()` lo trasforma in "001_189", rendendo 
  impossibile riconoscere il numero dal file.
- L'indice `pair_index` viene messo in coda, creando collisioni (due "Pikachu 001/001 ITA" 
  hanno slug diversi solo se in folder diversi).
- Lo hash MD5 della foto fronte non viene mai calcolato (skill richiede il controllo 
  duplicati per MD5).

**Fix**:
```python
import hashlib

def compute_file_hash(filepath):
    """Calcola MD5 del file per rilevare duplicati."""
    hash_md5 = hashlib.md5()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        print(f"Errore nel calcolo hash di {filepath}: {e}")
        return ""

def process_folder(folder_path, is_flat_1eur=False):
    scan_files = get_sorted_scans(folder_path)
    if not scan_files:
        return [], []

    if len(scan_files) % 2 != 0:
        print(f"⚠️  [{os.path.basename(folder_path)}]: {len(scan_files)} immagini (dispari)")

    items = []
    prezzi_req = []
    pair_index = 1

    for i in range(0, len(scan_files), 2):
        fronte_name = scan_files[i]
        retro_name = scan_files[i+1] if (i+1) < len(scan_files) else None

        fronte_path = os.path.join(folder_path, fronte_name)
        retro_path = os.path.join(folder_path, retro_name) if retro_name else None

        # Calcola hash MD5 del fronte per duplicati
        hash_fronte = compute_file_hash(fronte_path)

        # Lettura OCR/metadata
        card_data = {}
        if not is_flat_1eur and ocr and hasattr(ocr, 'process_card'):
            try:
                card_data = ocr.process_card(fronte_path)
            except Exception as e:
                print(f"Errore OCR su {fronte_name}: {e}")

        prefix = "Flat1Eur" if is_flat_1eur else "Pokemon"
        nome = card_data.get("nome", "").strip() or "Carta"
        set_name = card_data.get("set", "").strip() or "UNK"
        numero = card_data.get("numero", "").strip() or "001/001"
        lingua = card_data.get("lingua", "").strip() or "ITA"

        # Slug: numero deve restare leggibile (001-189, non 001_189)
        numero_slug = numero.replace("/", "-")  # 001/189 → 001-189
        clean_slug = clean_filename(
            f"{prefix}_{nome}_{numero_slug}_{set_name}_{lingua}_{pair_index}"
        )
        
        raw_key = f"{prefix}|{nome}|{numero}|{set_name}|{lingua}|{pair_index}"

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
            "description": f"Carta Pokémon {nome}. Set: {set_name}, Numero: {numero}, Lingua: {lingua}",
            "photo_1": target_fronte,
            "photo_2": target_retro,
            "is_flat": is_flat_1eur,
            "hash_fronte": hash_fronte
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
```

---

### 5. **ocr_tcg_processor.py — Parsing fragile, rarità mai letta**

**Linea 32-47**: Non estrae la rarità dal simbolo:
```python
def parse_numero_set(testo):
    match_num = re.search(r'(\d{1,3}/\d{1,3})', testo)
    numero = match_num.group(1) if match_num else "001/001"
    # ... set_codice
    return numero, set_codice

def pulisci_nome(testo):
    parole = re.findall(r'[a-zA-Z]{3,}', testo)
    for p in parole:
        p_upper = p.upper()
        if p_upper not in ["POKEMON", ...]:
            return p.capitalize()
    return "Pokemon"

def process_card(image_path):
    testo_completo = estrai_testo_immagine(image_path)
    numero, set_code = parse_numero_set(testo_completo)
    nome = pulisci_nome(testo_completo)
    # ❌ Rarità NON estratta
```

**Problema**:
- Estrae solo nome, numero, set da OCR testuale.
- La rarità (simbolo ● ◆ ★ ecc.) non è testo leggibile dall'OCR; va riconosciuta 
  da crop separati o visione.
- Tutti gli annunci hanno rarità "Comune" (default), che è quasi sempre sbagliato.

**Fix** (parziale; richiede agenti per il simbolo):
```python
def process_card(image_path, crop_symbol_path=None):
    """
    Estrae nome, numero, set, lingua da fronte.
    La rarità e finitura vanno lette dagli agenti su crop dedicati.
    """
    testo_completo = estrai_testo_immagine(image_path)
    numero, set_code = parse_numero_set(testo_completo)
    nome = pulisci_nome(testo_completo)
    lingua = estrai_lingua(testo_completo)

    title = f"{nome} {numero} Pokémon TCG {lingua}"[:100]
    
    set_esteso = MAPPA_SET.get(set_code, set_code)
    
    description = f"""🎴 Vendo carta Pokémon TCG {nome} {numero} in {lingua} originale.

✨ Carta Pokémon singola dell'espansione {set_esteso} ({set_code}), ideale per collezionisti e giocatori Pokémon TCG.

📋 Dettagli:
Nome: {nome}
Numero: {numero}
Espansione: {set_esteso}
Lingua: {lingua}
Condizioni: [Rarità da agente]

📸 Riceverai esattamente ciò che vedi in foto. Le foto sono parte integrante della descrizione."""

    return {
        "nome": nome,
        "title": title,
        "description": description,
        "set": set_code,
        "numero": numero,
        "lingua": lingua,
        "rarità": "DA_LEGGERE_DA_AGENTE",
        "finitura": "DA_LEGGERE_DA_AGENTE"
    }

def estrai_lingua(testo):
    """Rileva lingua dal testo OCR (molto approssimativo)."""
    testo_lower = testo.lower()
    # Pattern semplici: parole chiave in varie lingue
    if any(w in testo_lower for w in ["energie", "tipi", "attacchi", "difesa"]):
        return "ITA"
    if any(w in testo_lower for w in ["energy", "type", "attack", "defense"]):
        return "ENG"
    if any(w in testo_lower for w in ["énergie", "type", "attaque", "défense"]):
        return "FRA"
    if any(w in testo_lower for w in ["energía", "tipo", "ataque", "defensa"]):
        return "SPA"
    return "ENG"  # default
```

---

### 6. **run_pipeline.py — Ordine di esecuzione sbagliato**

**Linea 7-19**: Esegue processa_carte.py PRIMA di ct_prezzi.py:
```python
steps = [
    ("_prep_lotto.py", "1/5 Preparazione lotto"),
    ("processa_carte.py", "2/5 Elaborazione"),  # ❌ Tenta di aggiornare title/description
    ("tcg_text_formatter.py", "3/5 Formattazione testi"),
    ("ct_prezzi.py", "4/5 Recupero prezzi"),    # ❌ Legge _prezzi-da-recuperare.csv
    ("_build_csv.py", "5/5 Generazione CSV")
]
```

**Problema**:
- `processa_carte.py` tenta di aggiornare `title` e `description` leggendo dal 
  file _lotto_map.json, ma questi campi NON sono stati ancora popolati da `_prep_lotto.py`.
- `ct_prezzi.py` legge `_prezzi-da-recuperare.csv` generato da `_prep_lotto.py`, 
  ma se non esiste → crash silenzioso (solo print "non trovato").
- L'ordine è incoerente con la skill.

**Fix**:
```python
def main():
    steps = [
        ("_prep_lotto.py", "1/4 Preparazione lotto e staging foto"),
        ("ct_prezzi.py", "2/4 Recupero prezzi da CardTrader (offline)"),
        ("_build_csv.py", "3/4 Generazione CSV per Vinted"),
        ("verifica_finale.py", "4/4 Verifica integrità CSV e foto")
    ]
    
    # Nota: tcg_text_formatter.py è importato da _prep_lotto.py
    # processa_carte.py non è necessario (integrato in _prep_lotto.py)
```

---

### 7. **tcg_text_formatter.py — Lingua nel qualificatore ignorata**

**Linea 71-95**: Il qualificatore NON varia con la lingua:
```python
def componi_annuncio_pokemon(...):
    qualificatore = genera_qualificatore(finitura, rarita)
    # qualificatore = "Holo Rare" oppure "Rara" oppure ""
    
    if qualificatore:
        title = f"{nome} {numero} {qualificatore} {lingua_codice.capitalize()}"
    else:
        title = f"{nome} {numero} Pokémon TCG {lingua_codice.capitalize()}"
```

**Problema**:
- Se la rarità è "Rara" (nome italiano), il titolo recita: "Pikachu 001/025 Rara Ita" 
  (scorretto: mescola ita e ingl).
- Se è "Rare" (inglese internazionale), il titolo è OK: "Pikachu 001/025 Rare Ita".
- Il qualificatore deve essere SEMPRE in inglese internazionale.

**Fix**:
```python
RARITÀ_ITA_TO_ENG = {
    "Comune": "Common",
    "Non Comune": "Uncommon",
    "Rara": "Rare",
    "Holo Rare": "Holo Rare",
    "Double Rare": "Double Rare",
    "Ultra Rara": "Ultra Rare",
    "Illustrazione Speciale Rara": "Special Illustration Rare",
    "Promo": "Promo"
}

def componi_annuncio_pokemon(
    nome: str,
    numero: str,
    set_nome: str,
    set_codice: str,
    lingua_codice: str,
    rarita: str = "Common",
    finitura: str = "base",
    categoria: str = "normale",
    condizione: str = "Near Mint",
    tipo_energia: str = ""
) -> dict:
    # Converti rarità in inglese se necessario
    rarita_eng = RARITÀ_ITA_TO_ENG.get(rarita, rarita)  # fallback al valore passato
    
    qualificatore = genera_qualificatore(finitura, rarita_eng)
    lingua_cap = lingua_codice.capitalize()
    
    if qualificatore:
        title = f"{nome} {numero} {qualificatore} {lingua_cap}"
    else:
        title = f"{nome} {numero} Pokémon TCG {lingua_cap}"
    
    title = title[:100].strip()
    # ... resto
```

---

## RIASSUNTO DEGLI ERRORI E PRIORITÀ

| # | File | Problema | Severità | Fix |
|---|------|----------|----------|-----|
| 1 | `ct_prezzi.py` | Funzione `get_prices()` incompleta | **CRITICA** | Completare la logica di filtraggio |
| 2 | `_build_csv.py` | URL foto non valide, file non verificati | **CRITICA** | Verificare file in `_stage_git/`, usare raw URL |
| 3 | `ocr_tcg_processor.py` | Rarità e finitura mai estratte | **ALTA** | Delegare agli agenti; basarsi su crop simboli |
| 4 | `tcg_text_formatter.py` | Hashtag duplicati, lingua mescolata | **MEDIA** | Dedup case-insensitive, rarità in inglese |
| 5 | `_prep_lotto.py` | Slug confuso, hash MD5 mai calcolato | **MEDIA** | Numero slug: `001-189`, calcola MD5 |
| 6 | `run_pipeline.py` | Ordine esecuzione sbagliato | **MEDIA** | Riordina: prep → prezzi → csv |
| 7 | Varie | `processa_carte.py` non necessario | **BASSA** | Eliminare o integrare in `_prep_lotto.py` |

---

## MIGLIORAMENTI PROPOSTI

### A. Centralizzare la configurazione

Crea `_config.json`:
```json
{
  "github": {
    "owner": "pandabayo",
    "repo": "tcg-foto",
    "branch": "main",
    "raw_url": "https://raw.githubusercontent.com/pandabayo/tcg-foto/main",
    "token": "ghp_XXXXX"
  },
  "cardtrader": {
    "api_url": "https://api.cardtrader.com/api/v2",
    "token_file": ".ct_token.txt",
    "cache_dir": "_cache"
  },
  "dotb": {
    "catalog_id": "4875",
    "brand_id": "191646",
    "brand": "Pokémon",
    "status_id": "2",
    "package_size_id": "1",
    "color1_id": "15",
    "currency": "EUR"
  },
  "logging": {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  }
}
```

Tutti gli script leggono da qui.

### B. Logging strutturato

Aggiungi `logging` a ogni script:
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Al posto di print():
logger.info("CSV generato con successo")
logger.warning("Foto mancante: %s", foto_nome)
logger.error("Errore nel parsing: %s", str(e))
```

### C. Validazione schema CSV

Aggiungi in `_build_csv.py`:
```python
def valida_csv(rows, header):
    """Verifica che tutte le righe abbiano i campi corretti."""
    for i, row in enumerate(rows, start=2):  # skip header
        for col in header:
            if col not in row:
                logger.error(f"Riga {i}: colonna '{col}' mancante")
                return False
        if not row.get("photo_1"):
            logger.warning(f"Riga {i}: photo_1 vuota (SKU: {row.get('sku')})")
    return True
```

### D. Verifica URL foto

Aggiungi in `_build_csv.py`:
```python
def verifica_url_foto(url):
    """Verifica che l'URL GitHub sia valido (non accetta HEAD di GitHub)."""
    # GitHub raw content non supporta HEAD; si prova il download ridotto
    if not url:
        return False
    # Verifica solo il formato; il vero controllo è il file locale
    return url.startswith("https://raw.githubusercontent.com/")

# Nel loop:
if not verifica_url_foto(p1_url):
    logger.warning(f"URL foto_1 invalida per {key}: {p1_url}")
```

### E. Report dettagliato post-run

Crea `genera_report.py`:
```python
def genera_report(rows_csv, prezzi_ok, prezzi_manuali, foto_mancanti, duplicati):
    report = f"""
# Report finale — {datetime.datetime.now().isoformat()}

## Riepilogo
- Inserzioni generate: {len(rows_csv)}
- Prezzi da CardTrader: {len(prezzi_ok)}
- Prezzi manuali: {len(prezzi_manuali)}
- Foto mancanti: {len(foto_mancanti)}
- Duplicati rilevati: {len(duplicati)}

## Prezzi manuali (azione richiesta)
{chr(10).join(f'- {k}' for k in prezzi_manuali)}

## Foto mancanti
{chr(10).join(f'- {k} ({lato}): {nome}' for k, lato, nome in foto_mancanti)}

## Duplicati
{chr(10).join(f'- {k}' for k in duplicati)}
"""
    with open(f"Report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.md", "w") as f:
        f.write(report)
```

---

## FILE CORRETTO/OTTIMIZZATO (Priorità 1-3)

Vedi gli snippet sopra per:
1. ✅ `ct_prezzi.py` — Completa `get_prices()`
2. ✅ `_build_csv.py` — Verifica foto, URL raw corretti
3. ✅ `_prep_lotto.py` — Hash MD5, slug leggibile, naming coerente

Applica questi fix e riporta. Il resto è miglioramento graduale.
