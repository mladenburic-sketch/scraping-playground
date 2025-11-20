# src/config.py

# URL stranice SA SPISKOM PDF-ova
#BASE_URL_STRANICE = "https://www.cbcg.me/slike_i_fajlovi/fajlovi/fajlovi_kontrola_banaka/pokazatelji/banke/bs/ckb"
BASE_URL_STRANICE = "https://www.cbcg.me/me/kljucne-funkcije/kontrolna-funkcija/bilansi-stanja-i-bilansi-uspjeha-banaka/"

# Folder gde čuvamo preuzete fajlove
DOWNLOAD_FOLDER = "data/bankecg_izvestaji"

# Opcioni lokalni CA bundle (putanja do .pem fajla sa sertifikatom)
# Ako fajl ne postoji, koristi se podrazumevani certifi bundle.
CUSTOM_CA_BUNDLE = "certs/custom-ca.pem"