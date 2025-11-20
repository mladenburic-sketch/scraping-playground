# src/storage.py

from pathlib import Path

import certifi
import requests

from config import CUSTOM_CA_BUNDLE


def download_file(url: str, save_path: str):
    """
    Preuzima fajl (npr. PDF, sliku) sa datog URL-a i čuva ga na 'save_path'.
    Koristi stream=True za efikasno preuzimanje.
    """
    try:
        path = Path(save_path)

        if path.exists():
            print(f"Preskačem (već postoji): {path}")
            return True

        # Kreiraj direktorijum (npr. 'data/ckb_izvestaji/') ako ne postoji
        path.parent.mkdir(parents=True, exist_ok=True)

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36 Edg/124.0.2478.51"
            )
        }

        verify_path = _resolve_verify_path()

        response = requests.get(
            url,
            headers=headers,
            stream=True,  # stream=True je važno za velike fajlove
            timeout=30,
            verify=verify_path,
        )

        response.raise_for_status()

        # Pišemo fajl u "komadima" (chunks)
        with path.open("wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        print(f"Uspješno sačuvan: {path}")
        return True

    except requests.RequestException as e:
        print(f"Greška prilikom preuzimanja {url}: {e}")
        return False
    except IOError as e:
        print(f"Greška prilikom čuvanja fajla {save_path}: {e}")
        return False


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