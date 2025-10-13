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


# [STREAMLIT] ADJUST PADDING
padding = """
    <style>
    .block-container {
        padding-top: 2rem;
        padding-bottom: 0rem;
    }
    </style>
    """
st.markdown(padding, unsafe_allow_html=True)

# [LEAFMAP] ADD MAP BORDER
map_border_style = """
<style>
iframe {
    border: 1px solid white !important;
    box-sizing: border-box;
}
</style>
"""
st.markdown(map_border_style, unsafe_allow_html=True)

# [STREAMLIT] METRIC VALUE SIZE
metric_value = """
<style>
div[data-testid="stMetricValue"] {
    font-size: 1.6rem;
    font-weight: 800;
}
</style>
"""
st.markdown(metric_value, unsafe_allow_html=True)

# [STREAMLIT] METRIC BACKGROUND COLOR
metric_background = """
<style>
div[data-testid="stMetric"] {
    background: white;
    border-radius: 0.5rem;
    padding-top: 0.6rem;
    padding-bottom: 0.6rem;
    padding-left: 1rem;
    padding-right: 1rem;
}
</style>
"""
st.markdown(metric_background, unsafe_allow_html=True)


# ---- LOAD DATA ----
@st.cache_data
def load_data():
    cdo_barangays = pd.read_csv("cdo_barangays.csv")
    cdo_barangays["Geometry"] = cdo_barangays["Geometry"].apply(wkt.loads)
    gdf_barangays = gpd.GeoDataFrame(cdo_barangays, geometry="Geometry", crs="EPSG:4326")

    forecasts = pd.read_csv("all_models_forecasts.csv")
    forecasts["Date"] = pd.to_datetime(forecasts["Date"])
    merged = forecasts.merge(gdf_barangays, on="Barangay", how="left")
    merged_gdf = gpd.GeoDataFrame(merged, geometry="Geometry", crs="EPSG:4326")
    return merged_gdf

merged_all = load_data()

# ---- DATA PREP ----
merged_all["Year"] = merged_all["Date"].dt.year
merged_all["Week"] = merged_all["Date"].dt.isocalendar().week.astype(int)

# ---- DASHBOARD LAYOUT ----
col1, col2 = st.columns(2)

# ---- LEFT COLUMN ----
with col1:
    # --- DEFAULTS ---
    available_years = sorted(merged_all["Year"].unique())
    default_year_index = available_years.index(2025) if 2025 in available_years else len(available_years) - 1
    default_model_key = "varmax" if "varmax" in merged_all["Model"].unique() else merged_all["Model"].unique()[0]

    # --- INITIAL FILTER ---
    selected_year = available_years[default_year_index]
    selected_model = default_model_key
    
    model_data = merged_all[merged_all["Model"] == selected_model]
    year_data = model_data[model_data["Year"] == selected_year].copy()
    available_weeks = sorted(year_data["Week"].unique())
    selected_week = min(available_weeks)

    week_data = year_data[year_data["Week"] == selected_week].copy()

    if "Date" in week_data.columns:
        week_data["Date"] = week_data["Date"].astype(str)

    # --- ENSURE NUMERIC ---
    week_data["Forecast_Cases"] = pd.to_numeric(week_data["Forecast_Cases"], errors="coerce").fillna(0)
    # week_data["Forecast_vis"] = week_data["Forecast_Cases"].astype(float)

    # --- MAP SECTION ---
    bounds = week_data.total_bounds if not week_data.empty else [124.5, 8.4, 124.8, 8.6]
    buffer = 0.05
    m = leafmap.Map(
        location=[8.48, 124.65],
        zoom_start=11,
        min_zoom=10,
        max_zoom=18,
        tiles="CartoDB.PositronNoLabels",
        control_scale=False,
        layer_control=False,
    )

    # --- COLOR SCALE SETUP ---
    vmin = week_data["Forecast_Cases"].min()
    vmax = week_data["Forecast_Cases"].max()
    vmax = vmax if vmax > 0 else 1

    colormap = cm.LinearColormap(
        colors=["#ffffcc", "#ffeda0", "#fed976", "#feb24c",
                "#fd8d3c", "#f03b20", "#bd0026", "#800026"],
        vmin=vmin,
        vmax=vmax,
        caption="Forecasted Dengue Cases"
    )

    def get_color(value):
        try:
            if pd.isna(value):
                return "#d9d9d9"
            return colormap(value)
        except Exception:
            return "#d9d9d9"

    # --- STYLE FUNCTION FOR GEOJSON ---
    def style_function(feature):
        value = feature["properties"].get("Forecast_Cases", 0)
        return {
            "fillColor": get_color(value),
            "fillOpacity": 1.0,
            "color": "black",
            "weight": 1.0,
            "opacity": 1.0
        }

    # --- TOOLTIP FORMAT ---
    week_data = week_data.copy()
    week_data["Forecast_Cases_str"] = week_data["Forecast_Cases"].apply(lambda x: f"{x:.1f}")
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

    # --- FILTER CONTROLS ---
    filter_col1, filter_col2, filter_col3 = st.columns([1, 1, 2])
    with filter_col1:
        selected_year = st.selectbox("Select Year", available_years, index=default_year_index)
    with filter_col2:
        model_name_map = {
            "linear_regression": "Linear Regression",
            "varmax": "VARMAX",
            "random_forest": "Random Forest",
            "xgboost": "XGBoost"
        }
        model_display_names = [model_name_map[m] for m in merged_all["Model"].unique() if m in model_name_map]
        selected_model_display = st.selectbox("Select Model", model_display_names, 
                                              index=model_display_names.index(model_name_map[default_model_key]))
        selected_model = [k for k, v in model_name_map.items() if v == selected_model_display][0]
    with filter_col3:
        model_data = merged_all[merged_all["Model"] == selected_model]
        year_data = model_data[model_data["Year"] == selected_year].copy()
        available_weeks = sorted(year_data["Week"].unique())
        selected_week = st.select_slider("Select Week", options=available_weeks, value=max(available_weeks))

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

    table_df = week_data[['Barangay', 'Forecast_Cases', 'Risk_Level']].copy()
    table_df = table_df.rename(columns={"Forecast_Cases": "Forecasted Cases", "Risk_Level": "Risk Level"})
    table_df = table_df.sort_values(by='Forecasted Cases', ascending=False).reset_index(drop=True)

    def color_forecast(val):
        if pd.isna(val):
            return 'background-color: #d9d9d9; color: black'
        
        color = colormap(val)
        
        color_hex = color.lstrip('#')
        r, g, b = int(color_hex[0:2], 16), int(color_hex[2:4], 16), int(color_hex[4:6], 16)
        brightness = (r*299 + g*587 + b*114) / 1000
        
        text_color = "white" if brightness < 128 else "black"
        return f'background-color: {color}; color: {text_color}; font-weight: bold'
    
    styled_table = table_df.style.applymap(color_forecast, subset=['Forecasted Cases'])
    st.dataframe(styled_table, width='stretch', height=500)



