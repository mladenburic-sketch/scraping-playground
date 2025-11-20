# src/scraper.py

import time
from pathlib import Path
from urllib.parse import urlparse

import certifi
import requests

try:
    from playwright.sync_api import Error as PlaywrightError  # type: ignore[import]
    from playwright.sync_api import sync_playwright  # type: ignore[import]
except ImportError:  # Playwright nije instaliran u okruženju (npr. tokom lint-a)
    PlaywrightError = Exception  # type: ignore[assignment]
    sync_playwright = None  # type: ignore[assignment]

from config import CUSTOM_CA_BUNDLE


def dohvati_html(url: str) -> str | None:
    """
    Šalje GET zahtev na dati URL i vraća HTML sadržaj stranice.
    Ako server blokira zahtev (npr. 403), pokušava se Playwright fallback.
    """
    try:
        html = _fetch_with_requests(url)
        if html is not None:
            return html
    except requests.RequestException as e:
        print(f"Greška prilikom dohvatanja URL-a {url}: {e}")

    print("Pokušavam sa Playwright-om kao rezervom...")
    return _fetch_with_playwright(url)


def _fetch_with_requests(url: str) -> str | None:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36 Edg/124.0.2478.51"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Sec-Ch-Ua": '"Google Chrome";v="124", "Not:A-Brand";v="8", "Chromium";v="124"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
    }

    verify_path = _resolve_verify_path()

    session = requests.Session()
    session.headers.update(headers)

    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"

    try:
        # Prvo poseti početnu stranicu/domenu da dobiješ kolačiće ili token ako je potreban
        time.sleep(0.5)
        session.get(origin, verify=verify_path, timeout=10)
    except requests.RequestException:
        # Ignoriši grešku, pokušaj da nastaviš sa ciljnim URL-om
        pass

    # Referer može pomoći kod sajtova koji očekuju navigaciju
    session.headers["Referer"] = origin + "/"

    response = session.get(url, verify=verify_path, timeout=20)

    if response.status_code == 403:
        print("Server vratio 403 Forbidden. Prelazim na Playwright...")
        return None

    response.raise_for_status()

    print(f"Uspešno dohvaćen HTML sa {url}")
    return response.text


def _resolve_verify_path() -> str:
    custom_bundle = Path(CUSTOM_CA_BUNDLE)
    if custom_bundle.is_file():
        base_bundle = Path(certifi.where())
        combined_bundle = custom_bundle.with_name("combined-ca-bundle.pem")

        with base_bundle.open("r", encoding="utf-8") as base_file, \
                custom_bundle.open("r", encoding="utf-8") as custom_file, \
                combined_bundle.open("w", encoding="utf-8") as output_file:
            output_file.write(base_file.read())
            output_file.write("\n")
            output_file.write(custom_file.read())

        return str(combined_bundle)

    return certifi.where()


def _fetch_with_playwright(url: str) -> str | None:
    """
    Fallback koji koristi pravi browser (Chromium preko Playwright-a)
    za dohvat sadržaja. Ovo može zaobići strože zaštite.
    """
    if sync_playwright is None:
        print(
            "Playwright nije dostupan. Pokreni 'pip install -r requirements.txt' "
            "i zatim 'playwright install chromium' pa pokušaj ponovo."
        )
        return None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            page.goto(url, wait_until="networkidle", timeout=30_000)
            content = page.content()

            browser.close()
            return content

    except PlaywrightError as e:
        print(f"Playwright nije uspeo da dohvati URL {url}: {e}")
        return None