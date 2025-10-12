import streamlit as st
import geopandas as gpd
import pandas as pd
from shapely import wkt

import json
import plotly.express as px

# ---- PAGE CONFIG ----
st.set_page_config(
    page_title="Denvue Dashboard",
    layout="wide"
)

# ---- LOAD DATA ----
@st.cache_data
def load_data():
    # Load barangay geometry
    cdo_barangays = pd.read_csv("cdo_barangays.csv")
    cdo_barangays["Geometry"] = cdo_barangays["Geometry"].apply(wkt.loads)
    gdf_barangays = gpd.GeoDataFrame(cdo_barangays, geometry="Geometry", crs="EPSG:4326")

    # Load forecasts (VARMAX)
    forecasts = pd.read_csv("varmax_forecasts.csv")
    forecasts["Date"] = pd.to_datetime(forecasts["Date"])

    # Merge with geometry
    merged = forecasts.merge(gdf_barangays, on="Barangay", how="left")
    merged_gdf = gpd.GeoDataFrame(merged, geometry="Geometry", crs="EPSG:4326")
    return merged_gdf

merged_all = load_data()

# ---- GEOJSON ----
barangay_shapes = merged_all.drop_duplicates(subset="Barangay")[["Barangay", "Geometry"]].copy()
barangay_json = json.loads(barangay_shapes.set_geometry("Geometry").to_json())

# ---- DATA PREP ----
forecast_data = merged_all[["Barangay", "Date", "Forecast_Cases", "Risk_Level"]].copy()
forecast_data["Date"] = pd.to_datetime(forecast_data["Date"])
forecast_data["Year"] = forecast_data["Date"].dt.year
forecast_data["Date_str"] = forecast_data["Date"].dt.strftime("%Y-%m-%d")

# ---- COLOR RANGE ----
zmin = forecast_data["Forecast_Cases"].min()
zmax = forecast_data["Forecast_Cases"].max()

# ---- CHOROPLETH MAP ----
fig = px.choropleth_mapbox(
    forecast_data,
    geojson=barangay_json,
    locations="Barangay",
    featureidkey="properties.Barangay",
    color="Forecast_Cases",
    hover_name="Barangay",
    hover_data={
        "Forecast_Cases": True,
        "Risk_Level": True,
        "Date_str": True
    },
    animation_frame="Date_str",
    color_continuous_scale="YlOrRd",
    range_color=[zmin, zmax],
    mapbox_style="carto-positron",
    center={"lat": 8.48, "lon": 124.65},
    zoom=11,
)

fig.update_layout(
    width=1100,
    height=750,
    margin=dict(r=10, t=60, l=10, b=10),
    coloraxis_colorbar=dict(
        title="Forecasted Cases",
        orientation="h",
        yanchor="bottom",
        y=1.05,
        xanchor="center",
        x=0.5,
        thickness=10,
        len=0.5,
        title_side="top"
    ),
    title=dict(
        text="Weekly Dengue Forecast by Barangay (VARMAX Model)",
        x=0.5,
        xanchor="center"
    )
)

# ---- PAGE LAYOUT ----
st.markdown("## 🦟 Denvue Forecast Dashboard (2025–2027)")

col1, col2 = st.columns([2.5, 1])

with col1:
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.markdown("### 📊 Forecast Summary")

    # --- YEAR FILTER ---
    available_years = sorted(forecast_data["Year"].unique())
    selected_year = st.selectbox("Select Year", available_years, index=len(available_years) - 1)

    # --- FILTER DATA BY YEAR ---
    filtered_data = forecast_data[forecast_data["Year"] == selected_year]
    latest_date = filtered_data["Date"].max()
    latest_week = filtered_data[filtered_data["Date"] == latest_date][["Barangay", "Forecast_Cases", "Risk_Level"]]
    latest_week = latest_week.sort_values(by="Forecast_Cases", ascending=False)

    st.markdown(f"**Latest Week: {latest_date.strftime('%B %d, %Y')}**")
    st.dataframe(
        latest_week.style.background_gradient(subset=["Forecast_Cases"], cmap="YlOrRd"),
        use_container_width=True,
        height=700
    )

# ---- FOOTER ----
st.markdown(
    "<p style='text-align:center; color:gray; font-size:12px;'>"
    "Data Source: VARMAX Forecasts | Geometry: Cagayan de Oro Barangays (EPSG:4326)"
    "</p>",
    unsafe_allow_html=True
)
