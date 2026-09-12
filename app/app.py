

import streamlit as st
import pandas as pd
import folium

from streamlit_folium import st_folium

from risk_engine import create_live_risk_dataset

from data_loader import (
    load_static_data,
    load_boundaries,
    load_hospitals,
    load_cooling,
)


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Delhi Heat-Health Platform",
    page_icon="🌡️",
    layout="wide",
)


# ============================================================
# TITLE
# ============================================================

st.title("🌡️ Delhi Heat-Health Platform")
st.caption("Predict → Warn → Protect → Rescue")


# ============================================================
# LOAD LIVE RISK DATA
# ============================================================

@st.cache_data(ttl=1800)
def get_live_risk():
    return create_live_risk_dataset()


with st.spinner("Generating live Delhi heat-risk forecast..."):
    risk = get_live_risk()


# ============================================================
# LOAD SUPPORTING DATA
# ============================================================

boundaries = load_boundaries()
static = load_static_data()


# ============================================================
# CLEAN IDS
# ============================================================

risk["Ward_No"] = pd.to_numeric(
    risk["Ward_No"],
    errors="coerce",
)

boundaries["Ward_No"] = pd.to_numeric(
    boundaries["Ward_No"],
    errors="coerce",
)

static["Ward_No"] = pd.to_numeric(
    static["Ward_No"],
    errors="coerce",
)


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.header("Forecast Controls")

lead_times = sorted(
    risk["lead_time_days"].dropna().unique()
)

dates = sorted(
    risk["target_date"].dropna().unique()
)

lead_time = st.sidebar.selectbox(
    "Forecast horizon",
    lead_times,
    format_func=lambda x: f"{int(x)}-day forecast",
)

selected_date = st.sidebar.selectbox(
    "Target date",
    dates,
)


# ============================================================
# FILTER SELECTED FORECAST
# ============================================================

map_risk = risk[
    (risk["lead_time_days"] == lead_time)
    & (risk["target_date"] == selected_date)
].copy()


# ============================================================
# ADD RESOURCE INFORMATION FROM STATIC DATA
# ============================================================

resource_columns = [
    "nearest_hospital_dist_km",
    "nearest_cooling_center_dist_km",
    "hospitals_within_2km",
    "hospitals_within_5km",
    "hospital_beds_within_5km",
    "cooling_centers_within_1km",
    "cooling_centers_within_2km",
    "cooling_centers_temples_1km",
    "cooling_centers_schools_1km",
    "cooling_centers_govt_bldg_1km",
]

available_resource_columns = [
    column
    for column in resource_columns
    if column in static.columns
]


resource_data = static[
    ["Ward_No"] + available_resource_columns
].copy()


map_risk = map_risk.merge(
    resource_data,
    on="Ward_No",
    how="left",
)


# ============================================================
# ADD WARD NAMES FROM BOUNDARIES
# ============================================================

if "WardName" in boundaries.columns:

    ward_names = boundaries[
        ["Ward_No", "WardName"]
    ].drop_duplicates(
        "Ward_No"
    )

    map_risk = map_risk.merge(
        ward_names,
        on="Ward_No",
        how="left",
    )


# ============================================================
# PREPARE MAP DATA
# ============================================================

map_risk_clean = map_risk[
    [
        "Ward_No",
        "WardName",
        "forecast_wbgt_max_C",
        "WBGT_Hazard_Score",
        "Vulnerability_Score",
        "Response_Gap_Score",
        "Future_Heat_Hazard",
        "Human_Heat_Risk",
        "Risk_Category",
    ]
    + available_resource_columns
].copy()


map_data = boundaries.merge(
    map_risk_clean,
    on="Ward_No",
    how="left",
    suffixes=("", "_risk"),
)


# ============================================================
# RISK COLOUR
# ============================================================

def risk_color(category):

    if category is None:
        return "#BDBDBD"

    category = str(category).strip().lower()

    if category == "very high":
        return "#7f0000"

    if category == "high":
        return "#d7301f"

    if category == "moderate":
        return "#fc8d59"

    if category == "low":
        return "#91cf60"

    if category == "very low":
        return "#1a9850"

    return "#BDBDBD"


# ============================================================
# HEADER
# ============================================================

st.subheader(
    f"Delhi Heat-Health Risk — {selected_date}"
)

st.write(
    f"""
    **{int(lead_time)}-day forecast**

    Live Random Forest predictions are combined with
    ward-level heat exposure, population vulnerability,
    and response-access gaps across **250 MCD wards**.
    """
)

st.info(
    "The central gap in the MCD ward layer represents the "
    "NDMC jurisdiction, which is governed separately from MCD. "
    "It is not a missing MCD ward."
)


# ============================================================
# MAP
# ============================================================

m = folium.Map(
    location=[28.6139, 77.2090],
    zoom_start=10,
    tiles="CartoDB positron",
)


# ============================================================
# MAP STYLE
# ============================================================

def style_function(feature):

    properties = feature.get("properties", {})

    category = properties.get(
        "Risk_Category",
        None,
    )

    return {
        "fillColor": risk_color(category),
        "color": "#444444",
        "weight": 1,
        "fillOpacity": 0.65,
    }


# ============================================================
# TOOLTIP
# ============================================================

tooltip_fields = [
    "Ward_No",
    "WardName",
    "Risk_Category",
    "Human_Heat_Risk",
    "forecast_wbgt_max_C",
]

tooltip_aliases = [
    "Ward:",
    "Name:",
    "Risk:",
    "Human Heat Risk:",
    "Forecast WBGT:",
]


folium.GeoJson(
    map_data,
    name="MCD Wards",
    style_function=style_function,
    tooltip=folium.GeoJsonTooltip(
        fields=tooltip_fields,
        aliases=tooltip_aliases,
        localize=True,
        sticky=True,
        labels=True,
        style="""
            background-color: white;
            color: black;
            font-family: Arial;
            font-size: 13px;
            padding: 8px;
        """,
    ),
).add_to(m)


# ============================================================
# LEGEND
# ============================================================

legend_html = """
<div style="
    position: fixed;
    bottom: 30px;
    left: 30px;
    z-index: 9999;
    background-color: white;
    border: 2px solid #777;
    border-radius: 6px;
    padding: 12px;
    font-family: Arial;
    font-size: 13px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.25);
">

    <div style="
        font-weight: bold;
        font-size: 14px;
        margin-bottom: 8px;
    ">
        Heat-Health Risk
    </div>

    <div style="margin-bottom: 4px;">
        <span style="
            display:inline-block;
            width:16px;
            height:16px;
            background:#7f0000;
            margin-right:6px;
            vertical-align:middle;
        "></span>
        Very High
    </div>

    <div style="margin-bottom: 4px;">
        <span style="
            display:inline-block;
            width:16px;
            height:16px;
            background:#d7301f;
            margin-right:6px;
            vertical-align:middle;
        "></span>
        High
    </div>

    <div style="margin-bottom: 4px;">
        <span style="
            display:inline-block;
            width:16px;
            height:16px;
            background:#fc8d59;
            margin-right:6px;
            vertical-align:middle;
        "></span>
        Moderate
    </div>

    <div style="margin-bottom: 4px;">
        <span style="
            display:inline-block;
            width:16px;
            height:16px;
            background:#91cf60;
            margin-right:6px;
            vertical-align:middle;
        "></span>
        Low
    </div>

    <div>
        <span style="
            display:inline-block;
            width:16px;
            height:16px;
            background:#1a9850;
            margin-right:6px;
            vertical-align:middle;
        "></span>
        Very Low
    </div>

</div>
"""

m.get_root().html.add_child(
    folium.Element(legend_html)
)

folium.LayerControl().add_to(m)


# ============================================================
# DISPLAY MAP + CLICK DETECTION
# ============================================================

map_result = st_folium(
    m,
    width=None,
    height=700,
    key="delhi_heat_risk_map",
    returned_objects=["last_object_clicked"],
)


# ============================================================
# DETECT CLICKED WARD
# ============================================================

clicked = map_result.get(
    "last_object_clicked"
)

selected_ward = None

if clicked:

    clicked_properties = clicked.get(
        "properties",
        {}
    )

    clicked_ward = clicked_properties.get(
        "Ward_No"
    )

    if clicked_ward is not None:

        try:
            selected_ward = int(
                float(clicked_ward)
            )
        except (ValueError, TypeError):
            selected_ward = None


# ============================================================
# SELECTED WARD DETAIL
# ============================================================

if selected_ward is not None:

    selected_rows = map_data[
        map_data["Ward_No"] == selected_ward
    ]

    if not selected_rows.empty:

        ward = selected_rows.iloc[0]

        ward_name = ward.get(
            "WardName",
            f"Ward {selected_ward}"
        )

        risk_category = str(
            ward.get(
                "Risk_Category",
                "Unknown"
            )
        )

        risk_score = float(
            ward["Human_Heat_Risk"]
        )

        wbgt = float(
            ward["forecast_wbgt_max_C"]
        )

        hazard = float(
            ward["WBGT_Hazard_Score"]
        )

        vulnerability = float(
            ward["Vulnerability_Score"]
        )

        response_gap = float(
            ward["Response_Gap_Score"]
        )


        # ====================================================
        # WARD HEADER
        # ====================================================

        st.divider()

        st.subheader(
            f"📍 Ward {selected_ward} — {ward_name}"
        )

        st.caption(
            f"{int(lead_time)}-day forecast • "
            f"Target date: {selected_date}"
        )


        # ====================================================
        # TOP METRICS
        # ====================================================

        col1, col2, col3, col4 = st.columns(4)

        with col1:

            st.metric(
                "Heat-Health Risk",
                f"{risk_score:.3f}",
                risk_category,
            )

        with col2:

            st.metric(
                "Forecast WBGT",
                f"{wbgt:.1f} °C",
            )

        with col3:

            st.metric(
                "Heat Hazard",
                f"{hazard:.3f}",
            )

        with col4:

            st.metric(
                "Response Gap",
                f"{response_gap:.3f}",
            )


        # ====================================================
        # WHY IS IT AT RISK?
        # ====================================================

        st.markdown(
            "### Why is this ward at risk?"
        )

        explanation_col1, explanation_col2 = st.columns(2)

        with explanation_col1:

            st.markdown(
                f"""
                **🌡️ Future Heat Hazard**

                Forecast WBGT reaches
                **{wbgt:.1f} °C**.

                The empirical heat-hazard score is
                **{hazard:.3f}**, representing the position
                of this forecast relative to the historical
                WBGT reference distribution.
                """
            )

        with explanation_col2:

            st.markdown(
                f"""
                **👥 Population Vulnerability**

                Vulnerability score:
                **{vulnerability:.3f}**

                This combines the selected population-density
                and vulnerability indicators used by the model.
                """
            )


        # ====================================================
        # RESPONSE CAPACITY
        # ====================================================

        st.markdown(
            "### 🚑 Response capacity"
        )

        if response_gap >= 0.75:

            st.error(
                f"""
                **High response-access gap ({response_gap:.3f})**

                This ward has relatively weaker proximity to
                mapped hospitals and cooling resources.
                """
            )

        elif response_gap >= 0.50:

            st.warning(
                f"""
                **Moderate response-access gap ({response_gap:.3f})**

                Resource accessibility is relatively weaker
                than in lower-gap wards.
                """
            )

        else:

            st.success(
                f"""
                **Lower response-access gap ({response_gap:.3f})**

                This ward has comparatively better access to
                mapped response resources.
                """
            )


        # ====================================================
        # NEAREST RESOURCES
        # ====================================================

        st.markdown(
            "#### 📍 Nearest response resources"
        )

        resource_col1, resource_col2 = st.columns(2)


        # ----------------------------------------------------
        # HOSPITAL
        # ----------------------------------------------------

        with resource_col1:

            hospital_distance = ward.get(
                "nearest_hospital_dist_km",
                None
            )

            st.markdown(
                "**🏥 Nearest hospital**"
            )

            if pd.notna(hospital_distance):

                st.metric(
                    "Approx. distance",
                    f"{float(hospital_distance):.2f} km"
                )

            else:

                st.info(
                    "Hospital distance unavailable."
                )


        # ----------------------------------------------------
        # COOLING CENTRE
        # ----------------------------------------------------

        with resource_col2:

            cooling_distance = ward.get(
                "nearest_cooling_center_dist_km",
                None
            )

            st.markdown(
                "**❄️ Nearest cooling centre**"
            )

            if pd.notna(cooling_distance):

                st.metric(
                    "Approx. distance",
                    f"{float(cooling_distance):.2f} km"
                )

            else:

                st.info(
                    "Cooling-centre distance unavailable."
                )


        # ====================================================
        # RESOURCE COVERAGE
        # ====================================================

        st.markdown(
            "#### Resource coverage"
        )

        coverage_col1, coverage_col2, coverage_col3, coverage_col4 = st.columns(4)


        with coverage_col1:

            value = ward.get(
                "hospitals_within_2km",
                None
            )

            if pd.notna(value):

                st.metric(
                    "Hospitals ≤ 2 km",
                    int(value)
                )

            else:

                st.metric(
                    "Hospitals ≤ 2 km",
                    "N/A"
                )


        with coverage_col2:

            value = ward.get(
                "hospitals_within_5km",
                None
            )

            if pd.notna(value):

                st.metric(
                    "Hospitals ≤ 5 km",
                    int(value)
                )

            else:

                st.metric(
                    "Hospitals ≤ 5 km",
                    "N/A"
                )


        with coverage_col3:

            value = ward.get(
                "cooling_centers_within_1km",
                None
            )

            if pd.notna(value):

                st.metric(
                    "Cooling ≤ 1 km",
                    int(value)
                )

            else:

                st.metric(
                    "Cooling ≤ 1 km",
                    "N/A"
                )


        with coverage_col4:

            value = ward.get(
                "cooling_centers_within_2km",
                None
            )

            if pd.notna(value):

                st.metric(
                    "Cooling ≤ 2 km",
                    int(value)
                )

            else:

                st.metric(
                    "Cooling ≤ 2 km",
                    "N/A"
                )


        st.caption(
            "Resource-access indicators are based on the "
            "mapped hospital and cooling-centre datasets."
        )


        # ====================================================
        # RECOMMENDED ACTION
        # ====================================================

        st.markdown(
            "### 🛡️ Recommended action"
        )

        if risk_category in [
            "High",
            "Very High",
        ]:

            st.warning(
                """
                **Priority intervention recommended**

                • Issue advance heat-risk alerts  
                • Push hydration and heat-avoidance reminders  
                • Prioritise cooling-centre readiness  
                • Verify emergency medical preparedness  
                • Target outreach toward vulnerable populations
                """
            )

        elif risk_category == "Moderate":

            st.info(
                """
                **Preventive action recommended**

                • Monitor the forecast  
                • Prepare heat-safety messaging  
                • Check cooling-resource availability  
                • Encourage hydration and reduced peak-hour exposure
                """
            )

        else:

            st.success(
                """
                **Routine monitoring**

                Continue monitoring the forecast and maintain
                normal heat-health preparedness.
                """
            )


        # ====================================================
        # RISK COMPOSITION
        # ====================================================

        st.markdown(
            "### 📊 Risk composition"
        )

        component_df = pd.DataFrame(
            {
                "Component": [
                    "Future Heat Hazard",
                    "Population Vulnerability",
                    "Response Gap",
                ],
                "Score": [
                    hazard,
                    vulnerability,
                    response_gap,
                ],
                "Weight": [
                    "50%",
                    "30%",
                    "20%",
                ],
            }
        )

        st.dataframe(
            component_df,
            use_container_width=True,
            hide_index=True,
        )

        st.caption(
            "Human Heat Risk = 0.50 × Future Heat Hazard "
            "+ 0.30 × Vulnerability + 0.20 × Response Gap. "
            "This is a prioritisation index, not a probability "
            "of illness or death."
        )


# ============================================================
# NO WARD SELECTED
# ============================================================

else:

    st.info(
        "👆 Click any ward on the map to view its "
        "heat-health intelligence and response resources."
    )


# ============================================================
# SPATIAL COVERAGE
# ============================================================

st.divider()

st.subheader("📍 Spatial Coverage")

col1, col2, col3 = st.columns(3)

with col1:

    st.metric(
        "MCD wards",
        risk["Ward_No"].nunique(),
    )

with col2:

    st.metric(
        "Forecast",
        f"{int(lead_time)}-day",
    )

with col3:

    st.metric(
        "Target date",
        str(selected_date),
    )


st.caption(
    "The ward-level model currently covers the 250 MCD wards. "
    "NDMC and Delhi Cantonment are separate civic jurisdictions "
    "and are not assigned artificial MCD ward boundaries."
)


# ============================================================
# RISK SUMMARY
# ============================================================

st.divider()

st.subheader("📊 Risk Summary")

risk_counts = (
    map_data["Risk_Category"]
    .value_counts()
    .reindex(
        [
            "Very Low",
            "Low",
            "Moderate",
            "High",
            "Very High",
        ],
        fill_value=0,
    )
    .rename_axis("Risk Level")
    .reset_index(
        name="Number of Wards"
    )
)

st.dataframe(
    risk_counts,
    use_container_width=True,
    hide_index=True,
)


# ============================================================
# HIGH-RISK WARDS
# ============================================================

high_risk = map_data[
    map_data["Risk_Category"].isin(
        [
            "High",
            "Very High",
        ]
    )
].copy()


if not high_risk.empty:

    st.subheader(
        "🚨 High-Risk Wards"
    )

    high_risk_display = high_risk[
        [
            "Ward_No",
            "WardName",
            "Risk_Category",
            "forecast_wbgt_max_C",
            "WBGT_Hazard_Score",
            "Vulnerability_Score",
            "Response_Gap_Score",
            "Human_Heat_Risk",
        ]
    ].sort_values(
        "Human_Heat_Risk",
        ascending=False,
    )

    st.dataframe(
        high_risk_display,
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "Delhi Heat-Health Platform | "
    "Predict → Warn → Protect → Rescue"
)

