Place your custom CA certificate in PEM format here.

- Export the certificate chain (Base-64) from your browser or IT department.
- Save it as `custom-ca.pem` in this directory.
- The scraper will automatically detect the file and use it.

If the file is missing, the app falls back to the standard `certifi` bundle.

