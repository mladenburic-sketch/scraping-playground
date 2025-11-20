# src/pdf_to_csv.py

import os
from pathlib import Path
import csv
from typing import List, Optional

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

from config import DOWNLOAD_FOLDER


def extract_tables_from_pdf(pdf_path: Path) -> List[List[List[str]]]:
    """
    Ekstraktuje sve tabele iz PDF fajla.
    Vraća listu tabela, gde je svaka tabela lista redova, a svaki red lista ćelija.
    """
    if pdfplumber is None:
        raise ImportError(
            "pdfplumber nije instaliran. Pokreni 'pip install pdfplumber'"
        )
    
    tables = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                # Pokušaj da ekstraktuješ tabele sa stranice
                page_tables = page.extract_tables()
                if page_tables:
                    tables.extend(page_tables)
                    print(f"  Stranica {page_num}: pronađeno {len(page_tables)} tabela")
    except Exception as e:
        print(f"  Greška pri čitanju PDF-a: {e}")
    
    return tables


def clean_table(table: List[List[Optional[str]]]) -> List[List[str]]:
    """
    Čisti tabelu: uklanja None vrednosti i pretvara u stringove.
    """
    cleaned = []
    for row in table:
        if row is None:
            continue
        cleaned_row = []
        for cell in row:
            if cell is None:
                cleaned_row.append("")
            else:
                # Ukloni višestruke razmake i novi red
                cleaned_cell = str(cell).strip().replace("\n", " ").replace("\r", "")
                # Zamijeni višestruke razmake jednim
                while "  " in cleaned_cell:
                    cleaned_cell = cleaned_cell.replace("  ", " ")
                cleaned_row.append(cleaned_cell)
        # Preskoči potpuno prazne redove
        if any(cell.strip() for cell in cleaned_row):
            cleaned.append(cleaned_row)
    return cleaned


def save_table_to_csv(table: List[List[str]], csv_path: Path, table_num: int = 1):
    """
    Čuva tabelu u CSV fajl.
    """
    try:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for row in table:
                writer.writerow(row)
        print(f"    Sačuvana tabela {table_num}: {csv_path}")
    except Exception as e:
        print(f"    Greška pri čuvanju CSV-a {csv_path}: {e}")


def convert_pdf_to_csv(pdf_path: Path, output_folder: Path) -> int:
    """
    Konvertuje jedan PDF fajl u CSV fajlove (jedan CSV po tabeli).
    Vraća broj tabela koje je uspešno konvertovao.
    """
    print(f"\nObrađujem: {pdf_path.name}")
    
    tables = extract_tables_from_pdf(pdf_path)
    
    if not tables:
        print(f"  Nema tabela u PDF-u")
        return 0
    
    # Kreiraj output folder ako ne postoji
    output_folder.mkdir(parents=True, exist_ok=True)
    
    # Baza imena za CSV fajlove (bez .pdf ekstenzije)
    base_name = pdf_path.stem
    
    saved_count = 0
    for i, table in enumerate(tables, 1):
        cleaned_table = clean_table(table)
        
        if not cleaned_table:
            continue
        
        # Ako ima više tabela, dodaj broj u ime fajla
        if len(tables) > 1:
            csv_filename = f"{base_name}_table_{i}.csv"
        else:
            csv_filename = f"{base_name}.csv"
        
        csv_path = output_folder / csv_filename
        save_table_to_csv(cleaned_table, csv_path, i)
        saved_count += 1
    
    return saved_count


def convert_all_pdfs_to_csv(
    pdf_folder: str = DOWNLOAD_FOLDER,
    output_folder: str = "data/csv_output",
    recursive: bool = True
):
    """
    Konvertuje sve PDF fajlove iz foldera u CSV fajlove.
    
    Args:
        pdf_folder: Folder gde se nalaze PDF fajlovi
        output_folder: Folder gde će se čuvati CSV fajlovi
        recursive: Da li da traži PDF fajlove rekurzivno u podfolderima
    """
    if pdfplumber is None:
        print("ERROR: pdfplumber nije instaliran.")
        print("Pokreni: pip install pdfplumber")
        return
    
    pdf_dir = Path(pdf_folder)
    output_dir = Path(output_folder)
    
    if not pdf_dir.exists():
        print(f"ERROR: Folder {pdf_folder} ne postoji!")
        return
    
    # Pronađi sve PDF fajlove
    if recursive:
        pdf_files = list(pdf_dir.rglob("*.pdf"))
    else:
        pdf_files = list(pdf_dir.glob("*.pdf"))
    
    if not pdf_files:
        print(f"Nema PDF fajlova u {pdf_folder}")
        return
    
    print(f"Pronađeno {len(pdf_files)} PDF fajlova")
    print(f"Output folder: {output_dir}")
    print("=" * 60)
    
    total_tables = 0
    successful = 0
    failed = 0
    
    for pdf_file in pdf_files:
        try:
            # Zadrži relativnu strukturu foldera u output folderu
            relative_path = pdf_file.relative_to(pdf_dir)
            relative_output = output_dir / relative_path.parent
            
            tables_count = convert_pdf_to_csv(pdf_file, relative_output)
            if tables_count > 0:
                total_tables += tables_count
                successful += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  ERROR: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Završeno!")
    print(f"  Uspešno konvertovano: {successful} PDF fajlova")
    print(f"  Neuspešno: {failed} PDF fajlova")
    print(f"  Ukupno tabela: {total_tables}")
    print(f"  CSV fajlovi su u: {output_dir}")


def main():
    """Glavna funkcija za pokretanje konverzije."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Konvertuje PDF fajlove u CSV format"
    )
    parser.add_argument(
        "--pdf-folder",
        type=str,
        default=DOWNLOAD_FOLDER,
        help=f"Folder sa PDF fajlovima (default: {DOWNLOAD_FOLDER})"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/csv_output",
        help="Output folder za CSV fajlove (default: data/csv_output)"
    )
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Ne traži PDF fajlove rekurzivno u podfolderima"
    )
    
    args = parser.parse_args()
    
    convert_all_pdfs_to_csv(
        pdf_folder=args.pdf_folder,
        output_folder=args.output,
        recursive=not args.no_recursive
    )


if __name__ == "__main__":
    main()

