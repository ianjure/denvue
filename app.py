import streamlit as st
import geopandas as gpd
import pandas as pd
from shapely import wkt

import folium
import leafmap.foliumap as leafmap
import branca.colormap as cm
import json

# ---- PAGE CONFIG ----
st.set_page_config(page_title="Denvue Dashboard", layout="wide")

# ---- LOAD DATA ----
@st.cache_data
def load_data():
    cdo_barangays = pd.read_csv("cdo_barangays.csv")
    cdo_barangays["Geometry"] = cdo_barangays["Geometry"].apply(wkt.loads)
    gdf_barangays = gpd.GeoDataFrame(cdo_barangays, geometry="Geometry", crs="EPSG:4326")

    forecasts = pd.read_csv("varmax_forecasts.csv")
    forecasts["Date"] = pd.to_datetime(forecasts["Date"])
    merged = forecasts.merge(gdf_barangays, on="Barangay", how="left")
    merged_gdf = gpd.GeoDataFrame(merged, geometry="Geometry", crs="EPSG:4326")
    return merged_gdf

merged_all = load_data()

# ---- DATA PREP ----
merged_all["Year"] = merged_all["Date"].dt.year
merged_all["Week"] = merged_all["Date"].dt.isocalendar().week.astype(int)

# ---- PAGE TITLE ----
st.markdown("## 🦟 Denvue Forecast Dashboard (2025–2027)")

# ---- DASHBOARD LAYOUT ----
col1, col2 = st.columns([2.5, 1])

# ---- LEFT COLUMN ----
with col1:
    # --- YEAR SELECTOR ---
    available_years = sorted(merged_all["Year"].unique())
    selected_year = st.selectbox("📅 Select Year", available_years, index=len(available_years)-1)

    year_data = merged_all[merged_all["Year"] == selected_year]
    available_weeks = sorted(year_data["Week"].unique())
    selected_week = st.slider("🗓️ Select Week", min_value=min(available_weeks), max_value=max(available_weeks), value=max(available_weeks))

    # --- FILTER FOR SELECTED WEEK ---
    week_data = year_data[year_data["Week"] == selected_week].copy()

    # --- MAP VISUALIZATION RANGE ---
    vmin, vmax = 0, week_data["Forecast_Cases"].max()
    week_data["Forecast_vis"] = week_data["Forecast_Cases"].clip(vmin, vmax)

    # --- MAP SECTION ---
    bounds = week_data.total_bounds
    buffer = 0.05
    m = leafmap.Map(
        location=[8.48, 124.65],
        zoom_start=11,
        min_zoom=10,
        max_zoom=18,
        tiles="CartoDB.PositronNoLabels",
        max_bounds=True,
        min_lat=bounds[1] - buffer,
        max_lat=bounds[3] + buffer,
        min_lon=bounds[0] - buffer,
        max_lon=bounds[2] + buffer,
        control_scale=False,
        search_control=False,
        layer_control=False,
    )

    # --- COLOR BINS AND PALETTE ---
    bins = [0, 5, 10, 25, 50, 75, 100, 200, vmax]
    colors = ['#ffffcc', '#ffeda0', '#fed976', '#feb24c', '#fd8d3c', '#f03b20', '#bd0026', '#800026']

    def get_color(value):
        for i, b in enumerate(bins[1:]):
            if value < b:
                return colors[i]
        return colors[-1]

    colormap = cm.LinearColormap(colors=colors, vmin=vmin, vmax=vmax, caption="Forecasted Dengue Cases")

    def style_function(feature):
        value = feature['properties']['Forecast_vis']
        return {
            'fillColor': get_color(value),
            'fillOpacity': 0.75,
            'color': 'black',
            'weight': 1.0,
            'opacity': 0.9
        }

    week_data['Forecast_Cases_str'] = week_data['Forecast_Cases'].apply(lambda x: f"{x:.1f}")
    geojson_data = json.loads(week_data.to_json())

    folium.GeoJson(
        data=geojson_data,
        style_function=style_function,
        tooltip=folium.GeoJsonTooltip(
            fields=["Barangay", "Forecast_Cases_str", "Risk_Level"],
            aliases=["Barangay:", "Forecasted Cases:", "Risk Level:"],
            style=("font-weight: bold; font-size: 12px;"),
            sticky=True
        ),
        name="Forecasted Cases",
    ).add_to(m)

    colormap.add_to(m)

    st.subheader(f"🗺️ Dengue Forecast Map — Week {selected_week}, {selected_year}")
    m.to_streamlit(height=580, width=None, add_layer_control=False)

# ---- RIGHT COLUMN ----
with col2:
    st.subheader("🔍 Summary Metrics")

    avg_cases = week_data['Forecast_Cases'].mean().round(2)
    max_row = week_data.loc[week_data['Forecast_Cases'].idxmax()]
    min_row = week_data.loc[week_data['Forecast_Cases'].idxmin()]

    m1, m2, m3 = st.columns(3)
    m1.metric("Average Forecasted Cases", f"{avg_cases:.2f}")
    m2.metric("Highest Risk Barangay", max_row['Barangay'])
    m3.metric("Lowest Risk Barangay", min_row['Barangay'])

    # ---- TABLE SECTION ----
    st.subheader("📍Barangays by Forecasted Cases")

    table_df = week_data[['Barangay', 'Forecast_Cases', 'Risk_Level']].sort_values(by='Forecast_Cases', ascending=False).reset_index(drop=True)
    table_df['Forecast_Cases'] = table_df['Forecast_Cases'].map(lambda x: f"{x:.1f}")
    table_df = table_df.rename(columns={
        "Barangay": "Barangay",
        "Forecast_Cases": "Forecasted Cases",
        "Risk_Level": "Risk Level"
    })

    def color_forecast(val):
        try:
            val_float = float(val)
            color = get_color(val_float)
            dark_colors = ['#f03b20', '#bd0026', '#800026']
            text_color = "white" if color in dark_colors else "black"
            return f'background-color: {color}; color: {text_color}; font-weight: bold'
        except:
            return ''

    styled_table = table_df.style.applymap(color_forecast, subset=['Forecasted Cases'])
    st.dataframe(styled_table, use_container_width=True, height=400)
