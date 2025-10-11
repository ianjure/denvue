import streamlit as st
import geopandas as gpd
import pandas as pd
import plotly.express as px
import json

# ---- PAGE CONFIG ----
st.set_page_config(
    page_title="Denvue Dashboard",
    layout="wide"

# ---- LOAD DATA ----
@st.cache_data
def load_data():
    merged_all = pd.read_csv("forecasts.csv")

    # Convert geometry from WKT to GeoSeries
    merged_all["geometry"] = gpd.GeoSeries.from_wkt(merged_all["geometry"])
    merged_all = gpd.GeoDataFrame(merged_all, geometry="geometry", crs="EPSG:4326")

    # Ensure Date is datetime
    merged_all["Date"] = pd.to_datetime(merged_all["Date"])
    return merged_all

merged_all = load_data()

# ---- SEPARATE GEOMETRY ----
barangay_shapes = merged_all.drop_duplicates(subset="Barangay")[["Barangay", "geometry"]].copy()

# Ensure Barangay is string
barangay_shapes["Barangay"] = barangay_shapes["Barangay"].astype(str)
merged_all["Barangay"] = merged_all["Barangay"].astype(str)

# Convert to GeoJSON
barangay_json = json.loads(barangay_shapes.to_json())

# ---- TABULAR DATA ----
forecast_data = merged_all[["Barangay", "Date", "Forecast_Cases", "Risk_Level"]].copy()
forecast_data["Date"] = forecast_data["Date"].dt.strftime("%Y-%m-%d")

# ---- COLOR RANGE ----
zmin = forecast_data["Forecast_Cases"].min()
zmax = forecast_data["Forecast_Cases"].max()

# ---- CHOROPLETH ----
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
        "Date": True
    },
    animation_frame="Date",
    color_continuous_scale="YlOrRd",
    range_color=[zmin, zmax],
    mapbox_style="carto-positron",   # ✅ Neutral map background
    center={"lat": 8.48, "lon": 124.65},  # Center on Cagayan de Oro
    zoom=11,
)

# ---- LAYOUT TWEAKS ----
fig.update_layout(
    width=1100,
    height=750,
    margin=dict(r=20, t=80, l=20, b=20),
    coloraxis_colorbar=dict(
        title="Forecasted Cases",
        orientation="h",           # ✅ Make legend horizontal
        yanchor="bottom",
        y=1.05,                    # Move above the map
        xanchor="center",
        x=0.5,
        thickness=10,
        len=0.5,
        title_side="top"
    ),
    title=dict(
        text=f"Weekly Dengue Forecast by Barangay",
        x=0.5,  # ✅ Center the title
        xanchor="center"
    )
)

# ---- DISPLAY ----

st.plotly_chart(fig, use_container_width=True)
