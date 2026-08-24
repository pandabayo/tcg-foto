#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import subprocess
import sys
import os

def main():
    steps = [
        ("_prep_lotto.py", "1/5 Preparazione lotto ed estrazione OCR"),
        ("processa_carte.py", "2/5 Elaborazione e pulizia dati carte"),
        ("tcg_text_formatter.py", "3/5 Formattazione testi TCG"),
        ("ct_prezzi.py", "4/5 Recupero prezzi CardTrader"),
        ("_build_csv.py", "5/5 Generazione CSV finale per Vinted")
    ]
    
    for script, label in steps:
        print(f"\n========================================\nAVVIO STEP: {label}\n========================================")
        result = subprocess.run([sys.executable, script])
        if result.returncode != 0:
            print(f"\n⚠️  Errore durante l'esecuzione di {script}.")
            # Se fallisce ct_prezzi ma gli altri step erano ok, continua con _build_csv
            if script == "ct_prezzi.py":
                print("⚠️  Continuo senza prezzi CardTrader (tutte le carte avranno prezzo 1.00 EUR)")
                continue
            else:
                print("Interruzione pipeline.")
                sys.exit(result.returncode)

    # Push automatico su GitHub
    print("\n========================================\nAVVIO STEP: Push foto su GitHub\n========================================")
    try:
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", "Caricamento automatico foto lotto"], check=True)
        subprocess.run(["git", "push"], check=True)
        print("✅ Foto caricate con successo su GitHub!")
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Errore durante il git push: {e}")
        print("Nota: Il CSV è comunque stato generato localmente.")

    print("\n========================================\n✅ PIPELINE COMPLETATA CON SUCCESSO!\n========================================")

if __name__ == "__main__":
    main()