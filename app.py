import requests
import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import folium_static
from folium.plugins import HeatMap
from datetime import datetime
from io import StringIO

# Cesta k souboru
import os

# -------------------------
# Nastavení "wide" layoutu a titulku aplikace
# -------------------------
st.set_page_config(page_title="Avif statistika", layout="wide")

                   
# 🔹 Přímý odkaz na soubor na Google Drive (vyměň ID souboru!)
GOOGLE_DRIVE_FILE_ID = "1rg_3k3OKMJ2C_DkSmFxKfiYMLDRpuyEp"
GOOGLE_DRIVE_URL = f"https://drive.google.com/uc?export=download&id=1rg_3k3OKMJ2C_DkSmFxKfiYMLDRpuyEp"

@st.cache_data
def load_data_from_drive():
    """Načte CSV soubor přímo z Google Drive."""
    try:
        response = requests.get(GOOGLE_DRIVE_URL)
        response.raise_for_status()  # Ověří, zda je soubor dostupný
        csv_data = StringIO(response.text)
        df = pd.read_csv(csv_data, delimiter=";", encoding="utf-8-sig")
        return df
    except requests.exceptions.RequestException as e:
        st.error(f"Chyba při načítání dat: {e}")
        return pd.DataFrame()  # Při chybě vrátíme prázdný DataFrame

# 🔹 Uživatelské nahrání souboru
uploaded_file = st.file_uploader("Nahrajte nový soubor CSV", type=["csv"])

if uploaded_file is not None:
    st.warning("Uložit nahraný soubor do Google Drive musíte manuálně.")
    df = pd.read_csv(uploaded_file, delimiter=";", encoding="utf-8-sig")
else:
    df = load_data_from_drive()

if df.empty:
    st.warning("Nepodařilo se načíst data. Zkontrolujte odkaz na soubor Google Drive.")
else:
    st.success("Data byla úspěšně načtena!")

# 🔹 Zpracování dat
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

# 🔹 Výstup dat v aplikaci
#st.write(df.head())


# ------------------
# Checkboxy pro zobrazení / skrytí grafů a map (nahoře na stránce)
# ------------------
with st.expander("Zobrazení grafů a map"):
    c1, c2, c3 = st.columns(3)
    with c1:
        show_bar_yearly = st.checkbox("Graf: Počet druhů v jednotlivých letech", value=True)
        show_bar_species_yearly = st.checkbox("Graf: Počet pozorování vybraného druhu", value=True)
    with c2:
        show_pie_top_species = st.checkbox("Koláč: Nejčastější druhy", value=True)
        show_bar_monthly_obs = st.checkbox("Graf: Počty pozorování podle měsíců", value=True)
    with c3:
        show_bar_monthly_count = st.checkbox("Graf: Počty jedinců podle měsíců", value=True)
        show_map_markers = st.checkbox("Mapa s body pozorování", value=True)
        show_map_heat = st.checkbox("Heatmapa pozorování", value=True)

# ------------------
# Filtry: Druh + Datum + Aktivita
# ------------------

species_column = "SpeciesName"  # Sloupec s názvem druhu
activity_column = "Activity"     # Sloupec s aktivitou

# 1) Filtr druhu
species_list = ["Vyber"]
if df is not None and not df.empty and species_column in df.columns:
    species_list = ["Vyber"] + sorted(set(df[species_column].dropna().unique()))
selected_species = st.selectbox("Vyber druh ptáka:", species_list)

# 2) Filtr data
date_min = df["Datum"].min().date() if df is not None and not df.empty else datetime.today().date()
date_max = df["Datum"].max().date() if df is not None and not df.empty else datetime.today().date()

years = sorted(df["Datum"].dropna().dt.year.unique()) if df is not None and not df.empty else []
selected_year = st.selectbox("Vyberte rok:", ["Vlastní rozsah"] + years)

if selected_year == "Vlastní rozsah":
    date_from = st.date_input("Datum od:", date_min, min_value=date_min, max_value=date_max)
    date_to = st.date_input("Datum do:", date_max, min_value=date_min, max_value=date_max)
else:
    date_from = datetime(selected_year, 1, 1).date()
    date_to = datetime(selected_year, 12, 31).date()

# 3) Filtr aktivity
#activity_list = ["Vše"]
#if df is not None and not df.empty and activity_column in df.columns:
#    unique_activities = sorted(set(df[activity_column].dropna().unique()))
#    activity_list += unique_activities
#selected_activity = st.selectbox("Vyber aktivitu (výchozí = Vše):", activity_list)

# ------------------
# Filtrování dat
# ------------------

# Napřed vyfiltrujeme podle data
filtered_data = df[(df["Datum"].dt.date >= date_from) & (df["Datum"].dt.date <= date_to)]

# Pak podle druhu
if selected_species == "Vyber":
    # prázdná tabulka
    filtered_data = filtered_data.iloc[0:0]
elif selected_species != "Vše":
    filtered_data = filtered_data[filtered_data[species_column] == selected_species]


# ------------------
# GRAF 1: Počet pozorovaných druhů v jednotlivých letech
# ------------------
if df is not None and not df.empty:
    yearly_counts = df.groupby(df["Datum"].dt.year)[species_column].nunique().reset_index()
else:
    yearly_counts = pd.DataFrame(columns=["Datum", "Počet druhů"])
yearly_counts.rename(columns={"Datum": "Rok", species_column: "Počet druhů"}, inplace=True)
fig_yearly = px.bar(yearly_counts, x="Rok", y="Počet druhů", title="Celkový počet pozorovaných druhů podle roku", color_discrete_sequence=["green"])
fig_yearly.update_xaxes(type='category')

if show_bar_yearly:
    st.write("### Počet pozorovaných druhů v jednotlivých letech")
    st.plotly_chart(fig_yearly)

# ------------------
# GRAF 2: Počet pozorování vybraného druhu v jednotlivých letech
# ------------------
years_df = pd.DataFrame({"Rok": years})
if selected_species not in ["Vyber", "Vše"]:
    yearly_species_counts = df[df[species_column] == selected_species].groupby(df["Datum"].dt.year).size().reset_index(name="Počet pozorování")
    yearly_species_counts = years_df.merge(yearly_species_counts, left_on="Rok", right_on="Datum", how="left").fillna(0)
    yearly_species_counts["Počet pozorování"] = yearly_species_counts["Počet pozorování"].astype(int)
    fig_species_yearly = px.bar(yearly_species_counts, x="Rok", y="Počet pozorování", title=f"Počet pozorování druhu {selected_species} podle roku", color_discrete_sequence=["purple"])
    fig_species_yearly.update_xaxes(type='category')
    fig_species_yearly.update_yaxes(dtick=max(1, yearly_species_counts["Počet pozorování"].max() // 5))
    if show_bar_species_yearly:
        st.write(f"### Počet pozorování druhu {selected_species} v jednotlivých letech")
        st.plotly_chart(fig_species_yearly)

# ------------------
# GRAF 3: 10 nejčastěji pozorovaných druhů (koláč)
# ------------------
filtered_pie_data = df[(df["Datum"].dt.date >= date_from) & (df["Datum"].dt.date <= date_to)]
top_species = filtered_pie_data[species_column].value_counts().nlargest(10).reset_index()
top_species.columns = ["Druh", "Počet pozorování"]
fig_pie = px.pie(top_species, names="Druh", values="Počet pozorování", title="Podíl 10 nejčastějších druhů", hole=0.3)

if show_pie_top_species:
    st.write("### 10 nejčastěji pozorovaných druhů")
    st.plotly_chart(fig_pie)

# ------------------
# MAPA S BODY
# ------------------
if not filtered_data.empty and filtered_data[["Zeměpisná šířka", "Zeměpisná délka"]].notna().all().all():
    map_center = [filtered_data["Zeměpisná šířka"].mean(), filtered_data["Zeměpisná délka"].mean()]
else:
    map_center = [49.8175, 15.4730]

m = folium.Map(location=map_center, zoom_start=6)

if not filtered_data.empty:
    from folium.plugins import MarkerCluster
    marker_cluster = MarkerCluster().add_to(m)
    for _, row in filtered_data.dropna(subset=["Zeměpisná šířka", "Zeměpisná délka"]).iterrows():
        folium.Marker(
            location=[row["Zeměpisná šířka"], row["Zeměpisná délka"]],
            popup=f"{row['Místo pozorování']} ({row['Počet']} jedinců)",
        ).add_to(marker_cluster)

if show_map_markers:
    st.write("### Mapa pozorování")
    folium_static(m)

# ------------------
# HEATMAPA POZOROVÁNÍ
# ------------------
heat_map = folium.Map(location=map_center, zoom_start=6)
if not filtered_data.empty:
    heat_df = filtered_data.dropna(subset=["Zeměpisná šířka", "Zeměpisná délka", "Počet"])
    heat_agg = heat_df.groupby(["Zeměpisná šířka", "Zeměpisná délka"])['Počet'].sum().reset_index()
    heat_data = heat_agg.values.tolist()
    HeatMap(heat_data, radius=10).add_to(heat_map)

if show_map_heat:
    st.write("### Heatmapa pozorování")
    folium_static(heat_map)

# ------------------
# GRAFY PODLE MĚSÍCŮ
# ------------------
if not filtered_data.empty:
    filtered_data["Měsíc"] = filtered_data["Datum"].dt.month.map({1: "Leden", 2: "Únor", 3: "Březen", 4: "Duben", 5: "Květen", 6: "Červen", 7: "Červenec", 8: "Srpen", 9: "Září", 10: "Říjen", 11: "Listopad", 12: "Prosinec"})
    monthly_counts = filtered_data.groupby("Měsíc").agg({"Počet": "sum", "Datum": "count"}).reset_index()
    monthly_counts.rename(columns={"Datum": "Počet pozorování", "Počet": "Počet jedinců"}, inplace=True)
    all_months_df = pd.DataFrame({"Měsíc": ["Leden","Únor","Březen","Duben","Květen","Červen","Červenec","Srpen","Září","Říjen","Listopad","Prosinec"]})
    monthly_counts = all_months_df.merge(monthly_counts, on="Měsíc", how="left").fillna(0)
    monthly_counts["Počet pozorování"] = monthly_counts["Počet pozorování"].astype(int)
    monthly_counts["Počet jedinců"] = monthly_counts["Počet jedinců"].astype(int)

    fig1 = px.bar(monthly_counts, x="Měsíc", y="Počet pozorování", title="Počet pozorování podle měsíců", color_discrete_sequence=["blue"])
    fig1.update_yaxes(dtick=max(1, monthly_counts["Počet pozorování"].max() // 5))
    fig2 = px.bar(monthly_counts, x="Měsíc", y="Počet jedinců", title="Počet jedinců podle měsíců", color_discrete_sequence=["red"])
    fig2.update_yaxes(dtick=max(1, monthly_counts["Počet jedinců"].max() // 5))

    if show_bar_monthly_obs:
        st.write("### Počet pozorování podle měsíců")
        st.plotly_chart(fig1)

    if show_bar_monthly_count:
        st.write("### Počet jedinců podle měsíců")
        st.plotly_chart(fig2)

# Výpis dat s podporou stránkování
st.write(f"### Pozorování druhu: {selected_species}")
filtered_data_display = filtered_data.copy()
filtered_data_display["Počet"] = filtered_data_display["Počet"].apply(lambda x: 'x' if pd.isna(x) or x == '' else int(x))
filtered_data_display["Datum"] = filtered_data_display["Datum"].apply(lambda x: x.strftime('%d. %m. %Y') if pd.notna(x) else '')
st.write(filtered_data_display[["Datum", "Místo pozorování", "Počet", "Odkaz"]].to_html(escape=False), unsafe_allow_html=True)
