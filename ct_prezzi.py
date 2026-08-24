#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, json, time, csv, re, unicodedata
import urllib.request, urllib.parse, urllib.error

API = "https://api.cardtrader.com/api/v2"
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "_cache")
os.makedirs(CACHE, exist_ok=True)
TOKEN = None

def load_token():
    # Prova prima nella cartella del progetto
    base_token = os.path.join(HERE, ".ct_token.txt")
    if os.path.exists(base_token):
        return open(base_token, encoding="utf-8").read().strip()
    
    # Poi nella home directory (fallback)
    home = os.path.expanduser("~")
    for name in (".ct_token", ".ct_token.txt", "ct_token.txt", "ct_token"):
        p = os.path.join(home, name)
        if os.path.exists(p):
            return open(p, encoding="utf-8").read().strip()
    sys.exit("Token non trovato: salva il token in .ct_token.txt nella cartella del progetto o in " + os.path.join(home, ".ct_token.txt"))

def api_get(path, params=None, retries=4):
    url = API + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    for attempt in range(retries):
        req = urllib.request.Request(url, headers={"Authorization": "Bearer " + TOKEN, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(2 + attempt * 2); continue
            return None
        except Exception:
            time.sleep(1 + attempt)
    return None

def as_list(data):
    if data is None: return []
    if isinstance(data, dict) and "array" in data: return data["array"]
    return data if isinstance(data, list) else [data]

def cache_json(name, producer):
    p = os.path.join(CACHE, name)
    if os.path.exists(p):
        try: return json.load(open(p, encoding="utf-8"))
        except Exception: pass
    data = producer()
    if data is not None:
        json.dump(data, open(p, "w", encoding="utf-8"), ensure_ascii=False)
    return data

def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()

LANG = {"ITA":"it","JAP":"jp","ENG":"en","KOR":"kr","DEU":"de","FRA":"fr","SPA":"es","CHN":"zh-CN"}

def get_expansions():
    return as_list(cache_json("ct_expansions.json", lambda: api_get("/expansions")))

def get_blueprints(exp_id):
    return as_list(cache_json("ct_blueprints_%s.json" % exp_id, lambda: api_get("/blueprints/export", {"expansion_id": exp_id})))

def split_set(setstr):
    m = re.match(r"^(.*?)\s*\(([^)]+)\)\s*$", setstr or "")
    if m: return norm(m.group(1)), norm(m.group(2))
    return norm(setstr), ""

def find_expansion(exps, setstr):
    name, code = split_set(setstr)
    pool = [e for e in exps if e.get("game_id") == 5] # 5 = Pokemon TCG
    for e in pool:
        if code and norm(e.get("code", "")) == code: return e
    for e in pool:
        if name and norm(e.get("name", "")) == name: return e
    return None

def find_blueprint(bps, nome, numero):
    nnome = norm(nome)
    nnum = re.sub(r"^0+", "", (numero or "").split("/")[0])
    if nnum:
        for bp in bps:
            cn = bp.get("collector_number") or bp.get("number") or ""
            if re.sub(r"^0+", "", str(cn).split("/")[0]) == nnum:
                return bp
    cands = [bp for bp in bps if nnome in norm(bp.get("name", ""))]
    return cands[0] if cands else None

def get_prices(bp_id, lingua):
    loc = LANG.get((lingua or "").upper(), "it")
    data = api_get("/marketplace/products", {"blueprint_id": bp_id, "language": loc})
    if not data: return {"avg5": "", "min": ""}
    prods = data.get(str(bp_id)) if isinstance(data, dict) else list(data.values())[0] if data else []
    nm = []
    for p in prods or []:
        ph = p.get("properties_hash") or {}
        if ph.get("sealed") or p.get("graded"): continue
        c = p.get("price_cents")
        if c is None: continue
        if ph.get("condition") in ("Mint", "Near Mint"):
            nm.append(c)
    if not nm: return {"avg5": "", "min": ""}
    nm.sort()
    avg5 = round(sum(nm[:5]) / len(nm[:5]) / 100.0, 2)
    return {"avg5": avg5, "min": round(nm[0] / 100.0, 2)}

SCAGLIONI = [(0.24, 1.00), (0.29, 1.09), (0.34, 1.19), (0.39, 1.29), (0.44, 1.39),
             (0.49, 1.49), (0.59, 1.59), (0.69, 1.79), (0.79, 1.89), (0.99, 1.99),
             (1.49, 2.49), (1.99, 2.99), (2.99, 3.99)]

def vinted_price(mkt):
    if not mkt: return "1.00"
    m = float(mkt)
    if m >= 3.0: return "" # prezzo manuale per carte costose
    for hi, price in SCAGLIONI:
        if m <= hi + 1e-9: return "%.2f" % price
    return "1.00"

def cmd_process():
    reqp = os.path.join(HERE, "_prezzi-da-recuperare.csv")
    if not os.path.exists(reqp): return
    exps = get_expansions()
    rows_in = list(csv.DictReader(open(reqp, encoding="utf-8")))
    out = []
    for r in rows_in:
        e = find_expansion(exps, r.get("set", ""))
        if not e:
            out.append({"key": r.get("key"), "prezzo_vinted": "1.00", "ct_min": "", "note": "exp non trovata"})
            continue
        bl = get_blueprints(e["id"])
        bp = find_blueprint(bl, r.get("nome", ""), r.get("numero", ""))
        if not bp:
            out.append({"key": r.get("key"), "prezzo_vinted": "1.00", "ct_min": "", "note": "bp non trovato"})
            continue
        pr = get_prices(bp["id"], r.get("lingua", ""))
        vp = vinted_price(pr.get("avg5"))
        out.append({"key": r.get("key"), "prezzo_vinted": vp or "1.00", "ct_min": pr.get("min", ""), "note": ""})
        time.sleep(0.3)
    
    with open(os.path.join(HERE, "_prezzi-cardtrader.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["key", "prezzo_vinted", "ct_min", "note"])
        w.writeheader()
        w.writerows(out)
    print("Recupero prezzi completato. File _prezzi-cardtrader.csv generato.")

if __name__ == "__main__":
    TOKEN = load_token()
    cmd_process()