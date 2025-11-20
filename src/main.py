# src/main.py

import os
from pathlib import Path
from urllib.parse import urljoin  # Važno za pravilno spajanje URL-ova
import time

# Uvozimo naše module
from config import BASE_URL_STRANICE, DOWNLOAD_FOLDER
from scraper import dohvati_html
from parser import parse_pdf_links
from storage import download_file

def main():
    print(f"--- Pokretanje PDF Scrapera za {BASE_URL_STRANICE} ---")
    
    # Korak 1: Dohvati HTML stranice koja lista fajlove
    html_sadrzaj = dohvati_html(BASE_URL_STRANICE)
    
    if not html_sadrzaj:
        print("Ne mogu da dohvatim listu fajlova. Prekidam.")
        return

    # Korak 2: Parsiraj HTML da izvučeš imena .pdf fajlova
    pdf_fajlovi = parse_pdf_links(html_sadrzaj)
    
    if not pdf_fajlovi:
        print("Nije pronađen nijedan .pdf link na stranici.")
        return
        
    print(f"Pronađeno ukupno {len(pdf_fajlovi)} PDF fajlova.")
    
    # Korak 3: Prođi kroz listu i preuzmi svaki fajl
    for i, ime_fajla in enumerate(pdf_fajlovi, 1):
        
        # Kreiraj puni, apsolutni URL za fajl
        # npr. "https://.../ckb/" + "0925ckb_bs.pdf"
        puni_url = urljoin(BASE_URL_STRANICE, ime_fajla)
        
        # Kreiraj relativnu putanju gde čuvamo fajl; ukloni vodeću kosu crtu
        # npr. "data/ckb_izvestaji/0925ckb_bs.pdf"
        relativna_putanja = Path(ime_fajla.lstrip("/"))
        lokalna_putanja = Path(DOWNLOAD_FOLDER) / relativna_putanja
        
        print(f"\n[{i}/{len(pdf_fajlovi)}] Preuzimam: {ime_fajla}")
        
        # Pozovi funkciju za preuzimanje
        download_file(puni_url, str(lokalna_putanja))
        
        # Budi fin prema serveru, napravi malu pauzu
        time.sleep(0.5) # Pauza od pola sekunde
    
    print(f"\n--- Preuzimanje završeno. Svi fajlovi su u '{DOWNLOAD_FOLDER}' ---")

# Standardni Python način da se pokrene 'main' funkcija
if __name__ == "__main__":
    main()