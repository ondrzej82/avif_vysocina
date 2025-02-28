import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import folium_static
from folium.plugins import HeatMap
from datetime import datetime

# Cesta k souboru
import os

# -------------------------
# Nastavení "wide" layoutu a titulku aplikace
# -------------------------
st.set_page_config(page_title="Avif statistika", layout="wide")

FILE_PATH = "uploaded_file.csv"

# Zkontrolujeme, zda soubor existuje, a nastavíme výchozí cestu v session_state
if "file_path" not in st.session_state:
    if os.path.exists(FILE_PATH):
        st.session_state["file_path"] = FILE_PATH
    else:
        st.session_state["file_path"] = "pozorovani.csv"

# Uploader pro soubor
uploaded_file = st.file_uploader("Nahrajte soubor CSV", type=["csv"])

if uploaded_file is not None:
    # Uložíme soubor na disk
    with open(FILE_PATH, "wb") as f:
        f.write(uploaded_file.getbuffer())

    # Aktualizujeme session_state, aby byl soubor dostupný pro všechny
    st.session_state["file_path"] = FILE_PATH
    st.success("Soubor byl úspěšně nahrán a uložen.")

@st.cache_data
def load_data(file):
    try:
        df = pd.read_csv(file, delimiter=';', encoding='utf-8-sig')
        if df.empty:
            st.error("Nahraný soubor je prázdný. Nahrajte platný CSV soubor.")
            st.stop()
    except pd.errors.EmptyDataError:
        st.error("Soubor je prázdný nebo neplatný. Nahrajte prosím platný CSV soubor.")
        st.stop()
    df.rename(columns={
        "Date": "Datum",
        "SiteName": "Místo pozorování",
        "CountMin": "Počet",
        "ItemLink": "Odkaz",
        "Latitude": "Zeměpisná šířka",
        "Longitude": "Zeměpisná délka"
    }, inplace=True)
    df["Datum"] = pd.to_datetime(df["Datum"], format='%Y-%m-%d', errors='coerce')
    df = df.reset_index(drop=True)
    df["Odkaz"] = df["Odkaz"].apply(lambda x: f'<a href="{x}" target="_blank">link</a>' if pd.notna(x) else "")
    df["Počet"].fillna(1, inplace=True)
    df["Místo pozorování"].fillna("", inplace=True)
    df["Počet"] = df["Počet"].astype(int)
    return df

df = None
if uploaded_file is None and not os.path.exists("pozorovani.csv"):
    st.warning("Prosím nahrajte soubor CSV, než aplikace začne pracovat.")
    st.stop()

if uploaded_file is not None or os.path.exists("pozorovani.csv"):
    df = load_data(st.session_state["file_path"])
