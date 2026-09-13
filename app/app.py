import re

import streamlit as st
import pandas as pd
import folium

from streamlit_folium import st_folium

from risk_engine import (
    create_live_risk_dataset,
    create_hourly_risk,
    find_peak_risk_period,
)

from data_loader import (
    load_static_data,
    load_boundaries,
    load_hospitals,
    load_cooling_centres,
)

from citizen_dashboard import show_citizen_dashboard


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

st.title("Delhi Heat-Health Platform")

st.caption(
    "Predict → Warn → Protect → Rescue"
)


# ============================================================
# DASHBOARD MODE
# ============================================================

if "dashboard_mode" not in st.session_state:
    st.session_state.dashboard_mode = "authority"


mode_col1, mode_col2 = st.columns(2)


with mode_col1:

    if st.button(
        "🏛️ Authority Dashboard",
        use_container_width=True,
    ):

        st.session_state.dashboard_mode = "authority"

        st.rerun()


with mode_col2:

    if st.button(
        "👤 Check My Area",
        use_container_width=True,
    ):

        st.session_state.dashboard_mode = "citizen"

        st.rerun()


# ============================================================
# LOAD DAILY LIVE RISK DATA
# ============================================================

@st.cache_data(ttl=1800)
def get_live_risk():

    return create_live_risk_dataset()


with st.spinner(
    "Generating live Delhi heat-risk forecast..."
):

    risk = get_live_risk()


# ============================================================
# LOAD HOURLY RISK DATA
# ============================================================

@st.cache_data(ttl=1800)
def get_hourly_risk():

    return create_hourly_risk()


with st.spinner(
    "Generating hourly heat-risk forecast..."
):

    hourly_risk = get_hourly_risk()


# ============================================================
# LOAD SUPPORTING DATA
# ============================================================

boundaries = load_boundaries()

static = load_static_data()


# ============================================================
# CITIZEN DASHBOARD
# ============================================================

if st.session_state.dashboard_mode == "citizen":

    hospitals = load_hospitals()

    cooling_centres = load_cooling_centres()

    show_citizen_dashboard(
        risk=risk,
        static=static,
        boundaries=boundaries,
        hospitals=hospitals,
        cooling_centres=cooling_centres,
        hourly_risk=hourly_risk,
    )

    st.stop()


# ============================================================
# CLEAN IDS
# ============================================================

risk["Ward_No"] = pd.to_numeric(
    risk["Ward_No"],
    errors="coerce",
)

hourly_risk["Ward_No"] = pd.to_numeric(
    hourly_risk["Ward_No"],
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
# NORMALISE DATES
# ============================================================

risk["target_date"] = pd.to_datetime(
    risk["target_date"]
).dt.date


hourly_risk["target_date"] = pd.to_datetime(
    hourly_risk["target_date"]
).dt.date


hourly_risk["time"] = pd.to_datetime(
    hourly_risk["time"]
)


# ============================================================
# SESSION STATE
# ============================================================

if "selected_date" not in st.session_state:

    st.session_state.selected_date = sorted(
        risk["target_date"].dropna().unique()
    )[0]


if "selected_ward" not in st.session_state:

    st.session_state.selected_ward = None


# ============================================================
# AVAILABLE FORECAST DATES
# ============================================================

forecast_dates = sorted(
    risk["target_date"].dropna().unique()
)


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.header("Forecast")

st.sidebar.caption(
    "Select a target date. The forecast horizon is "
    "determined automatically."
)


sidebar_date = st.sidebar.selectbox(
    "Target date",

    forecast_dates,

    index=forecast_dates.index(
        st.session_state.selected_date
    ),

    format_func=lambda d: d.strftime(
        "%d %b %Y"
    ),
)


if sidebar_date != st.session_state.selected_date:

    st.session_state.selected_date = sidebar_date

    st.session_state.selected_ward = None

    st.rerun()


# ============================================================
# SELECTED DATE
# ============================================================

selected_date = st.session_state.selected_date


# ============================================================
# DETERMINE LEAD TIME
# ============================================================

selected_date_rows = risk[
    risk["target_date"] == selected_date
]


if not selected_date_rows.empty:

    lead_time = int(
        selected_date_rows[
            "lead_time_days"
        ].iloc[0]
    )

else:

    lead_time = None


# ============================================================
# 5-DAY FORECAST OUTLOOK
# ============================================================

st.subheader("5-Day Heat-Risk Outlook")

st.caption(
    "Select a forecast date to update the ward-level risk map."
)


calendar_cols = st.columns(
    len(forecast_dates)
)


for i, forecast_date in enumerate(forecast_dates):

    date_data = risk[
        risk["target_date"] == forecast_date
    ]

    high_count = int(
        date_data[
            date_data["Risk_Category"].isin(
                ["High", "Very High"]
            )
        ]["Ward_No"].nunique()
    )

    very_high_count = int(
        date_data[
            date_data["Risk_Category"]
            == "Very High"
        ]["Ward_No"].nunique()
    )

    is_selected = (
        forecast_date == selected_date
    )

    with calendar_cols[i]:

        st.markdown(
            f"**{forecast_date.strftime('%d %b')}**"
        )

        if st.button(
            "Selected"
            if is_selected
            else "View forecast",

            key=f"forecast_date_{forecast_date}",

            use_container_width=True,
        ):

            st.session_state.selected_date = (
                forecast_date
            )

            st.session_state.selected_ward = None

            st.rerun()

        if very_high_count > 0:

            st.error(
                f"VERY HIGH · {high_count} wards"
            )

        elif high_count >= 75:

            st.error(
                f"HIGH · {high_count} wards"
            )

        elif high_count >= 30:

            st.warning(
                f"ELEVATED · {high_count} wards"
            )

        else:

            st.success(
                f"LOWER · {high_count} wards"
            )


# ============================================================
# SELECTED DATE HEADER
# ============================================================

st.divider()

st.subheader(
    f"Heat-Health Risk — "
    f"{selected_date.strftime('%A, %d %B %Y')}"
)


if lead_time is not None:

    st.caption(
        f"{lead_time}-day forecast · "
        f"250 MCD wards"
    )


# ============================================================
# FILTER SELECTED FORECAST
# ============================================================

map_risk = risk[
    risk["target_date"] == selected_date
].copy()


# ============================================================
# ADD RESOURCE + POPULATION INFORMATION
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


# Population is contextual information.
# It is NOT treated as a probability of illness.

population_columns = [
    "TotalPop",
]


available_population_columns = [
    column
    for column in population_columns
    if column in static.columns
]


available_resource_columns = [
    column
    for column in resource_columns
    if column in static.columns
]


resource_data = static[
    ["Ward_No"]
    + available_resource_columns
    + available_population_columns
].copy()


map_risk = map_risk.merge(
    resource_data,
    on="Ward_No",
    how="left",
)


# ============================================================
# ADD WARD NAMES
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

else:

    map_risk["WardName"] = (
        "Ward "
        + map_risk["Ward_No"].astype(str)
    )


# ============================================================
# PREPARE MAP DATA
# ============================================================

map_columns = [

    "Ward_No",

    "WardName",

    "forecast_wbgt_max_C",

    "WBGT_Hazard_Score",

    "Vulnerability_Score",

    "Response_Gap_Score",

    "Future_Heat_Hazard",

    "Human_Heat_Risk",

    "Risk_Category",

] + available_resource_columns + available_population_columns


map_risk_clean = map_risk[
    map_columns
].copy()


map_data = boundaries.merge(
    map_risk_clean,
    on="Ward_No",
    how="left",
    suffixes=("", "_risk"),
)


# ============================================================
# RISK COLOURS
# ============================================================

def risk_color(category):

    if category is None:

        return "#BDBDBD"


    if pd.isna(category):

        return "#BDBDBD"


    category = (
        str(category)
        .strip()
        .lower()
    )


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
# CREATE FOLIUM MAP
# ============================================================

m = folium.Map(

    location=[
        28.6139,
        77.2090
    ],

    zoom_start=10,

    tiles="CartoDB positron",

)


# ============================================================
# MAP STYLE
# ============================================================

def style_function(feature):

    properties = feature.get(
        "properties",
        {}
    )

    category = properties.get(
        "Risk_Category",
        None,
    )

    return {

        "fillColor":
            risk_color(category),

        "color":
            "#555555",

        "weight":
            1,

        "fillOpacity":
            0.68,

    }


# ============================================================
# MAP TOOLTIP
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


# ============================================================
# MAP POPUP
# ============================================================

popup_fields = [

    "Ward_No",

    "WardName",

    "Risk_Category",

    "Human_Heat_Risk",

    "forecast_wbgt_max_C",

]


popup_aliases = [

    "Ward:",

    "Name:",

    "Risk:",

    "Human Heat Risk:",

    "Forecast WBGT:",

]


geojson = folium.GeoJson(

    map_data,

    name="MCD Wards",

    style_function=style_function,

    tooltip=folium.GeoJsonTooltip(

        fields=tooltip_fields,

        aliases=tooltip_aliases,

        localize=True,

        sticky=True,

        labels=True,

    ),

    popup=folium.GeoJsonPopup(

        fields=popup_fields,

        aliases=popup_aliases,

        localize=True,

        labels=True,

    ),

)


geojson.add_to(m)

folium.LayerControl().add_to(m)


# ============================================================
# RISK LEGEND
# ============================================================

st.markdown("#### Risk level")

legend_cols = st.columns(5)


with legend_cols[0]:

    st.markdown("🟩 **Very Low**")


with legend_cols[1]:

    st.markdown("🟩 **Low**")


with legend_cols[2]:

    st.markdown("🟧 **Moderate**")


with legend_cols[3]:

    st.markdown("🟥 **High**")


with legend_cols[4]:

    st.markdown("🟥 **Very High**")


st.caption(
    "Map colours correspond to the Human Heat Risk "
    "prioritisation categories."
)


# ============================================================
# DISPLAY MAP
# ============================================================

map_result = st_folium(

    m,

    width=None,

    height=700,

    key=(
        f"delhi_heat_risk_map_"
        f"{selected_date}"
    ),

    returned_objects=[

        "last_object_clicked",

        "last_object_clicked_popup",

    ],

)


# ============================================================
# DETECT CLICKED WARD
# ============================================================

clicked_popup = map_result.get(
    "last_object_clicked_popup"
)


clicked_ward = None


if clicked_popup:

    match = re.search(

        r"Ward:\s*([0-9]+)",

        str(clicked_popup),

    )

    if match:

        clicked_ward = int(
            match.group(1)
        )


if clicked_ward is not None:

    st.session_state.selected_ward = (
        clicked_ward
    )


selected_ward = (
    st.session_state.selected_ward
)


# ============================================================
# SELECTED WARD DETAIL
# ============================================================

if selected_ward is not None:

    selected_rows = map_risk[
        map_risk["Ward_No"]
        == selected_ward
    ]


    if not selected_rows.empty:

        ward = selected_rows.iloc[0]


        ward_name = ward.get(
            "WardName",
            f"Ward {selected_ward}",
        )


        if pd.isna(ward_name):

            ward_name = (
                f"Ward {selected_ward}"
            )


        risk_category = str(
            ward.get(
                "Risk_Category",
                "Unknown",
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
        # WARD POPULATION
        # ====================================================

        total_population = ward.get(
            "TotalPop",
            None,
        )


        if pd.notna(total_population):

            total_population = int(
                round(float(total_population))
            )

        else:

            total_population = None


        # ====================================================
        # WARD INTELLIGENCE
        # ====================================================

        st.divider()

        st.subheader(
            f"Ward {selected_ward} — "
            f"{ward_name}"
        )


        st.caption(
            f"{lead_time}-day forecast · "
            f"{selected_date.strftime('%d %B %Y')}"
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
        # POPULATION CONTEXT
        # ====================================================

        st.markdown(
            "### 👥 Population context"
        )


        if (
            total_population is not None
            and total_population > 0
        ):

            st.metric(
                "Ward population",
                f"{total_population:,}",
            )


            if risk_category in [
                "High",
                "Very High",
            ]:

                st.warning(
                    f"""
                    **{total_population:,} residents live in
                    this {risk_category}-risk ward.**

                    This population figure represents residents
                    living in a ward currently classified for
                    priority heat-health attention.

                    It does **not** mean that all residents will
                    experience heat-related illness.
                    """
                )

            else:

                st.info(
                    f"""
                    This ward has an estimated population of
                    **{total_population:,} residents**.
                    """
                )


        elif total_population == 0:

            st.info(
                "Ward population data is recorded as 0 for this ward."
            )


        else:

            st.info(
                "Ward population data is currently unavailable."
            )


        # ====================================================
        # HOURLY RISK TREND
        # ====================================================

        st.markdown(
            "### 📈 Hourly heat-risk outlook"
        )


        hourly_ward = hourly_risk[
            (hourly_risk["Ward_No"] == selected_ward)
            & (
                hourly_risk["target_date"]
                == selected_date
            )
        ].copy()


        if not hourly_ward.empty:

            hourly_ward = (
                hourly_ward
                .sort_values("time")
                .copy()
            )


            hourly_chart = hourly_ward[
                [
                    "time",
                    "Human_Heat_Risk",
                ]
            ].copy()


            hourly_chart = hourly_chart.set_index(
                "time"
            )


            hourly_chart = hourly_chart.rename(
                columns={
                    "Human_Heat_Risk":
                    "Human Heat Risk"
                }
            )


            st.line_chart(
                hourly_chart,
                y="Human Heat Risk",
                height=300,
            )


            st.caption(
                "Hourly Human Heat Risk for the selected "
                "ward and forecast date. Values represent "
                "the combined heat hazard, population "
                "vulnerability and response-access gap."
            )


        else:

            st.info(
                "Hourly risk information is not "
                "currently available for this ward and date."
            )


        # ====================================================
        # HOURLY PEAK RISK
        # ====================================================

        st.markdown(
            "### ⏰ Highest-risk period"
        )


        peak = find_peak_risk_period(
            hourly_risk,
            selected_ward,
            selected_date,
        )


        if peak:

            peak_col1, peak_col2, peak_col3 = (
                st.columns(3)
            )


            with peak_col1:

                st.metric(
                    "Peak period",
                    peak["period_label"],
                )


            with peak_col2:

                st.metric(
                    "3-hour average risk",
                    f"{peak['peak_risk']:.3f}",
                )


            with peak_col3:

                st.metric(
                    "Peak WBGT",
                    f"{peak['peak_wbgt']:.1f} °C",
                )


            if risk_category in [
                "High",
                "Very High",
            ]:

                st.warning(
                    f"Highest predicted risk occurs during "
                    f"**{peak['period_label']}**. "
                    "This period should be prioritised for "
                    "targeted heat-safety messaging and "
                    "operational preparedness."
                )


            elif risk_category == "Moderate":

                st.info(
                    f"Highest predicted risk occurs during "
                    f"**{peak['period_label']}**. "
                    "Consider scheduling preventive messaging "
                    "before this period."
                )


            else:

                st.success(
                    f"Highest predicted risk occurs during "
                    f"**{peak['period_label']}**."
                )


        else:

            st.info(
                "Hourly peak-risk information is not "
                "currently available for this ward and date."
            )


        # ====================================================
        # WHY IS THIS WARD AT RISK?
        # ====================================================

        st.markdown(
            "### Why is this ward at risk?"
        )


        explanation_col1, explanation_col2 = (
            st.columns(2)
        )


        with explanation_col1:

            st.markdown(
                f"""
                **Future Heat Hazard**

                Forecast WBGT reaches
                **{wbgt:.1f} °C**.

                The empirical heat-hazard score is
                **{hazard:.3f}**, representing the
                position of this forecast relative to
                the historical WBGT reference
                distribution.
                """
            )


        with explanation_col2:

            st.markdown(
                f"""
                **Population Vulnerability**

                Vulnerability score:
                **{vulnerability:.3f}**

                This represents the combined population
                vulnerability indicators used by the
                risk framework.
                """
            )


        # ====================================================
        # RESPONSE CAPACITY
        # ====================================================

        st.markdown(
            "### Response capacity"
        )


        if response_gap >= 0.75:

            st.error(
                f"""
                **High response-access gap ({response_gap:.3f})**

                This ward has relatively weaker
                proximity to mapped hospitals and
                cooling resources.
                """
            )


        elif response_gap >= 0.50:

            st.warning(
                f"""
                **Moderate response-access gap ({response_gap:.3f})**

                Resource accessibility is relatively
                weaker than in lower-gap wards.
                """
            )


        else:

            st.success(
                f"""
                **Lower response-access gap ({response_gap:.3f})**

                This ward has comparatively better
                access to mapped response resources.
                """
            )


        # ====================================================
        # NEAREST RESOURCES
        # ====================================================

        st.markdown(
            "#### Nearest response resources"
        )


        resource_col1, resource_col2 = (
            st.columns(2)
        )


        with resource_col1:

            hospital_distance = ward.get(
                "nearest_hospital_dist_km",
                None,
            )


            st.markdown(
                "**Nearest hospital**"
            )


            if pd.notna(
                hospital_distance
            ):

                st.metric(
                    "Approx. distance",
                    f"{float(hospital_distance):.2f} km",
                )

            else:

                st.info(
                    "Hospital distance unavailable."
                )


        with resource_col2:

            cooling_distance = ward.get(
                "nearest_cooling_center_dist_km",
                None,
            )


            st.markdown(
                "**Nearest cooling centre**"
            )


            if pd.notna(
                cooling_distance
            ):

                st.metric(
                    "Approx. distance",
                    f"{float(cooling_distance):.2f} km",
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


        coverage_col1, coverage_col2, coverage_col3, coverage_col4 = (
            st.columns(4)
        )


        with coverage_col1:

            value = ward.get(
                "hospitals_within_2km",
                None,
            )


            if pd.notna(value):

                st.metric(
                    "Hospitals ≤ 2 km",
                    int(value),
                )

            else:

                st.metric(
                    "Hospitals ≤ 2 km",
                    "N/A",
                )


        with coverage_col2:

            value = ward.get(
                "hospitals_within_5km",
                None,
            )


            if pd.notna(value):

                st.metric(
                    "Hospitals ≤ 5 km",
                    int(value),
                )

            else:

                st.metric(
                    "Hospitals ≤ 5 km",
                    "N/A",
                )


        with coverage_col3:

            value = ward.get(
                "cooling_centers_within_1km",
                None,
            )


            if pd.notna(value):

                st.metric(
                    "Cooling ≤ 1 km",
                    int(value),
                )

            else:

                st.metric(
                    "Cooling ≤ 1 km",
                    "N/A",
                )


        with coverage_col4:

            value = ward.get(
                "cooling_centers_within_2km",
                None,
            )


            if pd.notna(value):

                st.metric(
                    "Cooling ≤ 2 km",
                    int(value),
                )

            else:

                st.metric(
                    "Cooling ≤ 2 km",
                    "N/A",
                )


        st.caption(
            "Resource-access indicators are based on "
            "the mapped hospital and cooling-centre datasets."
        )


        # ====================================================
        # RECOMMENDED ACTION
        # ====================================================

        st.markdown(
            "### Recommended action"
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
            "### Risk composition"
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
        "Select a ward on the map to view its "
        "heat-health intelligence and response resources."
    )


# ============================================================
# TARGETED ALERT PLANNING
# ============================================================

st.divider()

st.subheader(
    "Targeted Alert Planning"
)


high_risk = map_risk[
    map_risk["Risk_Category"].isin(
        ["High", "Very High"]
    )
].copy()


high_risk_count = high_risk[
    "Ward_No"
].nunique()


very_high_count = high_risk[
    high_risk["Risk_Category"]
    == "Very High"
]["Ward_No"].nunique()


# ============================================================
# POPULATION IN HIGH-RISK WARDS
# ============================================================

if "TotalPop" in high_risk.columns:

    high_risk_population = (
        pd.to_numeric(
            high_risk["TotalPop"],
            errors="coerce",
        )
        .fillna(0)
        .sum()
    )

    high_risk_population = int(
        round(high_risk_population)
    )

else:

    high_risk_population = None


if high_risk_count > 0:

    if high_risk_population is not None:

        st.warning(
            f"""
            **{high_risk_count} MCD wards require targeted
            heat-risk attention for
            {selected_date.strftime('%d %B')}.**

            This includes **{very_high_count} Very High-risk wards**
            covering approximately
            **{high_risk_population:,} residents**.

            The population figure represents residents living
            in wards classified as High or Very High risk; it
            is not an estimate of illness or mortality.
            """
        )

    else:

        st.warning(
            f"""
            **{high_risk_count} MCD wards require targeted
            heat-risk attention for
            {selected_date.strftime('%d %B')}.**

            This includes **{very_high_count} Very High-risk wards**.
            """
        )

else:

    st.success(
        "No MCD wards are currently classified as High or Very High."
    )


# ============================================================
# ALERT PREPARATION BUTTON
# ============================================================

if high_risk_count > 0:

    if st.button(
        "Prepare targeted alerts",
        type="primary",
        use_container_width=True,
    ):

        alert_wards = (

            high_risk[

                [

                    "Ward_No",

                    "WardName",

                    "Risk_Category",

                    "Human_Heat_Risk",

                ]

            ]

            .sort_values(

                "Human_Heat_Risk",

                ascending=False,

            )

        )


        ward_list = ", ".join(

            str(int(x))

            for x in alert_wards[
                "Ward_No"
            ]

        )


        st.success(
            "Targeted alert list prepared."
        )


        st.markdown(
            f"""
            ### Alert preparation —
            {selected_date.strftime('%d %B %Y')}

            **Priority wards**

            {ward_list}

            **Suggested resident message**

            > **Heat-health alert:** High heat stress is
            > forecast for your ward. Residents are advised
            > to stay hydrated, avoid prolonged outdoor
            > exposure during peak heat, and use nearby
            > cooling facilities where available. Extra
            > attention should be given to vulnerable
            > residents.

            **Operational use**

            This list can be provided to the relevant
            communication system for targeted resident
            messaging.
            """
        )


        st.dataframe(

            alert_wards,

            use_container_width=True,

            hide_index=True,

        )


# ============================================================
# SPATIAL COVERAGE
# ============================================================

st.divider()

st.subheader(
    "Spatial Coverage"
)


col1, col2, col3 = st.columns(3)


with col1:

    st.metric(
        "MCD wards",
        risk["Ward_No"].nunique(),
    )


with col2:

    st.metric(
        "Forecast",
        f"{lead_time}-day",
    )


with col3:

    st.metric(
        "Target date",
        selected_date.strftime(
            "%d %b %Y"
        ),
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

st.subheader(
    "Risk Summary"
)


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

    .rename_axis(
        "Risk Level"
    )

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

if not high_risk.empty:

    st.subheader(
        "High-Risk Wards"
    )


    high_risk_display_columns = [

        "Ward_No",

        "WardName",

        "Risk_Category",

    ]


    if "TotalPop" in high_risk.columns:

        high_risk_display_columns.append(
            "TotalPop"
        )


    high_risk_display_columns += [

        "forecast_wbgt_max_C",

        "WBGT_Hazard_Score",

        "Vulnerability_Score",

        "Response_Gap_Score",

        "Human_Heat_Risk",

    ]


    high_risk_display = high_risk[
        high_risk_display_columns
    ].sort_values(

        "Human_Heat_Risk",

        ascending=False,

    )


    if "TotalPop" in high_risk_display.columns:

        high_risk_display["TotalPop"] = (
            pd.to_numeric(
                high_risk_display["TotalPop"],
                errors="coerce",
            )
            .round()
            .astype("Int64")
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
    "Delhi Heat-Health Platform · "
    "Predict → Warn → Protect → Rescue"
)