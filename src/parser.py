# src/parser.py

from bs4 import BeautifulSoup

# ... ovde može biti vaša stara funkcija parsiraj_citate ...


def parse_pdf_links(html: str) -> list[str]:
    """
    Parsira HTML iz 'directory listing-a' i vadi sve linkove
    koji se završavaju na .pdf.
    
    Vraća listu imena fajlova (npr. ['fajl1.pdf', 'fajl2.pdf'])
    """
    if not html:
        return []
    
    soup = BeautifulSoup(html, "html.parser")
    pdf_links = []
    
    # Pronalazi SVE <a> tagove (linkove) na stranici
    for tag in soup.find_all('a'):
        href = tag.get('href')  # Uzmi vrednost 'href' atributa

        # href može biti string, lista ili None (u zavisnosti od BeautifulSoup parsera)
        if isinstance(href, str):
            href_values = [href]
        elif isinstance(href, (list, tuple)):
            href_values = [v for v in href if isinstance(v, str)]
        else:
            href_values = []

        for vrednost in href_values:
            # Proverava da li se završava na .pdf
            if vrednost.lower().endswith('.pdf'):
                pdf_links.append(vrednost)
            
    return pdf_links