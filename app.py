import streamlit as st
from streamlit_float import *
from PIL import Image

import geopandas as gpd
import pandas as pd
from shapely import wkt

from datetime import datetime, timedelta

import folium
import leafmap.foliumap as leafmap
from branca.element import Template, MacroElement, Element
import numpy as np
import json

# PAGE CONFIG
icon = Image.open("icon.png")
st.set_page_config(page_title="Denvue Dashboard", layout="wide", page_icon=icon)
st.logo(image="logo.png", size="large")
float_init()

# [STREAMLIT] ADJUST PADDING
padding = """
<style>
.block-container {
    padding-top: -5rem;
    padding-bottom: 2.5rem;
}
</style>
"""
st.markdown(padding, unsafe_allow_html=True)

# [STREAMLIT] TOOLBAR BACKGROUND
toolbar_bg = """
<style>
div[data-testid="stToolbar"] {
    background-color: #698C6E;
}
</style>
"""
st.markdown(toolbar_bg, unsafe_allow_html=True)

# [STREAMLIT] HIDE MENU
hide_menu = """
<style>
div[data-testid="stToolbarActions"] {
    display: none;
}
span[data-testid="stMainMenu"] {
    display: none;
}
div[data-testid="stDecoration"] {
    visibility: hidden;
    height: 0%;
    position: fixed;
}
div[data-testid="stStatusWidget"] {
    visibility: hidden;
    height: 0%;
    position: fixed;
}
</style>
"""
st.markdown(hide_menu, unsafe_allow_html=True)

# [STREAMLIT] ADJUST HEADER
header = """
<style>
[data-testid="stHeader"] {
    z-index: 1;
}
</style>
    """
st.markdown(header, unsafe_allow_html=True)

# [STREAMLIT] HEADER COLOR
header_color = """
<style>
div[data-testid="stHeadingWithActionElements"] {
    color: #234528;
}
</style>
"""
st.markdown(header_color, unsafe_allow_html=True)

# [STREAMLIT] REMOVE HEADER ACTION ELEMENT
header_action = """
<style>
[data-testid="stHeaderActionElements"] {
    display: none;
}
</style>
"""
st.markdown(header_action, unsafe_allow_html=True)

# [STREAMLIT] BOTTOM ALIGN CONTENT
bottom_align = """
<style>
.stColumn.st-emotion-cache-1wpb1x8.e1wguzas2 > .stVerticalBlock.st-emotion-cache-wfksaw.e1wguzas3 {
    display: flex;
    justify-content: flex-end;
    align-items: flex-end;
}
</style>
"""
st.markdown(bottom_align, unsafe_allow_html=True)

# [LEAFMAP] ADD MAP BORDER
map_border_style = """
<style>
iframe {
    border: 1px solid #E0E0E0 !important;
    box-sizing: border-box;
    border-radius: 0.5rem;
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

# [STREAMLIT] METRIC STYLE
metric_style = """
<style>
div[data-testid="stMetric"] {
    color: #234528,
    background: white;
    border: 1px solid #E0E0E0;
    border-radius: 0.5rem;
    padding-top: 0.6rem;
    padding-bottom: 0.6rem;
    padding-left: 1rem;
    padding-right: 1rem;
}
</style>
"""
st.markdown(metric_style, unsafe_allow_html=True)

# LOAD DATA
@st.cache_data
def load_data():
    cdo_barangays = pd.read_csv("cdo_barangays.csv")
    cdo_barangays["Geometry"] = cdo_barangays["Geometry"].apply(wkt.loads)
    gdf_barangays = gpd.GeoDataFrame(cdo_barangays, geometry="Geometry", crs="EPSG:4326")

    forecasts = pd.read_csv("all_models_forecasts.csv")
    forecasts["Date"] = pd.to_datetime(forecasts["Date"])
    merged = forecasts.merge(gdf_barangays, on="Barangay", how="left")
    merged_all = gpd.GeoDataFrame(merged, geometry="Geometry", crs="EPSG:4326")
    
    return gdf_barangays, merged_all

gdf_barangays, merged_all = load_data()

# SESSION STATE
available_years = sorted(merged_all["Year"].unique()) if "Year" in merged_all.columns else sorted(merged_all["Date"].dt.year.unique())
if "Year" not in merged_all.columns:
    merged_all["Year"] = merged_all["Date"].dt.year
merged_all["Week"] = merged_all["Date"].dt.isocalendar().week.astype(int)

model_list = merged_all["Model"].unique()
default_model = "random_forest" if "random_forest" in model_list else model_list[0]
default_year = 2025 if 2025 in available_years else available_years[-1]

st.session_state.setdefault("selected_model", default_model)
st.session_state.setdefault("selected_year", default_year)

year_weeks = sorted(merged_all[merged_all["Year"] == st.session_state.selected_year]["Week"].unique())
if "selected_week" not in st.session_state:
    st.session_state.selected_week = min(year_weeks) if year_weeks else 1

# FILTER DATA
filtered_data = merged_all[
    (merged_all["Model"] == st.session_state.selected_model)
    & (merged_all["Year"] == st.session_state.selected_year)
    & (merged_all["Week"] == st.session_state.selected_week)
].copy()

filtered_data["Forecast_Cases"] = pd.to_numeric(filtered_data["Forecast_Cases"], errors="coerce").fillna(0)
filtered_data["Confidence"] = (filtered_data["Confidence"] * 100).round(1).astype(str) + "%"

# DASHBOARD LAYOUT
col1, col2 = st.columns(2)

# LEFT COLUMN
with col1:
    with st.container():
        # GET THE ACTUAL DATE RANGE
        start_date = datetime.fromisocalendar(st.session_state.selected_year, st.session_state.selected_week, 1)  # Monday
        end_date = datetime.fromisocalendar(st.session_state.selected_year, st.session_state.selected_week, 7)    # Sunday
        date_range_str = f"{start_date.strftime('%b %d, %Y')} - {end_date.strftime('%b %d, %Y')}"

        # MAP SECTION
        title, date = st.columns(2)
        with title:
            st.write(f"#### **Dengue Risk Distribution Map**")
        with date:
            st.markdown(
                f"""
                <div style='display: flex; height: 100%; align-items: flex-end; justify-content: flex-end;'>
                    <h6 style='margin: 0;'>{date_range_str}</h6>
                </div>
                """,
                unsafe_allow_html=True
            )
        bounds = filtered_data.total_bounds
        buffer = 0.05
        map = leafmap.Map(
            location=[8.48, 124.65],
            zoom_start=10,
            min_zoom=10,
            max_zoom=18,
            tiles="CartoDB.PositronNoLabels",
            max_bounds=True,
            min_lat=bounds[1]-buffer,
            max_lat=bounds[3]+buffer,
            min_lon=bounds[0]-buffer,
            max_lon=bounds[2]+buffer,
            attribution_control=False,
            draw_control=False,
            measure_control=False,
            fullscreen_control=False,
            locate_control=False,
            minimap_control=False,
            scale_control=False,
            layer_control=False,
            search_control=False,
        )
        
        risk_colors = {
            "Low": "#E9F3F2",
            "Moderate": "#F3B705",
            "High": "#F17404",
            "Critical": "#D9042C"
        }
        
        def get_color(risk_level):
            if pd.isna(risk_level):
                return "#E9F3F2"
            return risk_colors.get(risk_level, "#E9F3F2")
        
        def style_function(feature):
            risk_level = feature["properties"].get("Risk_Level", None)
            return {
                "fillColor": get_color(risk_level),
                "fillOpacity": 1.0,
                "color": "#686A6AFF",
                "weight": 1.0,
                "opacity": 1.0,
            }
        
        filtered_data["Forecast_Cases_str"] = filtered_data["Forecast_Cases"].apply(lambda x: f"{x}")
        geojson_data = json.loads(filtered_data[["Geometry", "Barangay", "Forecast_Cases_str", "Confidence", "Risk_Level"]].to_json())
        
        # ADD GEOJSON LAYER
        geojson = folium.GeoJson(
            data=geojson_data,
            style_function=style_function,
            tooltip=folium.GeoJsonTooltip(
                fields=["Barangay", "Forecast_Cases_str", "Confidence", "Risk_Level"],
                aliases=["Barangay:", "Forecast Cases:", "Confidence:", "Risk Level:"],
                style=("font-weight: bold; font-size: 12px;"),
                sticky=True,
            ),
            name="Forecast Cases",
            highlight_function=lambda x: {'weight': 3, 'color': 'green'},
            zoom_on_click=True
        ).add_to(map)

        # ADD BARANGAY NAME LAYER
        barangay_labels = folium.FeatureGroup(name="Barangay Labels", show=False)
        gdf_barangays["lon"] = gdf_barangays.geometry.centroid.x
        gdf_barangays["lat"] = gdf_barangays.geometry.centroid.y
        
        for idx, row in gdf_barangays.iterrows():
            folium.map.Marker(
                location=[row["lat"], row["lon"]],
                icon=folium.DivIcon(
                    html=f'<div style="font-size:6pt;font-weight:bold">{row["Barangay"]}</div>'
                )
            ).add_to(barangay_labels)
        
        barangay_labels.add_to(map)
        folium.LayerControl().add_to(map)
        
        # CUSTOM LEGEND
        legend_html = """
        {% macro html(this, kwargs) %}
        <div style="
            position: fixed; 
            bottom: 10px; left: 10px; width: 120px; 
            z-index:9999; font-size:14px;
            background-color: white;
            border:2px solid #ABABAB;
            border-radius:8px;
            padding: 10px;
        ">
            <b>Risk Level</b><br>
            <i style="background:#E9F3F2;width:18px;height:18px;float:left;margin-right:8px;border:1px solid #ccc;"></i>Low<br>
            <i style="background:#F3B705;width:18px;height:18px;float:left;margin-right:8px;border:1px solid #ccc;"></i>Moderate<br>
            <i style="background:#F17404;width:18px;height:18px;float:left;margin-right:8px;border:1px solid #ccc;"></i>High<br>
            <i style="background:#D9042C;width:18px;height:18px;float:left;margin-right:8px;border:1px solid #ccc;"></i>Critical<br>
        </div>
        {% endmacro %}
        """
        legend_macro = MacroElement()
        legend_macro._template = Template(legend_html)
        map.get_root().add_child(legend_macro)

        # SHOW MAP
        map.to_streamlit(height=450, width=None, add_layer_control=False)

        # FILTERS CONTROLS
        filter_col1, filter_col2 = st.columns([1, 3])
        
        with filter_col1:
            selected_year = st.selectbox(
                "Select Year",
                available_years,
                index=available_years.index(st.session_state.selected_year)
            )
        
        with filter_col2:
            available_weeks = sorted(merged_all[merged_all["Year"] == selected_year]["Week"].unique())
            selected_week = st.select_slider(
                "Select Week",
                available_weeks, 
                value=st.session_state.selected_week
            )
        
        # UPDATE SESSION STATE ON CHANGE
        if selected_year != st.session_state.selected_year or selected_week != st.session_state.selected_week:
            st.session_state.selected_year = selected_year
            st.session_state.selected_week = selected_week
            st.rerun()
            
# RIGHT COLUMN
with col2:
    # METRICS SECTION
    st.write("#### **Summary Metrics**")
    total_cases = filtered_data['Forecast_Cases'].sum()

    risk_order = {"Low": 1, "Moderate": 2, "High": 3, "Critical": 4}
    filtered_data["Risk_Code"] = filtered_data["Risk_Level"].map(risk_order)
    
    max_row = filtered_data.loc[filtered_data["Risk_Code"].idxmax()]
    min_row = filtered_data.loc[filtered_data["Risk_Code"].idxmin()]

    m1, m2, m3 = st.columns(3)
    m1.metric("Total Forecasted Cases", f"{total_cases}")
    m2.metric("Highest Risk Barangay", max_row['Barangay'])
    m3.metric("Lowest Risk Barangay", min_row['Barangay'])

    # TABLE SECTION
    st.write("#### **Risk Ranking by Barangay**")

    table_df = filtered_data[['Barangay', 'Forecast_Cases', 'Confidence', 'Risk_Level']].copy()
    table_df = table_df.rename(columns={"Forecast_Cases": "Forecast Cases", "Confidence": "Confidence", "Risk_Level": "Risk Level"})
    table_df["Forecast Cases"] = table_df["Forecast Cases"].astype(str)
    
    risk_order = ["Low", "Moderate", "High", "Critical"]
    table_df["Risk Level"] = pd.Categorical(table_df["Risk Level"], categories=risk_order, ordered=True)
    table_df = table_df.sort_values(by=['Risk Level', 'Forecast Cases'], ascending=[False, False]).reset_index(drop=True)

    def color_forecast(val):
        if pd.isna(val):
            return 'background-color: #E9F3F2; color: black'
        color = risk_colors.get(val, "#E9F3F2")
        if color == "#E9F3F2" or color == "#F3B705":
            text_color = "black"
        else:
            text_color = "white"
        return f'background-color: {color}; color: {text_color}; font-weight: bold'
    
    styled_table = table_df.style.applymap(color_forecast, subset=['Risk Level'])
    st.dataframe(styled_table, width='stretch', height=380)

# MODEL OPTIONS
@st.dialog("Model Options")
def open_model_options():
    model_name_map = {
        "linear_regression": "Linear Regression",
        "varmax": "VARMAX",
        "random_forest": "Random Forest",
        "xgboost": "XGBoost",
    }
    model_display = [model_name_map[m] for m in merged_all["Model"].unique() if m in model_name_map]
    model_to_key = {v: k for k, v in model_name_map.items()}

    selected_model_display = st.selectbox(
        "Select Model",
        model_display,
        index=model_display.index(model_name_map[st.session_state.selected_model]),
    )
    selected_model = model_to_key[selected_model_display]

    # UPDATE SESSION STATE ON CHANGE
    if selected_model != st.session_state.selected_model:
        st.session_state.selected_model = selected_model
        st.rerun()

button_container = st.container()
with button_container:
    if st.button("⚙️"):
        open_model_options()
    
button_css = float_css_helper(width="3rem", height="3rem", right="0.8rem", top="0.6rem", transition=0)
button_container.float(button_css)











