# app.py - Streamlit aplikacija za prikaz CSV rezultata

import streamlit as st
import pandas as pd
from pathlib import Path
from typing import List, Optional, cast
from enum import Enum
import os

from src.config import DOWNLOAD_FOLDER

# Konfiguracija stranice
st.set_page_config(
    page_title="PDF to CSV Viewer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Default folder za CSV fajlove
CSV_FOLDER = "data/csv_output/slike_i_fajlovi/fajlovi/fajlovi_kontrola_banaka/pokazatelji/banke"


@st.cache_data
def get_all_csv_files(csv_folder: str = CSV_FOLDER) -> List[Path]:
    """Pronalazi sve CSV fajlove u folderu (rekurzivno)."""
    csv_dir = Path(csv_folder)
    if not csv_dir.exists():
        return []
    return list(csv_dir.rglob("*.csv"))


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
    st.title("📊 Analiza-bilansi stanja")
    st.markdown("Pregled bilansa stanja i uspjeha banaka u periodu 2020-2025")

    
    class Akcija(Enum):
        PBCG = "Prva banka CG"
        CKB = "Crnogorska komercijalna banka"
        NLB = "NLB Montenegro banka"

    
    # Sidebar za navigaciju i filtere
    with st.sidebar:
        st.header("🔍 Navigacija")

        
        bank_chooser = st.selectbox(
            "Izaberite banku:",
            options=list(Akcija), # Daje listu [Akcija.SHOW_ALL, Akcija.ADD_NEW, ...]
            format_func=lambda clan: clan.value # Za prikaz koristi vrijednost (npr. "Prikaži sve...")
        )

        bank_folder_map = {
            Akcija.PBCG: "data/csv_output/slike_i_fajlovi/fajlovi/fajlovi_kontrola_banaka/pokazatelji/banke/bs/nik",
            Akcija.CKB: "data/csv_output/slike_i_fajlovi/fajlovi/fajlovi_kontrola_banaka/pokazatelji/banke/bs/ckb",
            Akcija.NLB: "data/csv_output/slike_i_fajlovi/fajlovi/fajlovi_kontrola_banaka/pokazatelji/banke/bs/mnb",
        }

        csv_folder = bank_folder_map.get(bank_chooser)
        if csv_folder is None:
            st.error("Neispravan izbor")
            st.stop()
        assert csv_folder is not None
        csv_folder = cast(str, csv_folder)

        # Folder selection
        #csv_folder = st.text_input(
        #    "CSV Folder",
        #    value=CSV_FOLDER,
        #    help="Putanja do foldera sa CSV fajlovima"
        #)

        # Koristi folder iz mape banaka
        # csv_folder = CSV_FOLDER
        
        # Učitaj sve CSV fajlove
        csv_files = get_all_csv_files(csv_folder)
        
        if not csv_files:
            st.warning(f"Nema CSV fajlova u folderu: {csv_folder}")
            st.stop()
        
        #st.success(f"Pronađeno {len(csv_files)} CSV fajlova")
        
        # Pretraga fajlova
        #search_term = st.text_input(
        #    "🔎 Pretraži fajlove",
        #    placeholder="Unesi ime fajla...",
        #    help="Filtriraj CSV fajlove po imenu"
        #)
        
        # Filtriraj fajlove - samo oni iz 2020+ (format mmyy* gdje yy >= 20)
        filtered_files = []
        for f in csv_files:
            file_name = f.name
            # Provjeri da li fajl ima format mmyy* (npr. 1220nik_bs.csv)
            if len(file_name) >= 4 and file_name[:4].isdigit():
                yy = int(file_name[2:4])  # Uzmi poslednje 2 cifre (godina)
                if yy >= 20:  # 2020 ili novije
                    filtered_files.append(f)
        
        #st.info(f"Prikazano: {len(filtered_files)} fajlova")

        df = None
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
                st.dataframe(df_aggregated)
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
            
            # Korak 4: Koristi Plotly za grupisanje barova (najbolje rešenje za grouped bars)
            try:
                import plotly.graph_objects as go
                import plotly.express as px
                
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
                        fig.add_trace(go.Bar(
                            x=df_cat['datum_str'],
                            y=df_cat['Amount_in_thousands'],
                            name=kategorija,
                            marker_color=colors.get(kategorija, '#808080')  # Siva ako kategorija nema definisanu boju
                        ))
                
                fig.update_layout(
                    title='Pregled kategorija po datumu',
                    xaxis_title='Datum',
                    yaxis_title='Iznos (u hiljadama)',
                    barmode='group',  # Ovo je ključno - grupiše barove jedan pored drugog
                    xaxis=dict(tickangle=-45),
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
                                fig2.add_trace(go.Bar(
                                    x=df_cat_2['datum_str'],
                                    y=df_cat_2['Amount_in_thousands'],
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
                            xaxis=dict(tickangle=-45),
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
                                ratio_pivot['datum_str'] = ratio_pivot.index.strftime('%d.%m.%Y')

                                fig_ratio = go.Figure(
                                    data=[
                                        go.Bar(
                                            x=ratio_pivot['datum_str'],
                                            y=(ratio_pivot['K/D odnos'] * 100).round(2),
                                            text=(ratio_pivot['K/D odnos'] * 100).round(2).astype(str) + '%',
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
    
    # Glavni sadržaj
    #if selected_file_idx is not None:
    #    selected_file = filtered_files_sorted[selected_file_idx]
        
        # Header sa informacijama o fajlu
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

