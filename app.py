# app.py - Streamlit aplikacija za prikaz CSV rezultata

import streamlit as st
import pandas as pd
from pathlib import Path
from typing import List, Optional, cast
from enum import Enum
import os
import logging
from datetime import datetime

from src.config import DOWNLOAD_FOLDER

# Konfiguracija logovanja
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'app_access.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Konfiguracija stranice
st.set_page_config(
    page_title="PDF to CSV Viewer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Default folder za CSV fajlove
CSV_FOLDER = "data/csv_output/slike_i_fajlovi/fajlovi/fajlovi_kontrola_banaka/pokazatelji/banke"


def get_all_csv_files(csv_folder: str = CSV_FOLDER) -> List[Path]:
    """Pronalazi sve CSV fajlove u folderu (rekurzivno)."""
    csv_dir = Path(csv_folder)
    # Pokušaj relativno od root-a ako ne postoji
    if not csv_dir.exists():
        csv_dir = Path(".") / csv_folder
    if not csv_dir.exists():
        return []
    csv_files = list(csv_dir.rglob("*.csv"))
    return csv_files


def load_csv_file(
    csv_path: Path,
    *,
    column_names: Optional[List[str]] = None,
    skip_header: bool = False,
) -> Optional[pd.DataFrame]:
    """Učitava CSV fajl u pandas DataFrame."""
    try:
        # Pokušaj sa različitim encoding-ima
        encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252", "iso-8859-1"]

        read_kwargs = {
            "header": 0 if column_names is None else None,
            "names": column_names,
            "skiprows": 1 if skip_header and column_names is not None else 0,
        }

        for encoding in encodings:
            try:
                df = pd.read_csv(csv_path, encoding=encoding, **read_kwargs)
                
                # Preskoči fajlove koji imaju kolonu "R. br."
                if df is not None and "R. br." in df.columns:
                    return None
                
                # Ukloni sekcijske headere (Aktiva, Obaveze, Kapital) koji se pojavljuju kao redovi
                # Ovi redovi imaju istu vrednost u prvoj koloni kao header
                if df is not None and len(df.columns) > 0:
                    first_col = df.columns[0]
                    # Filtriraj redove gde je prva kolona jednaka imenu sekcije (Aktiva, Obaveze, Kapital)
                    # ali samo ako je to tačno ta vrednost (ne deo teksta)
                    section_headers = ["Aktiva", "Obaveze", "Kapital"]
                    df = df[~df[first_col].isin(section_headers)]
                    
                    # Preimenuj AKTIVA ili IZNOS kolonu u Amount pre nego što preimenujemo prvu kolonu u Pozicija
                    # (ako postoji kolona 'AKTIVA' ili 'IZNOS' koja sadrži iznose)
                    # Prioritet: IZNOS > AKTIVA (jer IZNOS je verovatnije tačan naziv)
                    if 'IZNOS' in df.columns:
                        df = df.rename(columns={'IZNOS': 'Amount'})
                        # Ukloni AKTIVA ako postoji (da ne bude duplikat)
                        if 'AKTIVA' in df.columns:
                            df = df.drop(columns=['AKTIVA'])
                    elif 'AKTIVA' in df.columns:
                        df = df.rename(columns={'AKTIVA': 'Amount'})
                    
                    df = df.rename(columns={first_col: "Pozicija"})
                    
                    # Osiguraj da nema duplikata kolona
                    df = df.loc[:, ~df.columns.duplicated()]
                
                #df = df.fillna({"Amount": 0})
                return df
            except UnicodeDecodeError:
                continue

        # Ako ništa ne radi, probaj bez encoding-a
        df = pd.read_csv(csv_path, **read_kwargs)
        
        # Preskoči fajlove koji imaju kolonu "R. br."
        if df is not None and "R. br." in df.columns:
            return None
        
        # Ukloni sekcijske headere i ovde
        if df is not None and len(df.columns) > 0:
            first_col = df.columns[0]
            section_headers = ["Aktiva", "Obaveze", "Kapital"]
            df = df[~df[first_col].isin(section_headers)]
            
            # Preimenuj AKTIVA ili IZNOS kolonu u Amount pre nego što preimenujemo prvu kolonu u Pozicija
            # Prioritet: IZNOS > AKTIVA (jer IZNOS je verovatnije tačan naziv)
            if 'IZNOS' in df.columns:
                df = df.rename(columns={'IZNOS': 'Amount'})
                # Ukloni AKTIVA ako postoji (da ne bude duplikat)
                if 'AKTIVA' in df.columns:
                    df = df.drop(columns=['AKTIVA'])
            elif 'AKTIVA' in df.columns:
                df = df.rename(columns={'AKTIVA': 'Amount'})
            
            df = df.rename(columns={first_col: "Pozicija"})
            
            # Osiguraj da nema duplikata kolona
            df = df.loc[:, ~df.columns.duplicated()]
        
        return df
    except Exception as e:
        st.error(f"Greška pri učitavanju fajla: {e}")
        return None


def format_file_size(size_bytes: int) -> str:
    """Formatira veličinu fajla u čitljiv format."""
    size = float(size_bytes)
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} TB"


def main():
    # Log pristup aplikaciji
    logger.info("=" * 50)
    logger.info(f"Aplikacija otvorena - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    st.title("📊 Analiza-bilansi banaka u Crnoj Gori")
    st.markdown("Pregled bilansa banaka u Crnoj Gori u periodu 2020-2025")

    
    class Akcija(Enum):
        PBCG = "Prva banka CG"
        CKB = "Crnogorska komercijalna banka"
        NLB = "NLB Montenegro banka"
        UCB = "Universal Capital banka"
        HB = "Hipotekarna banka"
        ADR = "Adriatic banka"
        ADK = "Addiko banka"
        LOV = "Lovćen banka"
        ERB = "Erste banka"
        ZAP = "Zapad banka"
        ZIR = "Ziraat banka"

    # Mapa banaka sa njihovim kodovima
    bank_codes = {
        Akcija.PBCG: "nik",
        Akcija.CKB: "ckb",
        Akcija.NLB: "mnb",
        Akcija.UCB: "ffb",
        Akcija.HB: "hip",
        Akcija.ADR: "azm",
        Akcija.ADK: "hyp",
        Akcija.LOV: "lov",
        Akcija.ERB: "opp",
        Akcija.ZAP: "zap",
        Akcija.ZIR: "zir",
    }

    def get_csv_folder(bank: Akcija, analysis_type: str = "bs") -> Optional[str]:
        """Generiše putanju do CSV fajlova na osnovu banke i tipa analize."""
        bank_code = bank_codes.get(bank)
        if bank_code is None:
            return None
        base_path = "data/csv_output/slike_i_fajlovi/fajlovi/fajlovi_kontrola_banaka/pokazatelji/banke"
        return f"{base_path}/{analysis_type}/{bank_code}"
    
    # Izbor banke na glavnoj strani - desno
    col1, col2 = st.columns([3, 1])
    with col2:
        bank_chooser = st.selectbox(
            "Izaberite banku:",
            options=list(Akcija),
            format_func=lambda clan: clan.value,
            key="bank_selector"
        )
    
    # Log izabranu banku
    logger.info(f"Izabrana banka: {bank_chooser.value}")

    # Koristi funkciju za generisanje putanje (default je "bs" za bilans stanja)
    csv_folder = get_csv_folder(bank_chooser, "bs")
    if csv_folder is None:
        st.error("Neispravan izbor")
        logger.warning(f"Neispravan izbor banke")
        st.stop()
    assert csv_folder is not None
    csv_folder = cast(str, csv_folder)
    
    # Debug: provjeri da li folder postoji
    test_path = Path(csv_folder)
    if not test_path.exists():
        st.error(f"❌ Folder ne postoji: {csv_folder}")
        st.error(f"Trenutna radna direktorij: {Path.cwd()}")
        # Pokušaj da pronađeš folder relativno od root-a
        alt_paths = [
            Path(".") / csv_folder,
            Path("data") / csv_folder.replace("data/", ""),
        ]
        for alt in alt_paths:
            if alt.exists():
                st.info(f"Pronađen folder na alternativnoj putanji: {alt}")
                csv_folder = str(alt)
                break
        else:
            st.stop()
    
    # Učitaj sve CSV fajlove
    csv_files = get_all_csv_files(csv_folder)
    
    if not csv_files:
        st.warning(f"Nema CSV fajlova u folderu: {csv_folder}")
        st.info(f"Folder postoji: {Path(csv_folder).exists()}")
        st.info(f"Apsolutna putanja: {Path(csv_folder).absolute()}")
        # Listaj sve CSV fajlove u parent folderu
        parent = Path(csv_folder).parent
        if parent.exists():
            all_csvs = list(parent.rglob("*.csv"))
            st.info(f"Pronađeno {len(all_csvs)} CSV fajlova u parent folderu: {parent}")
        st.stop()
    
    # Filtriraj fajlove - samo oni iz 2020+ (format mmyy* gdje yy >= 20)
    filtered_files = []
    for f in csv_files:
        file_name = f.name
        # Provjeri da li fajl ima format mmyy* (npr. 1220nik_bs.csv)
        if len(file_name) >= 4 and file_name[:4].isdigit():
            yy = int(file_name[2:4])  # Uzmi poslednje 2 cifre (godina)
            if yy >= 20:  # 2020 ili novije
                filtered_files.append(f)

    # Inicijalizuj df i df_aggregated
    df = None
    df_aggregated = pd.DataFrame(columns=['balance_date', 'Amount', 'Kategorija'])
    
    if filtered_files:
        files_list: List[pd.DataFrame] = []
        base_columns: Optional[List[str]] = None

        for f in filtered_files:
            try:
                t_df = load_csv_file(
                    f,
                    column_names=base_columns,
                    skip_header=base_columns is not None,
                )
                if t_df is None:
                    continue

                if base_columns is None:
                    base_columns = list(t_df.columns)

                file_name = os.path.basename(f)
                t_df["f_source"] = file_name
                files_list.append(t_df)
            except Exception as e:
                st.error(f"Greška pri učitavanju fajla {f}: {e}")
                continue

        if files_list:
            # Osiguraj da svi DataFrames imaju iste kolone i nema duplikata
            # Prvo, ukloni duplikate kolona iz svakog DataFrame-a
            for i, t_df in enumerate(files_list):
                files_list[i] = t_df.loc[:, ~t_df.columns.duplicated()]
            
            # Zatim, prikupi sve jedinstvene kolone iz svih DataFrames
            all_columns = set()
            for t_df in files_list:
                all_columns.update(t_df.columns)
            
            # Konvertuj u listu i sortiraj za konzistentnost
            all_columns = sorted(list(all_columns))
            
            # Osiguraj da svi DataFrames imaju iste kolone
            for i, t_df in enumerate(files_list):
                # Dodaj nedostajuće kolone sa None vrednostima
                for col in all_columns:
                    if col not in t_df.columns:
                        t_df[col] = None
                # Reorder kolone da budu konzistentne
                files_list[i] = t_df[all_columns]
            
            df = pd.concat(files_list, ignore_index=True)
        else:
            st.error("Nema CSV fajlova u folderu")
            st.stop()

    if df is not None:
        temp_date = pd.to_datetime(
            df["f_source"].str[0:4], format="%m%y", errors="coerce"
        )
        df["balance_date"] = temp_date + pd.offsets.MonthEnd(0)
        df = df[df["balance_date"].dt.year >= 2020]
        # Preimenuj AKTIVA, IZNOS ili Aktiva kolonu u Amount (iznosi su u jednoj od ovih kolona)
        # Proveri sve varijante: 'AKTIVA' (sve veliko), 'Aktiva' (prvo veliko), 'IZNOS'
        if 'Amount' not in df.columns:
            if 'AKTIVA' in df.columns:
                df = df.rename(columns={'AKTIVA': 'Amount'})
            elif 'IZNOS' in df.columns:
                df = df.rename(columns={'IZNOS': 'Amount'})
            elif 'Aktiva' in df.columns:
                df = df.rename(columns={'Aktiva': 'Amount'})
        df = df.fillna({'Amount': 0})
        #st.dataframe(df)

    class Kategorija(Enum):
        AKTIVA = "Aktiva"
        OBAVEZE = "Obaveze"
        KAPITAL = "Kapital"

    cat_mapper = {
        Kategorija.AKTIVA: "16. UKUPNA SREDSTVA:",
        Kategorija.OBAVEZE: "28. UKUPNE OBAVEZE:",
        Kategorija.KAPITAL: "35. UKUPAN KAPITAL: (29. do 34.)",
    }

    # Korak 1: Učitaj sve kategorije umesto samo jedne
    if df is not None and "Pozicija" in df.columns:
        # Osiguraj da Amount kolona postoji (ako nije već preimenovana)
        if 'Amount' not in df.columns:
            # Pokušaj da pronađeš kolonu sa iznosima
            if 'IZNOS' in df.columns:
                df['Amount'] = df['IZNOS']
            elif 'AKTIVA' in df.columns:
                df['Amount'] = df['AKTIVA']
            elif 'Aktiva' in df.columns:
                df['Amount'] = df['Aktiva']
            else:
                st.warning(f"Amount kolona ne postoji. Dostupne kolone: {df.columns.tolist()}")
        
        # Korak 2: Učitaj sve kategorije i dodaj kolonu 'Kategorija'
        all_categories_data = []
        
        for kategorija_enum, pozicija_value in cat_mapper.items():
            df_filtered = df[df["Pozicija"] == pozicija_value].copy()
            
            if len(df_filtered) > 0 and 'Amount' in df_filtered.columns:
                # Konvertuj Amount u numerički tip pre agregacije
                if df_filtered['Amount'].dtype == 'object':
                    df_filtered['Amount'] = df_filtered['Amount'].astype(str).str.replace(',', '').astype(float)
                else:
                    df_filtered['Amount'] = pd.to_numeric(df_filtered['Amount'], errors='coerce').fillna(0)
                
                # Agregiraj po datumu
                df_agg = df_filtered.groupby('balance_date')['Amount'].sum().reset_index()
                # Dodaj kolonu sa imenom kategorije
                df_agg['Kategorija'] = kategorija_enum.value
                all_categories_data.append(df_agg)
        
        # Korak 3: Kombinuj sve kategorije u jedan DataFrame
        if all_categories_data:
            df_aggregated = pd.concat(all_categories_data, ignore_index=True)
        else:
            st.warning("Nema podataka za prikaz grafikona.")
            df_aggregated = pd.DataFrame(columns=['balance_date', 'Amount', 'Kategorija'])
    else:
        st.warning("Nema podataka za prikaz grafikona.")
        df_aggregated = pd.DataFrame(columns=['balance_date', 'Amount', 'Kategorija'])

    # Lista fajlova za izbor
    #st.subheader("📁 Dostupni fajlovi")
    
    # Sortiraj fajlove po imenu
    filtered_files_sorted = sorted(filtered_files, key=lambda x: x.name)
    
    # Kreiraj listu opcija za selectbox
    file_options = [
        f"{f.relative_to(Path(csv_folder))}" for f in filtered_files_sorted
    ]
    
    #selected_file_idx = st.selectbox(
    #    "Izaberi fajl",
    #    range(len(file_options)),
    #    format_func=lambda x: file_options[x],
    #    help="Izaberi CSV fajl za prikaz"
    #)

    # Kreiraj tabove
    tab1, tab2 = st.tabs([
        "📊 Analiza bilansa stanja",
        "📈 Analiza bilansa uspjeha"
    ])
    
    # Prvi tab - Analiza bilansa stanja
    with tab1:
        if df_aggregated is not None and len(df_aggregated) > 0:
            only_year_end = st.checkbox(
                "Prikaži samo stanje na kraju godine",
                value=True,
                help="Ako je uključeno, prikazuju se samo podaci za decembar (kraj svake godine)."
            )

            df_chart_source = df_aggregated.copy()
            if only_year_end:
                df_chart_source = df_chart_source[df_chart_source['balance_date'].dt.month == 12]

            if df_chart_source.empty:
                st.warning("Nema podataka za prikaz sa trenutno odabranim filterom (kraj godine).")
            else:
                st.subheader(f"Pregled svih kategorija u periodu: {df_chart_source['balance_date'].min().strftime('%d.%m.%Y')} - {df_chart_source['balance_date'].max().strftime('%d.%m.%Y')}")

                # Dodaj kontrolu za izbor kategorija
                available_categories = sorted(df_chart_source['Kategorija'].unique().tolist())
                selected_categories = st.multiselect(
                    "Izaberi kategorije za prikaz",
                    options=available_categories,
                    default=available_categories,  # Podrazumevano sve kategorije
                    help="Možeš ukloniti ili dodati kategorije na grafikonu"
                )
                
                #st.write("### Vertikalni Bar Chart (Datum na X osi)")
                
                # Filtriraj df_chart_source prema izabranim kategorijama
                if selected_categories:
                    df_chart = df_chart_source[df_chart_source['Kategorija'].isin(selected_categories)].copy()
                else:
                    st.warning("Nijedna kategorija nije izabrana. Prikazujem sve kategorije.")
                    df_chart = df_chart_source.copy()
                
                # Konvertuj Amount u numerički tip (ukloni zareze i druge karaktere ako postoje)
                # Napomena: Amount je već u hiljadama u CSV-u
                if df_chart['Amount'].dtype == 'object':
                    # Ukloni zareze i konvertuj u float
                    df_chart['Amount'] = df_chart['Amount'].astype(str).str.replace(',', '').astype(float)
                else:
                    # Osiguraj da je numerički tip
                    df_chart['Amount'] = pd.to_numeric(df_chart['Amount'], errors='coerce').fillna(0)
                
                # Amount je već u hiljadama u CSV-u, samo ga konvertuj u ceo broj
                df_chart['Amount_in_thousands'] = df_chart['Amount'].astype(int)
                
                # Osiguraj da balance_date je datetime tip
                if df_chart['balance_date'].dtype != 'datetime64[ns]':
                    df_chart['balance_date'] = pd.to_datetime(df_chart['balance_date'])
                
                df_chart = df_chart.sort_values(['balance_date', 'Kategorija']).reset_index(drop=True)
                
                # Konvertuj Amount u numerički tip (ukloni zareze i druge karaktere ako postoje)
                # Napomena: Amount je već u hiljadama u CSV-u
                if df_chart['Amount'].dtype == 'object':
                    # Ukloni zareze i konvertuj u float
                    df_chart['Amount'] = df_chart['Amount'].astype(str).str.replace(',', '').astype(float)
                else:
                    # Osiguraj da je numerički tip
                    df_chart['Amount'] = pd.to_numeric(df_chart['Amount'], errors='coerce').fillna(0)
                
                # Amount je već u hiljadama u CSV-u, samo ga konvertuj u ceo broj
                df_chart['Amount_in_thousands'] = df_chart['Amount'].astype(int)
                
                # Osiguraj da balance_date je datetime tip
                if df_chart['balance_date'].dtype != 'datetime64[ns]':
                    df_chart['balance_date'] = pd.to_datetime(df_chart['balance_date'])
                
                df_chart = df_chart.sort_values(['balance_date', 'Kategorija']).reset_index(drop=True)
                
                # Korak 4: Koristi Plotly za grupisanje barova (najbolje rešenje za grouped bars)
                try:
                    import plotly.graph_objects as go
                    import plotly.express as px
                    
                    # Sortiraj datume i kreiraj listu sortiranih datuma za x-os
                    unique_dates = sorted(df_chart['balance_date'].unique())
                    date_str_list = [pd.Timestamp(d).strftime('%d.%m.%Y') for d in unique_dates]
                    
                    # Konvertuj datum u string za bolje prikazivanje
                    df_chart['datum_str'] = df_chart['balance_date'].dt.strftime('%d.%m.%Y')
                    
                    # Kreiraj grouped bar chart sa Plotly
                    fig = go.Figure()
                    
                    # Sortiraj kategorije u željenom redosledu (samo one koje su izabrane)
                    category_order = ['Aktiva', 'Obaveze', 'Kapital',]
                    colors = {'Aktiva': '#1f77b4', 'Obaveze': '#ff7f0e', 'Kapital': '#2ca02c', }
                    
                    # Filtriraj category_order da uključi samo izabrane kategorije
                    filtered_category_order = [cat for cat in category_order if cat in selected_categories] if selected_categories else category_order
                    
                    for kategorija in filtered_category_order:
                        df_cat = df_chart[df_chart['Kategorija'] == kategorija].sort_values('balance_date')
                        if len(df_cat) > 0:
                            # Osiguraj da su vrednosti sortirane po datumu i mapirane na sortirane datume
                            y_values = []
                            for date in unique_dates:
                                matching_row = df_cat[df_cat['balance_date'] == date]
                                if len(matching_row) > 0:
                                    y_values.append(matching_row.iloc[0]['Amount_in_thousands'])
                                else:
                                    y_values.append(None)
                            
                            fig.add_trace(go.Bar(
                                x=date_str_list,
                                y=y_values,
                                name=kategorija,
                                marker_color=colors.get(kategorija, '#808080')  # Siva ako kategorija nema definisanu boju
                            ))
                    
                    fig.update_layout(
                        title='Pregled kategorija po datumu',
                        xaxis_title='Datum',
                        yaxis_title='Iznos (u hiljadama)',
                        barmode='group',  # Ovo je ključno - grupiše barove jedan pored drugog
                        xaxis=dict(tickangle=-45, categoryorder='array', categoryarray=date_str_list),
                        height=500,
                        showlegend=True
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                except ImportError:
                    st.warning("Plotly nije instaliran. Koristim st.bar_chart kao fallback.")
                    # Fallback: st.bar_chart sa pivot tabelom
                    pivot_df = df_chart.pivot_table(
                        index='balance_date',
                        columns='Kategorija',
                        values='Amount_in_thousands',
                        aggfunc='sum'
                    ).fillna(0)
                    pivot_df = pivot_df.sort_index()
                    category_order = ['Aktiva', 'Obaveze', 'Kapital']
                    existing_categories = [cat for cat in category_order if cat in pivot_df.columns]
                    if existing_categories:
                        pivot_df = pivot_df[existing_categories]
                    st.bar_chart(pivot_df, height=400)

                st.divider()
            
            # Drugi graf - sa drugim kategorijama (analogno prvom)
            if df is not None and "Pozicija" in df.columns and len(df_aggregated) > 0:
                class Kategorija_2(Enum):
                    KREDITI_KLIJENATA = "Krediti klijenata"
                    HoV = "Hartije od vrijednosti"
                    DEPOZITI_KLIJENATA = "Depoziti klijenata"

                cat_mapper_2 = {
                    Kategorija_2.KREDITI_KLIJENATA: ["2.b. Krediti i potrazivanja od klijenata","2.a. Krediti i potrazivanja od banaka"],
                    Kategorija_2.HoV: ["2.c. Hartije od vrijednosti","3.c. Hartije od vrijednosti","4.c. Hartije od vrijednosti"],
                    Kategorija_2.DEPOZITI_KLIJENATA: "17.b. Depoziti klijenata",
                }
                
                # Učitaj sve kategorije za drugi graf (analogno prvom)
                all_categories_data_2 = []
                
                for kategorija_enum_2, pozicije_values in cat_mapper_2.items():
                    for pozicija_value_2 in (pozicije_values if isinstance(pozicije_values, list) else [pozicije_values]):
                        df_filtered_2 = df[df["Pozicija"] == pozicija_value_2].copy()
                        
                        if len(df_filtered_2) > 0 and 'Amount' in df_filtered_2.columns:
                            # Konvertuj Amount u numerički tip pre agregacije
                            if df_filtered_2['Amount'].dtype == 'object':
                                df_filtered_2['Amount'] = df_filtered_2['Amount'].astype(str).str.replace(',', '').astype(float)
                            else:
                                df_filtered_2['Amount'] = pd.to_numeric(df_filtered_2['Amount'], errors='coerce').fillna(0)
                            
                            # Agregiraj po datumu
                            df_agg_2 = df_filtered_2.groupby('balance_date')['Amount'].sum().reset_index()
                            # Dodaj kolonu sa imenom kategorije (koristi Enum vrednost)
                            df_agg_2['Kategorija'] = kategorija_enum_2.value
                            all_categories_data_2.append(df_agg_2)
                
                # Kombinuj sve kategorije u jedan DataFrame
                if all_categories_data_2:
                    df_aggregated_2 = pd.concat(all_categories_data_2, ignore_index=True)

                    df_chart_2_source = df_aggregated_2.copy()
                    if only_year_end:
                        df_chart_2_source = df_chart_2_source[df_chart_2_source['balance_date'].dt.month == 12]

                    if df_chart_2_source.empty:
                        st.warning("Nema podataka za prikaz kredita i depozita sa trenutno odabranim filterom (kraj godine).")
                    else:
                        ratio_source = df_chart_2_source.copy()
                        if ratio_source['Amount'].dtype == 'object':
                            ratio_source['Amount'] = ratio_source['Amount'].astype(str).str.replace(',', '').astype(float)
                        else:
                            ratio_source['Amount'] = pd.to_numeric(ratio_source['Amount'], errors='coerce').fillna(0)
                        ratio_source['Amount_in_thousands'] = ratio_source['Amount'].astype(int)
                        st.subheader(f"Pregled kredita i depozita u periodu: {df_chart_2_source['balance_date'].min().strftime('%d.%m.%Y')} - {df_chart_2_source['balance_date'].max().strftime('%d.%m.%Y')}")
                    
                    # Dodaj kontrolu za izbor kategorija (analogno prvom)
                    available_categories_2 = sorted(df_chart_2_source['Kategorija'].unique().tolist())
                    selected_categories_2 = st.multiselect(
                        "Izaberi kategorije za pregled kredita i depozita",
                        options=available_categories_2,
                        default=available_categories_2,  # Podrazumevano sve kategorije
                        help="Možeš ukloniti ili dodati kategorije na grafikonu"
                    )
                    
                    #st.write("### Vertikalni Bar Chart (Datum na X osi)")
                    
                    # Filtriraj df_aggregated_2 prema izabranim kategorijama
                    if selected_categories_2:
                        df_chart_2 = df_chart_2_source[df_chart_2_source['Kategorija'].isin(selected_categories_2)].copy()
                    else:
                        st.warning("Nijedna kategorija nije izabrana. Prikazujem sve kategorije.")
                        df_chart_2 = df_chart_2_source.copy()
                    
                    # Konvertuj Amount u numerički tip (ukloni zareze i druge karaktere ako postoje)
                    # Napomena: Amount je već u hiljadama u CSV-u
                    if df_chart_2['Amount'].dtype == 'object':
                        df_chart_2['Amount'] = df_chart_2['Amount'].astype(str).str.replace(',', '').astype(float)
                    else:
                        df_chart_2['Amount'] = pd.to_numeric(df_chart_2['Amount'], errors='coerce').fillna(0)
                    
                    # Amount je već u hiljadama u CSV-u, samo ga konvertuj u ceo broj
                    df_chart_2['Amount_in_thousands'] = df_chart_2['Amount'].astype(int)
                    
                    # Osiguraj da balance_date je datetime tip
                    if df_chart_2['balance_date'].dtype != 'datetime64[ns]':
                        df_chart_2['balance_date'] = pd.to_datetime(df_chart_2['balance_date'])
                    
                    df_chart_2 = df_chart_2.sort_values(['balance_date', 'Kategorija']).reset_index(drop=True)
                    
                    # Koristi Plotly za grupisanje barova (analogno prvom)
                    try:
                        import plotly.graph_objects as go
                        import plotly.express as px
                        
                        # Sortiraj datume i kreiraj listu sortiranih datuma za x-os
                        unique_dates_2 = sorted(df_chart_2['balance_date'].unique())
                        date_str_list_2 = [pd.Timestamp(d).strftime('%d.%m.%Y') for d in unique_dates_2]
                        
                        # Konvertuj datum u string za bolje prikazivanje
                        df_chart_2['datum_str'] = df_chart_2['balance_date'].dt.strftime('%d.%m.%Y')
                        
                        # Kreiraj grouped bar chart sa Plotly
                        fig2 = go.Figure()
                        
                        # Sortiraj kategorije u željenom redosledu (samo one koje su izabrane)
                        category_order_2 = ['Krediti klijenata','Hartije od vrijednosti', 'Depoziti klijenata']
                        colors_2 = {'Krediti klijenata': '#1f77b4', 'Hartije od vrijednosti': '#ff7f0e', 'Depoziti klijenata': '#2ca02c'}
                        
                        # Filtriraj category_order_2 da uključi samo izabrane kategorije
                        filtered_category_order_2 = [cat for cat in category_order_2 if cat in selected_categories_2] if selected_categories_2 else category_order_2
                        
                        for kategorija in filtered_category_order_2:
                            df_cat_2 = df_chart_2[df_chart_2['Kategorija'] == kategorija].sort_values('balance_date')
                            if len(df_cat_2) > 0:
                                # Osiguraj da su vrednosti sortirane po datumu i mapirane na sortirane datume
                                y_values_2 = []
                                for date in unique_dates_2:
                                    matching_row = df_cat_2[df_cat_2['balance_date'] == date]
                                    if len(matching_row) > 0:
                                        y_values_2.append(matching_row.iloc[0]['Amount_in_thousands'])
                                    else:
                                        y_values_2.append(None)
                                
                                fig2.add_trace(go.Bar(
                                    x=date_str_list_2,
                                    y=y_values_2,
                                    name=kategorija,
                                    marker_color=colors_2.get(kategorija, '#808080'),  # Siva ako kategorija nema definisanu boju
                                    offsetgroup=kategorija,
                                    legendgroup=kategorija
                                ))
                        
                        fig2.update_layout(
                            title='Pregled kredita, HoV i depozita po datumu',
                            xaxis_title='Datum',
                            yaxis_title='Iznos (u hiljadama)',
                            barmode='group',  # Ovo je ključno - grupiše barove jedan pored drugog
                            xaxis=dict(tickangle=-45, categoryorder='array', categoryarray=date_str_list_2),
                            height=500,
                            showlegend=True
                        )
                        
                        st.plotly_chart(fig2, use_container_width=True)
                        
                    except ImportError:
                        st.warning("Plotly nije instaliran. Koristim st.bar_chart kao fallback.")
                        # Fallback: st.bar_chart sa pivot tabelom
                        pivot_df_2 = df_chart_2.pivot_table(
                            index='balance_date',
                            columns='Kategorija',
                            values='Amount_in_thousands',
                            aggfunc='sum'
                        ).fillna(0)
                        pivot_df_2 = pivot_df_2.sort_index()
                        category_order_2 = ['Krediti klijenata','Hartije od vrijednosti', 'Depoziti klijenata']
                        existing_categories_2 = [cat for cat in category_order_2 if cat in pivot_df_2.columns]
                        if existing_categories_2:
                            pivot_df_2 = pivot_df_2[existing_categories_2]
                        st.bar_chart(pivot_df_2, height=400)

                    # Dodatni graf: odnos kredita i depozita (K/D ratio) baziran na kompletnim podacima
                    ratio_pivot = ratio_source.pivot_table(
                        index='balance_date',
                        columns='Kategorija',
                        values='Amount_in_thousands',
                        aggfunc='sum'
                    ).fillna(0)
                    ratio_pivot = ratio_pivot.sort_index()

                    if {'Krediti klijenata', 'Depoziti klijenata'}.issubset(ratio_pivot.columns):
                        ratio_pivot['K/D odnos'] = ratio_pivot['Krediti klijenata'] / ratio_pivot['Depoziti klijenata'].replace({0: pd.NA})
                        ratio_pivot = ratio_pivot.dropna(subset=['K/D odnos'])

                        if not ratio_pivot.empty:
                            st.write("### Odnos kredita i depozita (K/D)")
                            try:
                                import plotly.graph_objects as go
                                # Sortiraj datume i kreiraj listu sortiranih datuma za x-os
                                ratio_pivot = ratio_pivot.sort_index()
                                ratio_dates = sorted(ratio_pivot.index)
                                ratio_date_str_list = [pd.Timestamp(d).strftime('%d.%m.%Y') for d in ratio_dates]
                                
                                # Mapiraj vrednosti na sortirane datume
                                ratio_y_values = []
                                for date in ratio_dates:
                                    if date in ratio_pivot.index:
                                        ratio_y_values.append((ratio_pivot.loc[date, 'K/D odnos'] * 100).round(2))
                                    else:
                                        ratio_y_values.append(None)

                                fig_ratio = go.Figure(
                                    data=[
                                        go.Bar(
                                            x=ratio_date_str_list,
                                            y=ratio_y_values,
                                            text=[f"{v}%" if v is not None else "" for v in ratio_y_values],
                                            textposition='outside',
                                            width=0.6
                                        )
                                    ]
                                )

                                fig_ratio.update_layout(
                                    title='Odnos kredita i depozita (K/D) u %',
                                    xaxis_title='Datum',
                                    yaxis_title='K/D (%)',
                                    yaxis=dict(ticksuffix='%', tickformat='.2f'),
                                    xaxis=dict(categoryorder='array', categoryarray=ratio_date_str_list),
                                    height=520,
                                    bargap=0.3,
                                    margin=dict(t=80, b=60)
                                )
                                fig_ratio.update_traces(
                                    hovertemplate='Datum: %{x}<br>K/D: %{y:.2f}%<extra></extra>'
                                )

                                st.plotly_chart(fig_ratio, use_container_width=True)
                            except ImportError:
                                st.bar_chart((ratio_pivot['K/D odnos'] * 100).round(2), height=300)
                        else:
                            st.info("Nije moguće izračunati odnos K/D (nedostaju podaci ili su depoziti 0).")
                    else:
                        st.info("Za prikaz odnosa K/D neophodno je imati i kredite i depozite u podacima.")
            else:
                st.warning("Nema podataka za prikaz drugog grafikona.")
    
    # Drugi tab - Analiza bilansa uspjeha
    with tab2:
        st.subheader("📈 Analiza bilansa uspjeha")
        
        # Koristi "bu" tip analize umjesto "bs"
        csv_folder_bu = get_csv_folder(bank_chooser, "bu")
        
        if csv_folder_bu is None:
            st.error("Neispravan izbor banke")
            logger.warning(f"Neispravan izbor banke za bilans uspjeha")
            st.stop()
        
        # Osiguraj da csv_folder_bu nije None
        csv_folder_bu = cast(str, csv_folder_bu)
        
        # Debug: provjeri da li folder postoji
        test_path_bu = Path(csv_folder_bu)
        if not test_path_bu.exists():
            st.error(f"❌ Folder ne postoji: {csv_folder_bu}")
            st.error(f"Trenutna radna direktorij: {Path.cwd()}")
            # Pokušaj da pronađeš folder relativno od root-a
            alt_paths = [
                Path(".") / csv_folder_bu,
                Path("data") / csv_folder_bu.replace("data/", ""),
            ]
            for alt in alt_paths:
                if alt.exists():
                    st.info(f"Pronađen folder na alternativnoj putanji: {alt}")
                    csv_folder_bu = str(alt)
                    break
            else:
                st.stop()
        
        # Učitaj sve CSV fajlove za bilans uspjeha
        csv_files_bu = get_all_csv_files(csv_folder_bu)
        
        if not csv_files_bu:
            st.warning(f"Nema CSV fajlova u folderu: {csv_folder_bu}")
            st.info(f"Folder postoji: {Path(csv_folder_bu).exists()}")
            st.info(f"Apsolutna putanja: {Path(csv_folder_bu).absolute()}")
            parent = Path(csv_folder_bu).parent
            if parent.exists():
                all_csvs = list(parent.rglob("*.csv"))
                st.info(f"Pronađeno {len(all_csvs)} CSV fajlova u parent folderu: {parent}")
            st.stop()
        
        # Filtriraj fajlove - samo oni iz 2020+ (format mmyy* gdje yy >= 20)
        filtered_files_bu = []
        for f in csv_files_bu:
            file_name = f.name
            if len(file_name) >= 4 and file_name[:4].isdigit():
                yy = int(file_name[2:4])
                if yy >= 20:
                    filtered_files_bu.append(f)
        
        if not filtered_files_bu:
            st.warning(f"Nema CSV fajlova za bilans uspjeha iz 2020+ u folderu: {csv_folder_bu}")
            df_bu = pd.DataFrame(columns=['balance_date', 'Amount', 'Pozicija', 'f_source']) # Prazan DataFrame
        else:
            df_bu = None
            if filtered_files_bu:
                files_list_bu: List[pd.DataFrame] = []
                base_columns_bu: Optional[List[str]] = None

                for f_bu in filtered_files_bu:
                    try:
                        t_df_bu = load_csv_file(
                            f_bu,
                            column_names=base_columns_bu,
                            skip_header=base_columns_bu is not None,
                        )
                        if t_df_bu is None:
                            continue

                        if base_columns_bu is None:
                            base_columns_bu = list(t_df_bu.columns)

                        file_name_bu = os.path.basename(f_bu)
                        t_df_bu["f_source"] = file_name_bu
                        files_list_bu.append(t_df_bu)
                    except Exception as e:
                        st.error(f"Greška pri učitavanju fajla {f_bu}: {e}")
                        continue

                if files_list_bu:
                    # Osiguraj da svi DataFrames imaju iste kolone i nema duplikata
                    for i, t_df_bu in enumerate(files_list_bu):
                        files_list_bu[i] = t_df_bu.loc[:, ~t_df_bu.columns.duplicated()]
                    
                    all_columns_bu = set()
                    for t_df_bu in files_list_bu:
                        all_columns_bu.update(t_df_bu.columns)
                    
                    all_columns_bu = sorted(list(all_columns_bu))
                    
                    for i, t_df_bu in enumerate(files_list_bu):
                        for col in all_columns_bu:
                            if col not in t_df_bu.columns:
                                t_df_bu[col] = None
                        files_list_bu[i] = t_df_bu[all_columns_bu]
                    
                    df_bu = pd.concat(files_list_bu, ignore_index=True)
                else:
                    st.warning("Nema CSV fajlova za bilans uspjeha u folderu")
                    df_bu = pd.DataFrame(columns=['balance_date', 'Amount', 'Pozicija', 'f_source']) # Prazan DataFrame
            else:
                df_bu = pd.DataFrame(columns=['balance_date', 'Amount', 'Pozicija', 'f_source']) # Prazan DataFrame

        if df_bu is not None:
            temp_date_bu = pd.to_datetime(
                df_bu["f_source"].str[0:4], format="%m%y", errors="coerce"
            )
            df_bu["balance_date"] = temp_date_bu + pd.offsets.MonthEnd(0)
            df_bu = df_bu[df_bu["balance_date"].dt.year >= 2020]
            
            # Preimenuj IZNOS ili AKTIVA kolonu u Amount
            if 'Amount' not in df_bu.columns:
                if 'IZNOS' in df_bu.columns:
                    df_bu = df_bu.rename(columns={'IZNOS': 'Amount'})
                elif 'AKTIVA' in df_bu.columns:
                    df_bu = df_bu.rename(columns={'AKTIVA': 'Amount'})
                elif 'Aktiva' in df_bu.columns:
                    df_bu = df_bu.rename(columns={'Aktiva': 'Amount'})
            df_bu = df_bu.fillna({'Amount': 0})

        # Definiši kategorije za bilans uspjeha
        class KategorijaBU(Enum):
            PRIHODI = "Prihodi"
            RASHODI = "Rashodi"

        # Mapa kategorija - korisnik će dodati pozicije iz CSV-ova
        cat_mapper_bu = {
            KategorijaBU.PRIHODI: [
                "1. Prihodi od kamata i slicni prihodi","2. Prihodi od kamata na obezvrijedene plasmane","4. Prihodi od naknada i provizija",
                "6. Neto dobitak / gubitak usled prestanka priznavanja finansijske instrumenata koji se ne vrednuju po fer vrijednosti kroz bilans uspjeha",
                "7. Neto dobitak/gubitak po osnovu finansijskih instrumenata koji se drze radi trgovanja",
                "8. Neto dobitak / gubitak od finansijskih instrumenata iskazanih po fer vrijednosti kroz bilans uspjeha, a koji se ne drze radi trgovanja",
                "9. Promjena fer vrijednosti u racunovodstvu zastite od rizika (hedzing)",
                "10. Neto gubici/dobici od kursnih razlika",
                "11. Neto dobitak/gubitak po osnovu prestanka priznavanja ostale imovine",
                "12. Ostali prihodi",
            ],
            KategorijaBU.RASHODI: [
                "3. Rashodi od kamata i slicni rashodi",
                "5. Rashodi naknada i provizija",
                "6. Neto dobitak / gubitak usled prestanka priznavanja finansijskih instrumenata koji se ne vrednuju po fer vrijednosti kroz bilans uspjeha",
                "7. Neto dobitak/gubitak po osnovu finansijskih instrumenata koji se drze radi trgovanja",
                "8. Neto dobitak / gubitak od finansijskih instrumenata iskazanih po fer vrijednosti kroz bilans uspjeha, a koji se ne drze radi trgovanja",
                "9. Promjena fer vrijednosti u racunovodstvu zastite od rizika (hedzing)",
                "10. Neto gubici/dobici od kursnih razlika",
                "11. Neto dobitak/gubitak po osnovu prestanka priznavanja ostale imovine",
                "13. Troskovi zaposlenih",
                "14. Troskovi amortizacije",
                "15. Opsti i administrativni troskovi",
                "16. Neto dobici/gubici po osnovu modifikacije i reklasifikacije finansijskih instrumenata",
                "17. Neto prihodi/rashodi po osnovu obezvredjenja finansijskih instrumenata koji se ne vrednuju po fer vrednosti kroz bilans uspjeha",
                "18. Troskovi rezervisanja",
                "19. Ostali rashodi",
            ],
        }

        if df_bu is not None and "Pozicija" in df_bu.columns:
            all_categories_data_bu = []
            
            # Pronađi pozicije koje su u obje kategorije (za filtriranje)
            prihodi_pozicije = set(cat_mapper_bu[KategorijaBU.PRIHODI])
            rashodi_pozicije = set(cat_mapper_bu[KategorijaBU.RASHODI])
            zajednicke_pozicije = prihodi_pozicije.intersection(rashodi_pozicije)
            
            for kategorija_enum_bu, pozicije_values_bu in cat_mapper_bu.items():
                for pozicija_value_bu in pozicije_values_bu:
                    df_filtered_bu = df_bu[df_bu["Pozicija"] == pozicija_value_bu].copy()
                    
                    # Debug: provjeri da li se pozicija poklapa
                    if len(df_filtered_bu) == 0:
                        # Pokušaj da pronađeš slične pozicije (case-insensitive, sa trim)
                        unique_pozicije = df_bu["Pozicija"].unique() if "Pozicija" in df_bu.columns else []
                        similar = [p for p in unique_pozicije if str(p).strip().lower() == pozicija_value_bu.strip().lower()]
                        if similar:
                            df_filtered_bu = df_bu[df_bu["Pozicija"] == similar[0]].copy()
                            logger.info(f"Pronađena slična pozicija: '{similar[0]}' umjesto '{pozicija_value_bu}'")
                    
                    if len(df_filtered_bu) > 0 and 'Amount' in df_filtered_bu.columns:
                        # Konvertuj Amount u numerički tip pre agregacije
                        if df_filtered_bu['Amount'].dtype == 'object':
                            df_filtered_bu['Amount'] = df_filtered_bu['Amount'].astype(str).str.replace(',', '').astype(float)
                        else:
                            df_filtered_bu['Amount'] = pd.to_numeric(df_filtered_bu['Amount'], errors='coerce').fillna(0)
                        
                        # Filtriraj vrednosti SAMO ako je pozicija u obje kategorije:
                        # - Za PRIHODE: uzmi samo pozitivne vrednosti (Amount > 0)
                        # - Za RASHODE: uzmi samo negativne vrednosti (Amount < 0)
                        if pozicija_value_bu in zajednicke_pozicije:
                            if kategorija_enum_bu == KategorijaBU.PRIHODI:
                                df_filtered_bu = df_filtered_bu[df_filtered_bu['Amount'] > 0].copy()
                            elif kategorija_enum_bu == KategorijaBU.RASHODI:
                                df_filtered_bu = df_filtered_bu[df_filtered_bu['Amount'] < 0].copy()
                                # Konvertuj negativne vrednosti u pozitivne za prikaz (uzmi apsolutnu vrednost)
                                df_filtered_bu['Amount'] = df_filtered_bu['Amount'].abs()
                        
                        # Agregiraj po datumu
                        df_agg_bu = df_filtered_bu.groupby('balance_date')['Amount'].sum().reset_index()
                        # Dodaj kolonu sa imenom kategorije
                        df_agg_bu['Kategorija'] = kategorija_enum_bu.value
                        all_categories_data_bu.append(df_agg_bu)
            
            # Kombinuj sve kategorije u jedan DataFrame
            if all_categories_data_bu:
                df_aggregated_bu = pd.concat(all_categories_data_bu, ignore_index=True)
                # Agregiraj ponovo po balance_date i Kategorija da bi se sumirale sve pozicije za isti datum i kategoriju
                df_aggregated_bu = df_aggregated_bu.groupby(['balance_date', 'Kategorija'])['Amount'].sum().reset_index()
            else:
                st.warning("Nema podataka za prikaz grafikona (dodaj pozicije u cat_mapper_bu).")
                df_aggregated_bu = pd.DataFrame(columns=['balance_date', 'Amount', 'Kategorija'])
        else:
            st.warning("Nema podataka za prikaz grafikona.")
            df_aggregated_bu = pd.DataFrame(columns=['balance_date', 'Amount', 'Kategorija'])

        # Checkbox za "samo kraj godine" - zajednički za oba grafa
        only_year_end_bu = st.checkbox(
            "Prikaži samo stanje na kraju godine",
            value=True,
            key="year_end_bu",
            help="Ako je uključeno, prikazuju se samo podaci za decembar (kraj svake godine)."
        )

        # Prvi graf - Prihodi i Rashodi
        if df_aggregated_bu is not None and len(df_aggregated_bu) > 0:
            df_chart_source_bu = df_aggregated_bu.copy()
            if only_year_end_bu:
                df_chart_source_bu = df_chart_source_bu[df_chart_source_bu['balance_date'].dt.month == 12]

            if df_chart_source_bu.empty:
                st.warning("Nema podataka za prikaz sa trenutno odabranim filterom (kraj godine).")
            else:
                st.subheader(f"Pregled prihoda i rashoda u periodu: {df_chart_source_bu['balance_date'].min().strftime('%d.%m.%Y')} - {df_chart_source_bu['balance_date'].max().strftime('%d.%m.%Y')}")

                # Dodaj kontrolu za izbor kategorija
                available_categories_bu = sorted(df_chart_source_bu['Kategorija'].unique().tolist())
                selected_categories_bu = st.multiselect(
                    "Izaberi kategorije za prikaz",
                    options=available_categories_bu,
                    default=available_categories_bu,
                    key="categories_bu",
                    help="Možeš ukloniti ili dodati kategorije na grafikonu"
                )
                
                # Filtriraj df_chart_source prema izabranim kategorijama
                if selected_categories_bu:
                    df_chart_bu = df_chart_source_bu[df_chart_source_bu['Kategorija'].isin(selected_categories_bu)].copy()
                else:
                    st.warning("Nijedna kategorija nije izabrana. Prikazujem sve kategorije.")
                    df_chart_bu = df_chart_source_bu.copy()
                
                # Konvertuj Amount u numerički tip
                if df_chart_bu['Amount'].dtype == 'object':
                    df_chart_bu['Amount'] = df_chart_bu['Amount'].astype(str).str.replace(',', '').astype(float)
                else:
                    df_chart_bu['Amount'] = pd.to_numeric(df_chart_bu['Amount'], errors='coerce').fillna(0)
                
                # Amount je već u hiljadama u CSV-u, samo ga konvertuj u ceo broj
                df_chart_bu['Amount_in_thousands'] = df_chart_bu['Amount'].astype(int)
                
                # Osiguraj da balance_date je datetime tip
                if df_chart_bu['balance_date'].dtype != 'datetime64[ns]':
                    df_chart_bu['balance_date'] = pd.to_datetime(df_chart_bu['balance_date'])
                
                df_chart_bu = df_chart_bu.sort_values(['balance_date', 'Kategorija']).reset_index(drop=True)
                
                # Kreiraj bar chart sa Plotly
                try:
                    import plotly.graph_objects as go
                    import plotly.express as px
                    
                    # Sortiraj datume i kreiraj listu sortiranih datuma za x-os
                    unique_dates_bu = sorted(df_chart_bu['balance_date'].unique())
                    date_str_list_bu = [pd.Timestamp(d).strftime('%d.%m.%Y') for d in unique_dates_bu]
                    
                    # Konvertuj datum u string za bolje prikazivanje
                    df_chart_bu['datum_str'] = df_chart_bu['balance_date'].dt.strftime('%d.%m.%Y')
                    
                    # Kreiraj grouped bar chart sa Plotly
                    fig_bu = go.Figure()
                    
                    # Sortiraj kategorije u željenom redosledu
                    category_order_bu = ['Prihodi', 'Rashodi']
                    colors_bu = {'Prihodi': '#2ca02c', 'Rashodi': '#d62728'}  # Zelena za prihode, crvena za rashode
                    
                    # Filtriraj category_order da uključi samo izabrane kategorije
                    filtered_category_order_bu = [cat for cat in category_order_bu if cat in selected_categories_bu] if selected_categories_bu else category_order_bu
                    
                    for kategorija_bu in filtered_category_order_bu:
                        df_cat_bu = df_chart_bu[df_chart_bu['Kategorija'] == kategorija_bu].sort_values('balance_date')
                        if len(df_cat_bu) > 0:
                            # Osiguraj da su vrednosti sortirane po datumu i mapirane na sortirane datume
                            y_values_bu = []
                            for date in unique_dates_bu:
                                matching_row = df_cat_bu[df_cat_bu['balance_date'] == date]
                                if len(matching_row) > 0:
                                    y_values_bu.append(matching_row.iloc[0]['Amount_in_thousands'])
                                else:
                                    y_values_bu.append(None)
                            
                            fig_bu.add_trace(go.Bar(
                                x=date_str_list_bu,
                                y=y_values_bu,
                                name=kategorija_bu,
                                marker_color=colors_bu.get(kategorija_bu, '#808080')
                            ))
                    
                    fig_bu.update_layout(
                        title='Pregled prihoda i rashoda po datumu (Bez poreza na dobit)',
                        xaxis_title='Datum',
                        yaxis_title='Iznos (u hiljadama)',
                        barmode='group',
                        xaxis=dict(tickangle=-45, categoryorder='array', categoryarray=date_str_list_bu),
                        height=500,
                        showlegend=True,
                    )
                    
                    st.plotly_chart(fig_bu, use_container_width=True)
                    
                except ImportError:
                    st.warning("Plotly nije instaliran. Koristim st.bar_chart kao fallback.")
                    # Fallback: st.bar_chart sa pivot tabelom
                    pivot_df_bu = df_chart_bu.pivot_table(
                        index='balance_date',
                        columns='Kategorija',
                        values='Amount_in_thousands',
                        aggfunc='sum'
                    ).fillna(0)
                    pivot_df_bu = pivot_df_bu.sort_index()
                    category_order_bu = ['Prihodi', 'Rashodi']
                    existing_categories_bu = [cat for cat in category_order_bu if cat in pivot_df_bu.columns]
                    if existing_categories_bu:
                        pivot_df_bu = pivot_df_bu[existing_categories_bu]
                    st.bar_chart(pivot_df_bu, height=400)
                
                st.divider()
            
            # Drugi graf - sa novim kategorijama za bilans uspjeha
            if df_bu is not None and "Pozicija" in df_bu.columns:
                class KategorijaBU_2(Enum):
                    PRIHODI_KAMATA = "Prihodi od kamata (neto)"
                    PRIHODI_NAKNADE = "Prihodi od naknada i provizija (neto)"
                
                # Mapa kategorija - korisnik će dodati pozicije iz CSV-ova
                cat_mapper_bu_2 = {
                    KategorijaBU_2.PRIHODI_KAMATA: [
                        "I. NETO PRIHODI OD KAMATA (1 + 2 - 3)",
                    ],
                    KategorijaBU_2.PRIHODI_NAKNADE: [
                        "II. NETO PRIHODI OD NAKNADA I PROVIZIJA (4 - 5)"
                    ],
                }
                
                # Učitaj sve kategorije za drugi graf
                all_categories_data_bu_2 = []
                
                # Pronađi pozicije koje su u obje kategorije (za filtriranje)
                prihodi_pozicije_2 = set(cat_mapper_bu_2.get(KategorijaBU_2.PRIHODI_KAMATA, []))
                rashodi_pozicije_2 = set(cat_mapper_bu_2.get(KategorijaBU_2.PRIHODI_NAKNADE, []))
                zajednicke_pozicije_2 = prihodi_pozicije_2.intersection(rashodi_pozicije_2)
                
                for kategorija_enum_bu_2, pozicije_values_bu_2 in cat_mapper_bu_2.items():
                    for pozicija_value_bu_2 in pozicije_values_bu_2:
                        df_filtered_bu_2 = df_bu[df_bu["Pozicija"] == pozicija_value_bu_2].copy()
                        
                        # Debug: provjeri da li se pozicija poklapa
                        if len(df_filtered_bu_2) == 0:
                            # Pokušaj da pronađeš slične pozicije (case-insensitive, sa trim)
                            unique_pozicije = df_bu["Pozicija"].unique() if "Pozicija" in df_bu.columns else []
                            similar = [p for p in unique_pozicije if str(p).strip().lower() == pozicija_value_bu_2.strip().lower()]
                            if similar:
                                df_filtered_bu_2 = df_bu[df_bu["Pozicija"] == similar[0]].copy()
                                logger.info(f"Pronađena slična pozicija: '{similar[0]}' umjesto '{pozicija_value_bu_2}'")
                        
                        if len(df_filtered_bu_2) > 0 and 'Amount' in df_filtered_bu_2.columns:
                            # Konvertuj Amount u numerički tip pre agregacije
                            if df_filtered_bu_2['Amount'].dtype == 'object':
                                df_filtered_bu_2['Amount'] = df_filtered_bu_2['Amount'].astype(str).str.replace(',', '').astype(float)
                            else:
                                df_filtered_bu_2['Amount'] = pd.to_numeric(df_filtered_bu_2['Amount'], errors='coerce').fillna(0)
                            
                            # Filtriraj vrednosti SAMO ako je pozicija u obje kategorije:
                            # - Za PRIHODI_KAMATA: uzmi samo pozitivne vrednosti (Amount > 0)
                            # - Za PRIHODI_NAKNADE: uzmi samo negativne vrednosti (Amount < 0)
                            if pozicija_value_bu_2 in zajednicke_pozicije_2:
                                if kategorija_enum_bu_2 == KategorijaBU_2.PRIHODI_KAMATA:
                                    df_filtered_bu_2 = df_filtered_bu_2[df_filtered_bu_2['Amount'] > 0].copy()
                                elif kategorija_enum_bu_2 == KategorijaBU_2.PRIHODI_NAKNADE:
                                    df_filtered_bu_2 = df_filtered_bu_2[df_filtered_bu_2['Amount'] < 0].copy()
                                    # Konvertuj negativne vrednosti u pozitivne za prikaz (uzmi apsolutnu vrednost)
                                    df_filtered_bu_2['Amount'] = df_filtered_bu_2['Amount'].abs()
                            
                            # Agregiraj po datumu
                            df_agg_bu_2 = df_filtered_bu_2.groupby('balance_date')['Amount'].sum().reset_index()
                            # Dodaj kolonu sa imenom kategorije
                            df_agg_bu_2['Kategorija'] = kategorija_enum_bu_2.value
                            all_categories_data_bu_2.append(df_agg_bu_2)
                
                # Kombinuj sve kategorije u jedan DataFrame
                if all_categories_data_bu_2:
                    df_aggregated_bu_2 = pd.concat(all_categories_data_bu_2, ignore_index=True)
                    # Agregiraj ponovo po balance_date i Kategorija da bi se sumirale sve pozicije za isti datum i kategoriju
                    df_aggregated_bu_2 = df_aggregated_bu_2.groupby(['balance_date', 'Kategorija'])['Amount'].sum().reset_index()
                else:
                    # Debug: prikaži dostupne pozicije u CSV-u
                    if df_bu is not None and "Pozicija" in df_bu.columns:
                        unique_pozicije = sorted(df_bu["Pozicija"].unique().tolist())
                        st.warning("Nema podataka za prikaz drugog grafikona.")
                        with st.expander("🔍 Debug: Dostupne pozicije u CSV-u"):
                            st.write(f"Broj jedinstvenih pozicija: {len(unique_pozicije)}")
                            st.write("Prvih 20 pozicija:")
                            for poz in unique_pozicije[:20]:
                                st.write(f"- {poz}")
                            st.write("\nTražene pozicije:")
                            for kategorija_enum_bu_2, pozicije_values_bu_2 in cat_mapper_bu_2.items():
                                st.write(f"\n**{kategorija_enum_bu_2.value}:**")
                                for poz in pozicije_values_bu_2:
                                    found = any(str(p).strip().lower() == poz.strip().lower() for p in unique_pozicije)
                                    st.write(f"  - {poz} {'✅' if found else '❌'}")
                    else:
                        st.warning("Nema podataka za prikaz drugog grafikona (dodaj pozicije u cat_mapper_bu_2).")
                    df_aggregated_bu_2 = pd.DataFrame(columns=['balance_date', 'Amount', 'Kategorija'])
            else:
                df_aggregated_bu_2 = pd.DataFrame(columns=['balance_date', 'Amount', 'Kategorija'])
            
            # Drugi graf - sa novim kategorijama
            if df_aggregated_bu_2 is not None and len(df_aggregated_bu_2) > 0:
                df_chart_source_bu_2 = df_aggregated_bu_2.copy()
                if only_year_end_bu:
                    df_chart_source_bu_2 = df_chart_source_bu_2[df_chart_source_bu_2['balance_date'].dt.month == 12]
                
                if df_chart_source_bu_2.empty:
                    st.warning("Nema podataka za prikaz drugog grafikona sa trenutno odabranim filterom (kraj godine).")
                else:
                    st.subheader(f"Pregled neto prihoda od kamata i naknada u periodu: {df_chart_source_bu_2['balance_date'].min().strftime('%d.%m.%Y')} - {df_chart_source_bu_2['balance_date'].max().strftime('%d.%m.%Y')}")
                    
                    # Dodaj kontrolu za izbor kategorija
                    available_categories_bu_2 = sorted(df_chart_source_bu_2['Kategorija'].unique().tolist())
                    selected_categories_bu_2 = st.multiselect(
                        "Izaberi kategorije za prikaz",
                        options=available_categories_bu_2,
                        default=available_categories_bu_2,
                        key="categories_bu_2",
                        help="Možeš ukloniti ili dodati kategorije na grafikonu"
                    )
                    
                    # Filtriraj df_chart_source prema izabranim kategorijama
                    if selected_categories_bu_2:
                        df_chart_bu_2 = df_chart_source_bu_2[df_chart_source_bu_2['Kategorija'].isin(selected_categories_bu_2)].copy()
                    else:
                        st.warning("Nijedna kategorija nije izabrana. Prikazujem sve kategorije.")
                        df_chart_bu_2 = df_chart_source_bu_2.copy()
                    
                    # Konvertuj Amount u numerički tip
                    if df_chart_bu_2['Amount'].dtype == 'object':
                        df_chart_bu_2['Amount'] = df_chart_bu_2['Amount'].astype(str).str.replace(',', '').astype(float)
                    else:
                        df_chart_bu_2['Amount'] = pd.to_numeric(df_chart_bu_2['Amount'], errors='coerce').fillna(0)
                    
                    # Amount je već u hiljadama u CSV-u, samo ga konvertuj u ceo broj
                    df_chart_bu_2['Amount_in_thousands'] = df_chart_bu_2['Amount'].astype(int)
                    
                    # Osiguraj da balance_date je datetime tip
                    if df_chart_bu_2['balance_date'].dtype != 'datetime64[ns]':
                        df_chart_bu_2['balance_date'] = pd.to_datetime(df_chart_bu_2['balance_date'])
                    
                    df_chart_bu_2 = df_chart_bu_2.sort_values(['balance_date', 'Kategorija']).reset_index(drop=True)
                    
                    # Kreiraj bar chart sa Plotly
                    try:
                        import plotly.graph_objects as go
                        import plotly.express as px
                        
                        # Sortiraj datume i kreiraj listu sortiranih datuma za x-os
                        unique_dates_bu_2 = sorted(df_chart_bu_2['balance_date'].unique())
                        date_str_list_bu_2 = [pd.Timestamp(d).strftime('%d.%m.%Y') for d in unique_dates_bu_2]
                        
                        # Konvertuj datum u string za bolje prikazivanje
                        df_chart_bu_2['datum_str'] = df_chart_bu_2['balance_date'].dt.strftime('%d.%m.%Y')
                        
                        # Kreiraj grouped bar chart sa Plotly
                        fig_bu_2 = go.Figure()
                        
                        # Sortiraj kategorije u željenom redosledu
                        category_order_bu_2 = ['Prihodi od kamata (neto)', 'Prihodi od naknada i provizija (neto)']
                        colors_bu_2 = {
                            'Prihodi od kamata (neto)': '#1f77b4',
                            'Prihodi od naknada i provizija (neto)': '#ff7f0e'
                        }
                        
                        # Filtriraj category_order da uključi samo izabrane kategorije
                        filtered_category_order_bu_2 = [cat for cat in category_order_bu_2 if cat in selected_categories_bu_2] if selected_categories_bu_2 else category_order_bu_2
                        
                        for kategorija_bu_2 in filtered_category_order_bu_2:
                            df_cat_bu_2 = df_chart_bu_2[df_chart_bu_2['Kategorija'] == kategorija_bu_2].sort_values('balance_date')
                            if len(df_cat_bu_2) > 0:
                                # Osiguraj da su vrednosti sortirane po datumu i mapirane na sortirane datume
                                y_values_bu_2 = []
                                for date in unique_dates_bu_2:
                                    matching_row = df_cat_bu_2[df_cat_bu_2['balance_date'] == date]
                                    if len(matching_row) > 0:
                                        y_values_bu_2.append(matching_row.iloc[0]['Amount_in_thousands'])
                                    else:
                                        y_values_bu_2.append(None)
                                
                                fig_bu_2.add_trace(go.Bar(
                                    x=date_str_list_bu_2,
                                    y=y_values_bu_2,
                                    name=kategorija_bu_2,
                                    marker_color=colors_bu_2.get(kategorija_bu_2, '#808080')
                                ))
                        
                        fig_bu_2.update_layout(
                            title='Pregled neto prihoda od kamata i naknada po datumu',
                            xaxis_title='Datum',
                            yaxis_title='Iznos (u hiljadama)',
                            barmode='group',
                            xaxis=dict(tickangle=-45, categoryorder='array', categoryarray=date_str_list_bu_2),
                            height=500,
                            showlegend=True,
                        )
                        
                        st.plotly_chart(fig_bu_2, use_container_width=True)
                        
                    except ImportError:
                        st.warning("Plotly nije instaliran. Koristim st.bar_chart kao fallback.")
                        # Fallback: st.bar_chart sa pivot tabelom
                        pivot_df_bu_2 = df_chart_bu_2.pivot_table(
                            index='balance_date',
                            columns='Kategorija',
                            values='Amount_in_thousands',
                            aggfunc='sum'
                        ).fillna(0)
                        pivot_df_bu_2 = pivot_df_bu_2.sort_index()
                        category_order_bu_2 = ['Prihodi od kamata (neto)', 'Prihodi od naknada i provizija (neto)']
                        existing_categories_bu_2 = [cat for cat in category_order_bu_2 if cat in pivot_df_bu_2.columns]
                        if existing_categories_bu_2:
                            pivot_df_bu_2 = pivot_df_bu_2[existing_categories_bu_2]
                        st.bar_chart(pivot_df_bu_2, height=400)
                
                st.divider()
            
            # Treći graf - Rashodi po kategorijama
            if df_bu is not None and "Pozicija" in df_bu.columns:
                class KategorijaBU_3(Enum):
                    TROSKOVI_ZAPOSLENIH = "Troskovi zaposlenih"
                    TROSKOVI_AMORTIZACIJE = "Troskovi amortizacije"
                    OPSTI_TROSKOVI = "Opsti i administrativni troskovi"
                
                # Mapa kategorija za treći graf
                cat_mapper_bu_3 = {
                    KategorijaBU_3.TROSKOVI_ZAPOSLENIH: [
                        "13. Troskovi zaposlenih",
                    ],
                    KategorijaBU_3.TROSKOVI_AMORTIZACIJE: [
                        "14. Troskovi amortizacije",
                    ],
                    KategorijaBU_3.OPSTI_TROSKOVI: [
                        "15. Opsti i administrativni troskovi",
                    ],
                }
                
                # Učitaj sve kategorije za treći graf
                all_categories_data_bu_3 = []
                
                for kategorija_enum_bu_3, pozicije_values_bu_3 in cat_mapper_bu_3.items():
                    for pozicija_value_bu_3 in pozicije_values_bu_3:
                        df_filtered_bu_3 = df_bu[df_bu["Pozicija"] == pozicija_value_bu_3].copy()
                        
                        # Debug: provjeri da li se pozicija poklapa
                        if len(df_filtered_bu_3) == 0:
                            # Pokušaj da pronađeš slične pozicije (case-insensitive, sa trim)
                            unique_pozicije = df_bu["Pozicija"].unique() if "Pozicija" in df_bu.columns else []
                            similar = [p for p in unique_pozicije if str(p).strip().lower() == pozicija_value_bu_3.strip().lower()]
                            if similar:
                                df_filtered_bu_3 = df_bu[df_bu["Pozicija"] == similar[0]].copy()
                                logger.info(f"Pronađena slična pozicija: '{similar[0]}' umjesto '{pozicija_value_bu_3}'")
                        
                        if len(df_filtered_bu_3) > 0 and 'Amount' in df_filtered_bu_3.columns:
                            # Konvertuj Amount u numerički tip pre agregacije
                            if df_filtered_bu_3['Amount'].dtype == 'object':
                                df_filtered_bu_3['Amount'] = df_filtered_bu_3['Amount'].astype(str).str.replace(',', '').astype(float)
                            else:
                                df_filtered_bu_3['Amount'] = pd.to_numeric(df_filtered_bu_3['Amount'], errors='coerce').fillna(0)
                            
                            # Vrednosti su već pozitivne u CSV-u, koristimo ih direktno
                            
                            # Agregiraj po datumu
                            df_agg_bu_3 = df_filtered_bu_3.groupby('balance_date')['Amount'].sum().reset_index()
                            # Dodaj kolonu sa imenom kategorije
                            df_agg_bu_3['Kategorija'] = kategorija_enum_bu_3.value
                            all_categories_data_bu_3.append(df_agg_bu_3)
                
                # Kombinuj sve kategorije u jedan DataFrame
                if all_categories_data_bu_3:
                    df_aggregated_bu_3 = pd.concat(all_categories_data_bu_3, ignore_index=True)
                    # Agregiraj ponovo po balance_date i Kategorija da bi se sumirale sve pozicije za isti datum i kategoriju
                    df_aggregated_bu_3 = df_aggregated_bu_3.groupby(['balance_date', 'Kategorija'])['Amount'].sum().reset_index()
                else:
                    st.warning("Nema podataka za prikaz trećeg grafikona (rashodi).")
                    df_aggregated_bu_3 = pd.DataFrame(columns=['balance_date', 'Amount', 'Kategorija'])
            else:
                df_aggregated_bu_3 = pd.DataFrame(columns=['balance_date', 'Amount', 'Kategorija'])
            
            # Treći graf - Rashodi po kategorijama
            if df_aggregated_bu_3 is not None and len(df_aggregated_bu_3) > 0:
                df_chart_source_bu_3 = df_aggregated_bu_3.copy()
                if only_year_end_bu:
                    df_chart_source_bu_3 = df_chart_source_bu_3[df_chart_source_bu_3['balance_date'].dt.month == 12]
                
                if df_chart_source_bu_3.empty:
                    st.warning("Nema podataka za prikaz trećeg grafikona sa trenutno odabranim filterom (kraj godine).")
                else:
                    st.subheader(f"Pregled rashoda po kategorijama u periodu: {df_chart_source_bu_3['balance_date'].min().strftime('%d.%m.%Y')} - {df_chart_source_bu_3['balance_date'].max().strftime('%d.%m.%Y')}")
                    
                    # Dodaj kontrolu za izbor kategorija
                    available_categories_bu_3 = sorted(df_chart_source_bu_3['Kategorija'].unique().tolist())
                    selected_categories_bu_3 = st.multiselect(
                        "Izaberi kategorije za prikaz",
                        options=available_categories_bu_3,
                        default=available_categories_bu_3,
                        key="categories_bu_3",
                        help="Možeš ukloniti ili dodati kategorije na grafikonu"
                    )
                    
                    # Filtriraj df_chart_source prema izabranim kategorijama
                    if selected_categories_bu_3:
                        df_chart_bu_3 = df_chart_source_bu_3[df_chart_source_bu_3['Kategorija'].isin(selected_categories_bu_3)].copy()
                    else:
                        st.warning("Nijedna kategorija nije izabrana. Prikazujem sve kategorije.")
                        df_chart_bu_3 = df_chart_source_bu_3.copy()
                    
                    # Konvertuj Amount u numerički tip
                    if df_chart_bu_3['Amount'].dtype == 'object':
                        df_chart_bu_3['Amount'] = df_chart_bu_3['Amount'].astype(str).str.replace(',', '').astype(float)
                    else:
                        df_chart_bu_3['Amount'] = pd.to_numeric(df_chart_bu_3['Amount'], errors='coerce').fillna(0)
                    
                    # Amount je već u hiljadama u CSV-u, samo ga konvertuj u ceo broj
                    df_chart_bu_3['Amount_in_thousands'] = df_chart_bu_3['Amount'].astype(int)
                    
                    # Osiguraj da balance_date je datetime tip
                    if df_chart_bu_3['balance_date'].dtype != 'datetime64[ns]':
                        df_chart_bu_3['balance_date'] = pd.to_datetime(df_chart_bu_3['balance_date'])
                    
                    df_chart_bu_3 = df_chart_bu_3.sort_values(['balance_date', 'Kategorija']).reset_index(drop=True)
                    
                    # Kreiraj bar chart sa Plotly
                    try:
                        import plotly.graph_objects as go
                        import plotly.express as px
                        
                        # Sortiraj datume i kreiraj listu sortiranih datuma za x-os
                        unique_dates_bu_3 = sorted(df_chart_bu_3['balance_date'].unique())
                        date_str_list_bu_3 = [pd.Timestamp(d).strftime('%d.%m.%Y') for d in unique_dates_bu_3]
                        
                        # Konvertuj datum u string za bolje prikazivanje
                        df_chart_bu_3['datum_str'] = df_chart_bu_3['balance_date'].dt.strftime('%d.%m.%Y')
                        
                        # Kreiraj grouped bar chart sa Plotly
                        fig_bu_3 = go.Figure()
                        
                        # Sortiraj kategorije u željenom redosledu
                        category_order_bu_3 = [
                            'Troskovi zaposlenih',
                            'Troskovi amortizacije',
                            'Opsti i administrativni troskovi'
                        ]
                        colors_bu_3 = {
                            'Troskovi zaposlenih': '#d62728',
                            'Troskovi amortizacije': '#ff7f0e',
                            'Opsti i administrativni troskovi': '#9467bd'
                        }
                        
                        # Filtriraj category_order da uključi samo izabrane kategorije
                        filtered_category_order_bu_3 = [cat for cat in category_order_bu_3 if cat in selected_categories_bu_3] if selected_categories_bu_3 else category_order_bu_3
                        
                        for kategorija_bu_3 in filtered_category_order_bu_3:
                            df_cat_bu_3 = df_chart_bu_3[df_chart_bu_3['Kategorija'] == kategorija_bu_3].sort_values('balance_date')
                            if len(df_cat_bu_3) > 0:
                                # Osiguraj da su vrednosti sortirane po datumu i mapirane na sortirane datume
                                y_values_bu_3 = []
                                for date in unique_dates_bu_3:
                                    matching_row = df_cat_bu_3[df_cat_bu_3['balance_date'] == date]
                                    if len(matching_row) > 0:
                                        y_values_bu_3.append(matching_row.iloc[0]['Amount_in_thousands'])
                                    else:
                                        y_values_bu_3.append(None)
                                
                                fig_bu_3.add_trace(go.Bar(
                                    x=date_str_list_bu_3,
                                    y=y_values_bu_3,
                                    name=kategorija_bu_3,
                                    marker_color=colors_bu_3.get(kategorija_bu_3, '#808080')
                                ))
                        
                        fig_bu_3.update_layout(
                            title='Pregled rashoda po kategorijama po datumu',
                            xaxis_title='Datum',
                            yaxis_title='Iznos (u hiljadama)',
                            barmode='group',
                            xaxis=dict(tickangle=-45, categoryorder='array', categoryarray=date_str_list_bu_3),
                            height=500,
                            showlegend=True,
                        )
                        
                        st.plotly_chart(fig_bu_3, use_container_width=True)
                        
                    except ImportError:
                        st.warning("Plotly nije instaliran. Koristim st.bar_chart kao fallback.")
                        # Fallback: st.bar_chart sa pivot tabelom
                        pivot_df_bu_3 = df_chart_bu_3.pivot_table(
                            index='balance_date',
                            columns='Kategorija',
                            values='Amount_in_thousands',
                            aggfunc='sum'
                        ).fillna(0)
                        pivot_df_bu_3 = pivot_df_bu_3.sort_index()
                        category_order_bu_3 = [
                            'Troskovi zaposlenih',
                            'Troskovi amortizacije',
                            'Opsti i administrativni troskovi'
                        ]
                        existing_categories_bu_3 = [cat for cat in category_order_bu_3 if cat in pivot_df_bu_3.columns]
                        if existing_categories_bu_3:
                            pivot_df_bu_3 = pivot_df_bu_3[existing_categories_bu_3]
                        st.bar_chart(pivot_df_bu_3, height=400)
                
                st.divider()
            
            # Četvrti graf - Neto profit/gubitak
            if df_bu is not None and "Pozicija" in df_bu.columns:
                class KategorijaBU_4(Enum):
                    NETO_PROFIT = "Neto profit/gubitak"
                
                # Mapa kategorija za četvrti graf
                cat_mapper_bu_4 = {
                    KategorijaBU_4.NETO_PROFIT: [
                        "22. NETO PROFIT/GUBITAK (III - 21)",
                    ],
                }
                
                # Učitaj sve kategorije za četvrti graf
                all_categories_data_bu_4 = []
                
                for kategorija_enum_bu_4, pozicije_values_bu_4 in cat_mapper_bu_4.items():
                    for pozicija_value_bu_4 in pozicije_values_bu_4:
                        df_filtered_bu_4 = df_bu[df_bu["Pozicija"] == pozicija_value_bu_4].copy()
                        
                        # Debug: provjeri da li se pozicija poklapa
                        if len(df_filtered_bu_4) == 0:
                            # Pokušaj da pronađeš slične pozicije (case-insensitive, sa trim)
                            unique_pozicije = df_bu["Pozicija"].unique() if "Pozicija" in df_bu.columns else []
                            similar = [p for p in unique_pozicije if str(p).strip().lower() == pozicija_value_bu_4.strip().lower()]
                            if similar:
                                df_filtered_bu_4 = df_bu[df_bu["Pozicija"] == similar[0]].copy()
                                logger.info(f"Pronađena slična pozicija: '{similar[0]}' umjesto '{pozicija_value_bu_4}'")
                        
                        if len(df_filtered_bu_4) > 0 and 'Amount' in df_filtered_bu_4.columns:
                            # Konvertuj Amount u numerički tip pre agregacije
                            if df_filtered_bu_4['Amount'].dtype == 'object':
                                df_filtered_bu_4['Amount'] = df_filtered_bu_4['Amount'].astype(str).str.replace(',', '').astype(float)
                            else:
                                df_filtered_bu_4['Amount'] = pd.to_numeric(df_filtered_bu_4['Amount'], errors='coerce').fillna(0)
                            
                            # Neto profit može biti i pozitivan i negativan - uzmi sve vrednosti
                            
                            # Agregiraj po datumu
                            df_agg_bu_4 = df_filtered_bu_4.groupby('balance_date')['Amount'].sum().reset_index()
                            # Dodaj kolonu sa imenom kategorije
                            df_agg_bu_4['Kategorija'] = kategorija_enum_bu_4.value
                            all_categories_data_bu_4.append(df_agg_bu_4)
                
                # Kombinuj sve kategorije u jedan DataFrame
                if all_categories_data_bu_4:
                    df_aggregated_bu_4 = pd.concat(all_categories_data_bu_4, ignore_index=True)
                    # Agregiraj ponovo po balance_date i Kategorija da bi se sumirale sve pozicije za isti datum i kategoriju
                    df_aggregated_bu_4 = df_aggregated_bu_4.groupby(['balance_date', 'Kategorija'])['Amount'].sum().reset_index()
                else:
                    st.warning("Nema podataka za prikaz četvrtog grafikona (neto profit/gubitak).")
                    df_aggregated_bu_4 = pd.DataFrame(columns=['balance_date', 'Amount', 'Kategorija'])
            else:
                df_aggregated_bu_4 = pd.DataFrame(columns=['balance_date', 'Amount', 'Kategorija'])
            
            # Četvrti graf - Neto profit/gubitak
            if df_aggregated_bu_4 is not None and len(df_aggregated_bu_4) > 0:
                df_chart_source_bu_4 = df_aggregated_bu_4.copy()
                if only_year_end_bu:
                    df_chart_source_bu_4 = df_chart_source_bu_4[df_chart_source_bu_4['balance_date'].dt.month == 12]
                
                if df_chart_source_bu_4.empty:
                    st.warning("Nema podataka za prikaz četvrtog grafikona sa trenutno odabranim filterom (kraj godine).")
                else:
                    st.subheader(f"Pregled neto profita/gubitka u periodu: {df_chart_source_bu_4['balance_date'].min().strftime('%d.%m.%Y')} - {df_chart_source_bu_4['balance_date'].max().strftime('%d.%m.%Y')}")
                    
                    # Konvertuj Amount u numerički tip
                    if df_chart_source_bu_4['Amount'].dtype == 'object':
                        df_chart_source_bu_4['Amount'] = df_chart_source_bu_4['Amount'].astype(str).str.replace(',', '').astype(float)
                    else:
                        df_chart_source_bu_4['Amount'] = pd.to_numeric(df_chart_source_bu_4['Amount'], errors='coerce').fillna(0)
                    
                    # Amount je već u hiljadama u CSV-u, samo ga konvertuj u ceo broj
                    df_chart_source_bu_4['Amount_in_thousands'] = df_chart_source_bu_4['Amount'].astype(int)
                    
                    # Osiguraj da balance_date je datetime tip
                    if df_chart_source_bu_4['balance_date'].dtype != 'datetime64[ns]':
                        df_chart_source_bu_4['balance_date'] = pd.to_datetime(df_chart_source_bu_4['balance_date'])
                    
                    df_chart_bu_4 = df_chart_source_bu_4.sort_values('balance_date').reset_index(drop=True)
                    
                    # Kreiraj bar chart sa Plotly
                    try:
                        import plotly.graph_objects as go
                        import plotly.express as px
                        
                        # Sortiraj datume i kreiraj listu sortiranih datuma za x-os
                        unique_dates_bu_4 = sorted(df_chart_bu_4['balance_date'].unique())
                        date_str_list_bu_4 = [pd.Timestamp(d).strftime('%d.%m.%Y') for d in unique_dates_bu_4]
                        
                        # Konvertuj datum u string za bolje prikazivanje
                        df_chart_bu_4['datum_str'] = df_chart_bu_4['balance_date'].dt.strftime('%d.%m.%Y')
                        
                        # Kreiraj bar chart sa Plotly - različite boje za pozitivne i negativne vrednosti
                        fig_bu_4 = go.Figure()
                        
                        # Mapiraj vrednosti na sortirane datume za pozitivne i negativne vrednosti
                        y_values_positive = []
                        y_values_negative = []
                        
                        for date in unique_dates_bu_4:
                            matching_row = df_chart_bu_4[df_chart_bu_4['balance_date'] == date]
                            if len(matching_row) > 0:
                                value = matching_row.iloc[0]['Amount_in_thousands']
                                if value >= 0:
                                    y_values_positive.append(value)
                                    y_values_negative.append(None)
                                else:
                                    y_values_positive.append(None)
                                    y_values_negative.append(value)
                            else:
                                y_values_positive.append(None)
                                y_values_negative.append(None)
                        
                        # Dodaj trace samo ako ima pozitivnih vrednosti
                        if any(v is not None for v in y_values_positive):
                            fig_bu_4.add_trace(go.Bar(
                                x=date_str_list_bu_4,
                                y=y_values_positive,
                                name='Profit',
                                marker_color='#2ca02c'  # Zelena za profit
                            ))
                        
                        # Dodaj trace samo ako ima negativnih vrednosti
                        if any(v is not None for v in y_values_negative):
                            fig_bu_4.add_trace(go.Bar(
                                x=date_str_list_bu_4,
                                y=y_values_negative,
                                name='Gubitak',
                                marker_color='#d62728'  # Crvena za gubitak
                            ))
                        
                        fig_bu_4.update_layout(
                            title='Neto profit/gubitak po datumu',
                            xaxis_title='Datum',
                            yaxis_title='Iznos (u hiljadama)',
                            barmode='overlay',  # Preklapaju se barovi
                            xaxis=dict(tickangle=-45, categoryorder='array', categoryarray=date_str_list_bu_4),
                            height=500,
                            showlegend=True,
                        )
                        
                        st.plotly_chart(fig_bu_4, use_container_width=True)
                        
                    except ImportError:
                        st.warning("Plotly nije instaliran. Koristim st.bar_chart kao fallback.")
                        # Fallback: st.bar_chart
                        pivot_df_bu_4 = df_chart_bu_4.set_index('balance_date')['Amount_in_thousands']
                        st.bar_chart(pivot_df_bu_4, height=400)
        
        else:
            st.warning("Nema podataka za prikaz grafikona.")
    
    # Glavni sadržaj (komentarisano)
            only_year_end = st.checkbox(
                "Prikaži samo stanje na kraju godine",
                value=True,
                help="Ako je uključeno, prikazuju se samo podaci za decembar (kraj svake godine)."
            )

            df_chart_source = df_aggregated.copy()
            if only_year_end:
                df_chart_source = df_chart_source[df_chart_source['balance_date'].dt.month == 12]

            if df_chart_source.empty:
                st.warning("Nema podataka za prikaz sa trenutno odabranim filterom (kraj godine).")
            else:
                st.subheader(f"Pregled svih kategorija u periodu: {df_chart_source['balance_date'].min().strftime('%d.%m.%Y')} - {df_chart_source['balance_date'].max().strftime('%d.%m.%Y')}")

                # Dodaj kontrolu za izbor kategorija
                available_categories = sorted(df_chart_source['Kategorija'].unique().tolist())
                selected_categories = st.multiselect(
                    "Izaberi kategorije za prikaz",
                    options=available_categories,
                    default=available_categories,  # Podrazumevano sve kategorije
                    help="Možeš ukloniti ili dodati kategorije na grafikonu"
                )
                
                # Filtriraj df_chart_source prema izabranim kategorijama
                if selected_categories:
                    df_chart = df_chart_source[df_chart_source['Kategorija'].isin(selected_categories)].copy()
                else:
                    st.warning("Nijedna kategorija nije izabrana. Prikazujem sve kategorije.")
                    df_chart = df_chart_source.copy()
                
                # Konvertuj Amount u numerički tip
                if df_chart['Amount'].dtype == 'object':
                    df_chart['Amount'] = df_chart['Amount'].astype(str).str.replace(',', '').astype(float)
                else:
                    df_chart['Amount'] = pd.to_numeric(df_chart['Amount'], errors='coerce').fillna(0)
                
                # Amount je već u hiljadama u CSV-u, samo ga konvertuj u ceo broj
                df_chart['Amount_in_thousands'] = df_chart['Amount'].astype(int)
                
                # Osiguraj da balance_date je datetime tip
                if df_chart['balance_date'].dtype != 'datetime64[ns]':
                    df_chart['balance_date'] = pd.to_datetime(df_chart['balance_date'])
                
                df_chart = df_chart.sort_values(['balance_date', 'Kategorija']).reset_index(drop=True)
                
                # Koristi Plotly za grupisanje barova
                try:
                    import plotly.graph_objects as go
                    import plotly.express as px
                    
                    # Sortiraj datume i kreiraj listu sortiranih datuma za x-os
                    unique_dates = sorted(df_chart['balance_date'].unique())
                    date_str_list = [pd.Timestamp(d).strftime('%d.%m.%Y') for d in unique_dates]
                    
                    # Konvertuj datum u string za bolje prikazivanje
                    df_chart['datum_str'] = df_chart['balance_date'].dt.strftime('%d.%m.%Y')
                    
                    # Kreiraj grouped bar chart sa Plotly
                    fig = go.Figure()
                    
                    # Sortiraj kategorije u željenom redosledu (samo one koje su izabrane)
                    category_order = ['Aktiva', 'Obaveze', 'Kapital',]
                    colors = {'Aktiva': '#1f77b4', 'Obaveze': '#ff7f0e', 'Kapital': '#2ca02c', }
                    
                    # Filtriraj category_order da uključi samo izabrane kategorije
                    filtered_category_order = [cat for cat in category_order if cat in selected_categories] if selected_categories else category_order
                    
                    for kategorija in filtered_category_order:
                        df_cat = df_chart[df_chart['Kategorija'] == kategorija].sort_values('balance_date')
                        if len(df_cat) > 0:
                            # Osiguraj da su vrednosti sortirane po datumu i mapirane na sortirane datume
                            y_values = []
                            for date in unique_dates:
                                matching_row = df_cat[df_cat['balance_date'] == date]
                                if len(matching_row) > 0:
                                    y_values.append(matching_row.iloc[0]['Amount_in_thousands'])
                                else:
                                    y_values.append(None)
                            
                            fig.add_trace(go.Bar(
                                x=date_str_list,
                                y=y_values,
                                name=kategorija,
                                marker_color=colors.get(kategorija, '#808080')
                            ))
                    
                    fig.update_layout(
                        title='Pregled kategorija po datumu',
                        xaxis_title='Datum',
                        yaxis_title='Iznos (u hiljadama)',
                        barmode='group',
                        xaxis=dict(tickangle=-45, categoryorder='array', categoryarray=date_str_list),
                        height=500,
                        showlegend=True
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                except ImportError:
                    st.warning("Plotly nije instaliran. Koristim st.bar_chart kao fallback.")
                    # Fallback: st.bar_chart sa pivot tabelom
                    pivot_df = df_chart.pivot_table(
                        index='balance_date',
                        columns='Kategorija',
                        values='Amount_in_thousands',
                        aggfunc='sum'
                    ).fillna(0)
                    pivot_df = pivot_df.sort_index()
                    category_order = ['Aktiva', 'Obaveze', 'Kapital']
                    existing_categories = [cat for cat in category_order if cat in pivot_df.columns]
                    if existing_categories:
                        pivot_df = pivot_df[existing_categories]
                    st.bar_chart(pivot_df, height=400)

                st.divider()
            
            # Drugi graf - sa drugim kategorijama
            if df is not None and "Pozicija" in df.columns and len(df_aggregated) > 0:
                class Kategorija_2(Enum):
                    KREDITI_KLIJENATA = "Krediti klijenata"
                    HoV = "Hartije od vrijednosti"
                    DEPOZITI_KLIJENATA = "Depoziti klijenata"

                cat_mapper_2 = {
                    Kategorija_2.KREDITI_KLIJENATA: ["2.b. Krediti i potrazivanja od klijenata","2.a. Krediti i potrazivanja od banaka"],
                    Kategorija_2.HoV: ["2.c. Hartije od vrijednosti","3.c. Hartije od vrijednosti","4.c. Hartije od vrijednosti"],
                    Kategorija_2.DEPOZITI_KLIJENATA: "17.b. Depoziti klijenata",
                }
                
                # Učitaj sve kategorije za drugi graf
                all_categories_data_2 = []
                
                for kategorija_enum_2, pozicije_values in cat_mapper_2.items():
                    for pozicija_value_2 in (pozicije_values if isinstance(pozicije_values, list) else [pozicije_values]):
                        df_filtered_2 = df[df["Pozicija"] == pozicija_value_2].copy()
                        
                        if len(df_filtered_2) > 0 and 'Amount' in df_filtered_2.columns:
                            # Konvertuj Amount u numerički tip pre agregacije
                            if df_filtered_2['Amount'].dtype == 'object':
                                df_filtered_2['Amount'] = df_filtered_2['Amount'].astype(str).str.replace(',', '').astype(float)
                            else:
                                df_filtered_2['Amount'] = pd.to_numeric(df_filtered_2['Amount'], errors='coerce').fillna(0)
                            
                            # Agregiraj po datumu
                            df_agg_2 = df_filtered_2.groupby('balance_date')['Amount'].sum().reset_index()
                            # Dodaj kolonu sa imenom kategorije
                            df_agg_2['Kategorija'] = kategorija_enum_2.value
                            all_categories_data_2.append(df_agg_2)
                
                # Kombinuj sve kategorije u jedan DataFrame
                if all_categories_data_2:
                    df_aggregated_2 = pd.concat(all_categories_data_2, ignore_index=True)

                    df_chart_2_source = df_aggregated_2.copy()
                    if only_year_end:
                        df_chart_2_source = df_chart_2_source[df_chart_2_source['balance_date'].dt.month == 12]

                    if df_chart_2_source.empty:
                        st.warning("Nema podataka za prikaz kredita i depozita sa trenutno odabranim filterom (kraj godine).")
                    else:
                        ratio_source = df_chart_2_source.copy()
                        if ratio_source['Amount'].dtype == 'object':
                            ratio_source['Amount'] = ratio_source['Amount'].astype(str).str.replace(',', '').astype(float)
                        else:
                            ratio_source['Amount'] = pd.to_numeric(ratio_source['Amount'], errors='coerce').fillna(0)
                        ratio_source['Amount_in_thousands'] = ratio_source['Amount'].astype(int)
                        st.subheader(f"Pregled kredita i depozita u periodu: {df_chart_2_source['balance_date'].min().strftime('%d.%m.%Y')} - {df_chart_2_source['balance_date'].max().strftime('%d.%m.%Y')}")
                    
                        # Dodaj kontrolu za izbor kategorija
                        available_categories_2 = sorted(df_chart_2_source['Kategorija'].unique().tolist())
                        selected_categories_2 = st.multiselect(
                            "Izaberi kategorije za pregled kredita i depozita",
                            options=available_categories_2,
                            default=available_categories_2,
                            help="Možeš ukloniti ili dodati kategorije na grafikonu"
                        )
                        
                        # Filtriraj df_aggregated_2 prema izabranim kategorijama
                        if selected_categories_2:
                            df_chart_2 = df_chart_2_source[df_chart_2_source['Kategorija'].isin(selected_categories_2)].copy()
                        else:
                            st.warning("Nijedna kategorija nije izabrana. Prikazujem sve kategorije.")
                            df_chart_2 = df_chart_2_source.copy()
                        
                        # Konvertuj Amount u numerički tip
                        if df_chart_2['Amount'].dtype == 'object':
                            df_chart_2['Amount'] = df_chart_2['Amount'].astype(str).str.replace(',', '').astype(float)
                        else:
                            df_chart_2['Amount'] = pd.to_numeric(df_chart_2['Amount'], errors='coerce').fillna(0)
                        
                        # Amount je već u hiljadama u CSV-u, samo ga konvertuj u ceo broj
                        df_chart_2['Amount_in_thousands'] = df_chart_2['Amount'].astype(int)
                        
                        # Osiguraj da balance_date je datetime tip
                        if df_chart_2['balance_date'].dtype != 'datetime64[ns]':
                            df_chart_2['balance_date'] = pd.to_datetime(df_chart_2['balance_date'])
                        
                        df_chart_2 = df_chart_2.sort_values(['balance_date', 'Kategorija']).reset_index(drop=True)
                        
                        # Koristi Plotly za grupisanje barova
                        try:
                            import plotly.graph_objects as go
                            import plotly.express as px
                            
                            # Sortiraj datume i kreiraj listu sortiranih datuma za x-os
                            unique_dates_2 = sorted(df_chart_2['balance_date'].unique())
                            date_str_list_2 = [pd.Timestamp(d).strftime('%d.%m.%Y') for d in unique_dates_2]
                            
                            # Konvertuj datum u string za bolje prikazivanje
                            df_chart_2['datum_str'] = df_chart_2['balance_date'].dt.strftime('%d.%m.%Y')
                            
                            # Kreiraj grouped bar chart sa Plotly
                            fig2 = go.Figure()
                            
                            # Sortiraj kategorije u željenom redosledu
                            category_order_2 = ['Krediti klijenata','Hartije od vrijednosti', 'Depoziti klijenata']
                            colors_2 = {'Krediti klijenata': '#1f77b4', 'Hartije od vrijednosti': '#ff7f0e', 'Depoziti klijenata': '#2ca02c'}
                            
                            # Filtriraj category_order_2 da uključi samo izabrane kategorije
                            filtered_category_order_2 = [cat for cat in category_order_2 if cat in selected_categories_2] if selected_categories_2 else category_order_2
                            
                            for kategorija in filtered_category_order_2:
                                df_cat_2 = df_chart_2[df_chart_2['Kategorija'] == kategorija].sort_values('balance_date')
                                if len(df_cat_2) > 0:
                                    # Osiguraj da su vrednosti sortirane po datumu i mapirane na sortirane datume
                                    y_values_2 = []
                                    for date in unique_dates_2:
                                        matching_row = df_cat_2[df_cat_2['balance_date'] == date]
                                        if len(matching_row) > 0:
                                            y_values_2.append(matching_row.iloc[0]['Amount_in_thousands'])
                                        else:
                                            y_values_2.append(None)
                                    
                                    fig2.add_trace(go.Bar(
                                        x=date_str_list_2,
                                        y=y_values_2,
                                        name=kategorija,
                                        marker_color=colors_2.get(kategorija, '#808080'),
                                        offsetgroup=kategorija,
                                        legendgroup=kategorija
                                    ))
                            
                            fig2.update_layout(
                                title='Pregled kredita, HoV i depozita po datumu',
                                xaxis_title='Datum',
                                yaxis_title='Iznos (u hiljadama)',
                                barmode='group',
                                xaxis=dict(tickangle=-45, categoryorder='array', categoryarray=date_str_list_2),
                                height=500,
                                showlegend=True
                            )
                            
                            st.plotly_chart(fig2, use_container_width=True)
                            
                        except ImportError:
                            st.warning("Plotly nije instaliran. Koristim st.bar_chart kao fallback.")
                            # Fallback: st.bar_chart sa pivot tabelom
                            pivot_df_2 = df_chart_2.pivot_table(
                                index='balance_date',
                                columns='Kategorija',
                                values='Amount_in_thousands',
                                aggfunc='sum'
                            ).fillna(0)
                            pivot_df_2 = pivot_df_2.sort_index()
                            category_order_2 = ['Krediti klijenata','Hartije od vrijednosti', 'Depoziti klijenata']
                            existing_categories_2 = [cat for cat in category_order_2 if cat in pivot_df_2.columns]
                            if existing_categories_2:
                                pivot_df_2 = pivot_df_2[existing_categories_2]
                            st.bar_chart(pivot_df_2, height=400)

                        # Dodatni graf: odnos kredita i depozita (K/D ratio)
                        ratio_pivot = ratio_source.pivot_table(
                            index='balance_date',
                            columns='Kategorija',
                            values='Amount_in_thousands',
                            aggfunc='sum'
                        ).fillna(0)
                        ratio_pivot = ratio_pivot.sort_index()

                        if {'Krediti klijenata', 'Depoziti klijenata'}.issubset(ratio_pivot.columns):
                            ratio_pivot['K/D odnos'] = ratio_pivot['Krediti klijenata'] / ratio_pivot['Depoziti klijenata'].replace({0: pd.NA})
                            ratio_pivot = ratio_pivot.dropna(subset=['K/D odnos'])

                            if not ratio_pivot.empty:
                                st.write("### Odnos kredita i depozita (K/D)")
                                try:
                                    import plotly.graph_objects as go
                                    # Sortiraj datume i kreiraj listu sortiranih datuma za x-os
                                    ratio_pivot = ratio_pivot.sort_index()
                                    ratio_dates = sorted(ratio_pivot.index)
                                    ratio_date_str_list = [pd.Timestamp(d).strftime('%d.%m.%Y') for d in ratio_dates]
                                    
                                    # Mapiraj vrednosti na sortirane datume
                                    ratio_y_values = []
                                    for date in ratio_dates:
                                        if date in ratio_pivot.index:
                                            ratio_y_values.append((ratio_pivot.loc[date, 'K/D odnos'] * 100).round(2))
                                        else:
                                            ratio_y_values.append(None)

                                    fig_ratio = go.Figure(
                                        data=[
                                            go.Bar(
                                                x=ratio_date_str_list,
                                                y=ratio_y_values,
                                                text=[f"{v}%" if v is not None else "" for v in ratio_y_values],
                                                textposition='outside',
                                                width=0.6
                                            )
                                        ]
                                    )

                                    fig_ratio.update_layout(
                                        title='Odnos kredita i depozita (K/D) u %',
                                        xaxis_title='Datum',
                                        yaxis_title='K/D (%)',
                                        yaxis=dict(ticksuffix='%', tickformat='.2f'),
                                        xaxis=dict(categoryorder='array', categoryarray=ratio_date_str_list),
                                        height=400,
                                        bargap=0.3
                                    )
                                    fig_ratio.update_traces(
                                        hovertemplate='Datum: %{x}<br>K/D: %{y:.2f}%<extra></extra>'
                                    )

                                    st.plotly_chart(fig_ratio, use_container_width=True)
                                except ImportError:
                                    st.bar_chart((ratio_pivot['K/D odnos'] * 100).round(2), height=300)
                            else:
                                st.info("Nije moguće izračunati odnos K/D (nedostaju podaci ili su depoziti 0).")
                        else:
                            st.info("Za prikaz odnosa K/D neophodno je imati i kredite i depozite u podacima.")
            else:
                st.warning("Nema podataka za prikaz drugog grafikona.")
    
    # Glavni sadržaj (komentarisano)
    #if selected_file_idx is not None:
    #    selected_file = filtered_files_sorted[selected_file_idx]
    #    
    #    # Header sa informacijama o fajlu
        #col1, col2, col3 = st.columns(3)
        
        #with col1:
            #st.metric("Ime fajla", selected_file.name)
        
        #with col2:
            #file_size = selected_file.stat().st_size
            #st.metric("Veličina", format_file_size(file_size))
        
        #with col3:
            #st.metric("Putanja", str(selected_file.relative_to(Path(csv_folder))))
        
        st.divider()
        
        # Učitaj i prikaži CSV
        #with st.spinner("Učitavam CSV fajl..."):
            #df = load_csv_file(selected_file)
        
        #if df is not None:
            # Osnovne informacije
            #col1, col2, col3, col4 = st.columns(4)
            
            #with col1:
                #st.metric("Redovi", len(df))
            
            #with col2:
                #st.metric("Kolone", len(df.columns))
            
            #with col3:
                #st.metric("Prazne ćelije", df.isna().sum().sum())
            
            #with col4:
                #memory_usage = df.memory_usage(deep=True).sum()
                #st.metric("Memorija", format_file_size(memory_usage))
            
            #st.divider()
            
            # Tabs za različite prikaze
            #tab1, tab2, tab3, tab4 = st.tabs([
            #    "📋 Podaci", 
            #    "📊 Statistika", 
            #    "🔍 Pretraga", 
            #    "💾 Export"
            #])
            
            #with tab1:
                #st.subheader("Tabela podataka")
                
                # Opcije za prikaz
                #show_options = st.expander("⚙️ Opcije prikaza", expanded=False)
                #with show_options:
                    #max_rows = st.slider(
                        #"Maksimalno redova",
                        #min_value=10,
                        #max_value=min(1000, len(df)),
                        #value=min(100, len(df)),
                        #step=10
                    #)
                    #show_index = st.checkbox("Prikaži indeks", value=False)
                
                #st.dataframe(
                    #df.head(max_rows),
                    #width='stretch',
                    #hide_index=not show_index
                #)
                
                #if len(df) > max_rows:
                    #st.info(f"Prikazano prvih {max_rows} od {len(df)} redova")
            
            #with tab2:
                #st.subheader("Statistika")
                
                # Opisne statistike
                #if len(df.select_dtypes(include=['number']).columns) > 0:
                    #st.write("**Numeričke kolone:**")
                    #st.dataframe(
                        #df.select_dtypes(include=['number']).describe(),
                        #width='stretch'
                    #)
                
                # Info o tipovima podataka
                #st.write("**Tipovi podataka:**")
                #dtype_info = pd.DataFrame({
                    #'Kolone': df.columns,
                    #'Tip': [str(dtype) for dtype in df.dtypes],
                    #'Nedostajuće vrednosti': df.isna().sum().values,
                    #'Jedinstvene vrednosti': [df[col].nunique() for col in df.columns]
                #})
                #st.dataframe(dtype_info, width='stretch', hide_index=True)
            
            #with tab3:
                #st.subheader("Pretraga i filtriranje")
                
                # Filter po kolonama
                #filter_cols = st.multiselect(
                    #"Izaberi kolone za prikaz",
                    #options=df.columns.tolist(),
                    #default=df.columns.tolist()[:min(5, len(df.columns))]
                #)
                
                #if filter_cols:
                    #filtered_df = df[filter_cols]
                    
                    # Tekstualna pretraga
                    #search_col = st.selectbox(
                        #"Pretraži u koloni",
                    #    options=[None] + filter_cols,
                    #    format_func=lambda x: "Sve kolone" if x is None else x
                    #)
                    
                    #search_text = st.text_input("Tekst za pretragu")
                    
                    #if search_text:
                        #if search_col:
                            #mask = filtered_df[search_col].astype(str).str.contains(
                                #search_text, case=False, na=False
                            #)
                        #else:
                            #mask = filtered_df.astype(str).apply(
                                #lambda x: x.str.contains(search_text, case=False, na=False)
                            #).any(axis=1)
                        #filtered_df = filtered_df[mask]
                    
                    #st.dataframe(
                        #filtered_df,
                        #width='stretch',
                        #hide_index=True
                    #)
                    #st.info(f"Pronađeno {len(filtered_df)} redova")
            
            #with tab4:
                #st.subheader("Export podataka")
                
                #export_format = st.radio(
                    #"Format za export",
                    #options=["CSV", "Excel", "JSON"],
                    #horizontal=True
                #)
                
                #if st.button("💾 Preuzmi fajl"):
                    #if export_format == "CSV":
                        #csv_data = df.to_csv(index=False)
                        #st.download_button(
                            #label="Preuzmi CSV",
                            #data=csv_data,
                            #file_name=f"{selected_file.stem}_export.csv",
                            #mime="text/csv"
                        #)
                    #elif export_format == "Excel":
                        # Za Excel treba openpyxl
                        #try:
                            #import io
                            #buffer = io.BytesIO()
                            #df.to_excel(buffer, index=False, engine='openpyxl')
                            #buffer.seek(0)
                            #st.download_button(
                                #label="Preuzmi Excel",
                                #data=buffer,
                                #file_name=f"{selected_file.stem}_export.xlsx",
                                #mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            #)
                        #except ImportError:
                            #st.error("Za Excel export instaliraj: pip install openpyxl")
                    #elif export_format == "JSON":
                        #json_data = df.to_json(orient='records', indent=2)
                        #st.download_button(
                            #label="Preuzmi JSON",
                            #data=json_data,
                            #file_name=f"{selected_file.stem}_export.json",
                            #mime="application/json"
                        #)
        #else:
            #st.error("Nije moguće učitati CSV fajl.")SW


if __name__ == "__main__":
    main()

