import streamlit as st
import geopandas as gpd
import pandas as pd
from shapely import wkt

import folium
import leafmap.foliumap as leafmap
from branca.element import Template, MacroElement
import json

# PAGE CONFIG
st.set_page_config(page_title="Denvue Dashboard", layout="wide")
st.logo(image="logo.png", size="large")

# [STREAMLIT] ADJUST PADDING
padding = """
    <style>
    .block-container {
        padding-top: 0rem;
        padding-bottom: 4rem;
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

# [LEAFMAP] ADD MAP BORDER
map_border_style = """
<style>
iframe {
    border: 1px solid white !important;
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

# LOAD DATA
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

# DATA PREPARATION
merged_all["Year"] = merged_all["Date"].dt.year
merged_all["Week"] = merged_all["Date"].dt.isocalendar().week.astype(int)
merged_all["Date"] = merged_all["Date"].astype(str)

# DASHBOARD LAYOUT
col1, col2 = st.columns(2)

# LEFT COLUMN
with col1:
    with st.container():
        # --- DEFAULTS ---
        available_years = sorted(merged_all["Year"].unique())
        default_year = 2025 if 2025 in available_years else available_years[-1]
        default_model = "varmax" if "varmax" in merged_all["Model"].unique() else merged_all["Model"].unique()[0]

        # SESSION STATE INITIALIZATION
        if "selected_year" not in st.session_state:
            st.session_state.selected_year = default_year
        if "selected_model" not in st.session_state:
            st.session_state.selected_model = default_model
        if "selected_week" not in st.session_state:
            default_weeks = sorted(
                merged_all[merged_all["Year"] == st.session_state.selected_year]["Week"].unique()
            )
            st.session_state.selected_week = min(default_weeks) if default_weeks else 1

        # FILTER DATA
        filtered_data = merged_all[
            (merged_all["Model"] == st.session_state.selected_model)
            & (merged_all["Year"] == st.session_state.selected_year)
            & (merged_all["Week"] == st.session_state.selected_week)
        ].copy()

        filtered_data["Forecast_Cases"] = pd.to_numeric(filtered_data["Forecast_Cases"], errors="coerce").fillna(0)

        # MAP SECTION
        st.write(f"#### **Dengue Risk Distribution Map**")
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
            "Low Risk": "#ffffcc",
            "Medium Risk": "#fd8d3c",
            "High Risk": "#bd0026"
        }
        
        def get_color(risk_level):
            if pd.isna(risk_level):
                return "#d9d9d9"
            return risk_colors.get(risk_level, "#d9d9d9")
        
        def style_function(feature):
            risk_level = feature["properties"].get("Risk_Level", None)
            return {
                "fillColor": get_color(risk_level),
                "fillOpacity": 1.0,
                "color": "black",
                "weight": 1.0,
                "opacity": 1.0,
            }
        
        filtered_data["Forecast_Cases_str"] = filtered_data["Forecast_Cases"].apply(lambda x: f"{x:.1f}")
        geojson_data = json.loads(filtered_data.to_json())
        
        # ADD GEOJSON LAYER
        folium.GeoJson(
            data=geojson_data,
            style_function=style_function,
            tooltip=folium.GeoJsonTooltip(
                fields=["Barangay", "Forecast_Cases_str", "Risk_Level"],
                aliases=["Barangay:", "Forecasted Cases:", "Risk Level:"],
                style=("font-weight: bold; font-size: 12px;"),
                sticky=True,
            ),
            name="Forecasted Cases",
        ).add_to(map)
        
        # CUSTOM LEGEND
        legend_html = """
        {% macro html(this, kwargs) %}
        <div style="
            position: fixed; 
            bottom: 10px; left: 10px; width: 180px; 
            z-index:9999; font-size:14px;
            background-color: white;
            border:2px solid grey;
            border-radius:8px;
            padding: 10px;
        ">
            <b>Risk Level</b><br>
            <i style="background:#ffffcc;width:18px;height:18px;float:left;margin-right:8px;"></i>Low Risk<br>
            <i style="background:#fd8d3c;width:18px;height:18px;float:left;margin-right:8px;"></i>Moderate Risk<br>
            <i style="background:#bd0026;width:18px;height:18px;float:left;margin-right:8px;"></i>High Risk<br>
        </div>
        {% endmacro %}
        """
        legend = MacroElement()
        legend._template = Template(legend_html)
        map.get_root().add_child(legend)
        map.to_streamlit(height=450, width=None, add_layer_control=False)

        # FILTERS CONTROLS
        filter_col1, filter_col2, filter_col3 = st.columns([1, 1, 2])

        with filter_col1:
            selected_year = st.selectbox(
                "Select Year",
                available_years,
                index=available_years.index(st.session_state.selected_year)
            )
        
        with filter_col2:
            model_name_map = {
                "linear_regression": "Linear Regression",
                "varmax": "VARMAX",
                "random_forest": "Random Forest",
                "xgboost": "XGBoost",
            }
            model_display_names = [
                model_name_map[m] for m in merged_all["Model"].unique() if m in model_name_map
            ]
            model_display_to_key = {v: k for k, v in model_name_map.items()}
        
            selected_model_display = st.selectbox(
                "Select Model",
                model_display_names,
                index=model_display_names.index(model_name_map[st.session_state.selected_model]),
            )
            selected_model = model_display_to_key[selected_model_display]
        
        with filter_col3:
            model_data = merged_all[merged_all["Model"] == selected_model]
            year_data = model_data[model_data["Year"] == selected_year].copy()
            available_weeks = sorted(year_data["Week"].unique())
        
            selected_week = st.select_slider(
                "Select Week",
                options=available_weeks,
                value=st.session_state.selected_week
                if st.session_state.selected_week in available_weeks
                else min(available_weeks),
            )
        
        # UPDATE SESSION STATE ON CHANGE
        if (
            selected_year != st.session_state.selected_year
            or selected_model != st.session_state.selected_model
            or selected_week != st.session_state.selected_week
        ):
            st.session_state.selected_year = selected_year
            st.session_state.selected_model = selected_model
            st.session_state.selected_week = selected_week
            st.rerun()
            
# RIGHT COLUMN
with col2:
    # METRICS SECTION
    st.write("### **Summary Metrics**")

    avg_cases = filtered_data['Forecast_Cases'].mode()
    max_row = filtered_data.loc[filtered_data['Forecast_Cases'].idxmax()]
    min_row = filtered_data.loc[filtered_data['Forecast_Cases'].idxmin()]

    m1, m2, m3 = st.columns(3)
    m1.metric("Average Forecasted Cases", f"{avg_cases}")
    m2.metric("Highest Risk Barangay", max_row['Barangay'])
    m3.metric("Lowest Risk Barangay", min_row['Barangay'])

    # TABLE SECTION
    st.write("### **Risk Ranking by Barangay**")

    table_df = filtered_data[['Barangay', 'Forecast_Cases', 'Risk_Level']].copy()
    table_df = table_df.rename(columns={"Forecast_Cases": "Forecasted Cases", "Risk_Level": "Risk Level"})
    
    risk_order = ["Low Risk", "Moderate Risk", "High Risk"]
    table_df["Risk Level"] = pd.Categorical(table_df["Risk Level"], categories=risk_order, ordered=True)
    table_df = table_df.sort_values(by=['Risk Level', 'Forecasted Cases'], ascending=[False, False]).reset_index(drop=True)

    def color_forecast(val):
        if pd.isna(val):
            return 'background-color: #d9d9d9; color: black'
        
        color = risk_colors.get(val, "#d9d9d9")
        color_hex = color.lstrip('#')

        r, g, b = int(color_hex[0:2], 16), int(color_hex[2:4], 16), int(color_hex[4:6], 16)
        brightness = (r*299 + g*587 + b*114) / 1000
        
        text_color = "white" if brightness < 128 else "black"
        return f'background-color: {color}; color: {text_color}; font-weight: bold'
    
    styled_table = table_df.style.applymap(color_forecast, subset=['Risk Level'])
    st.dataframe(styled_table, width='stretch', height=400)
