import math

import pandas as pd
import streamlit as st

from risk_engine import find_peak_risk_period


# ============================================================
# RISK INFORMATION
# ============================================================

RISK_INFO = {
    "Very Low": {
        "title": "Very low heat risk",
        "message": (
            "Heat conditions in your area are expected to be relatively mild."
        ),
        "actions": [
            "Stay hydrated, especially if spending time outdoors.",
            "Use shade when available.",
        ],
    },

    "Low": {
        "title": "Low heat risk",
        "message": (
            "Some heat stress may occur, particularly during longer "
            "periods outdoors."
        ),
        "actions": [
            "Carry water when going outdoors.",
            "Take breaks in shade or cooler places.",
            "Stay hydrated throughout the day.",
        ],
    },

    "Moderate": {
        "title": "Moderate heat risk",
        "message": (
            "Heat conditions may become uncomfortable and stressful, "
            "especially during the highest-risk part of the day."
        ),
        "actions": [
            "Carry water if you are going outdoors.",
            "Avoid unnecessary strenuous activity during the highest-risk period.",
            "Take breaks in shade or cool spaces.",
            "Check on older family members and young children.",
        ],
    },

    "High": {
        "title": "High heat risk",
        "message": (
            "Heat conditions are expected to be stressful in your area. "
            "Extra care is recommended, especially during the highest-risk period."
        ),
        "actions": [
            "Avoid unnecessary outdoor activity during the highest-risk period.",
            "Carry water and drink regularly.",
            "Use shade, air-conditioned spaces or other cool places when possible.",
            "Check on older adults, children and anyone who may need extra help.",
        ],
    },

    "Very High": {
        "title": "Very high heat risk",
        "message": (
            "Your area is expected to experience particularly stressful "
            "heat conditions. Avoid prolonged outdoor exposure where possible."
        ),
        "actions": [
            "Avoid unnecessary outdoor activity.",
            "Stay in a cool or shaded place as much as possible.",
            "Drink water regularly.",
            "Check on older adults, children and other vulnerable people.",
            "Plan access to medical or cooling support before going out.",
        ],
    },
}


# ============================================================
# HELPERS
# ============================================================

def format_date(date_value):
    """Format a date in a citizen-friendly way."""
    return pd.Timestamp(date_value).strftime("%A, %d %B %Y")


def format_hour(timestamp):
    """Format a timestamp as e.g. 1 PM."""
    return pd.Timestamp(timestamp).strftime("%I %p").lstrip("0")


def haversine_km(lat1, lon1, lat2, lon2):
    """Calculate distance between two latitude/longitude points."""

    R = 6371.0

    lat1 = math.radians(float(lat1))
    lon1 = math.radians(float(lon1))
    lat2 = math.radians(float(lat2))
    lon2 = math.radians(float(lon2))

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(dlon / 2) ** 2
    )

    return 2 * R * math.asin(math.sqrt(a))


def get_ward_centroid(boundaries, ward_no):
    """Get the centroid of a ward from its actual geometry."""

    ward = boundaries[
        boundaries["Ward_No"].astype(str) == str(ward_no)
    ].copy()

    if ward.empty:
        return None, None

    geometry = ward.iloc[0]["geometry"]

    if geometry is None or geometry.is_empty:
        return None, None

    centroid = geometry.centroid

    return centroid.y, centroid.x


def find_nearest_facility(ward_lat, ward_lon, facilities):
    """Find nearest facility using haversine distance."""

    if ward_lat is None or ward_lon is None:
        return None

    if facilities is None or facilities.empty:
        return None

    results = facilities.copy()

    results["distance_km"] = results.apply(
        lambda row: haversine_km(
            ward_lat,
            ward_lon,
            row["lat"],
            row["lon"],
        ),
        axis=1,
    )

    nearest = results.sort_values("distance_km").iloc[0]

    return {
        "name": nearest["name"],
        "lat": float(nearest["lat"]),
        "lon": float(nearest["lon"]),
        "distance_km": float(nearest["distance_km"]),
        "facility_type": nearest.get("facility_type", None),
    }


def get_resource_counts(static_row):
    """Read precomputed accessibility counts."""

    def safe_int(column):
        value = static_row.get(column, 0)

        if pd.isna(value):
            return 0

        try:
            return int(value)
        except Exception:
            return 0

    return {
        "hospitals_2km": safe_int("hospitals_within_2km"),
        "beds_5km": safe_int("hospital_beds_within_5km"),
        "cooling_1km": safe_int("cooling_centers_within_1km"),
        "cooling_2km": safe_int("cooling_centers_within_2km"),
    }


# ============================================================
# MAIN CITIZEN DASHBOARD
# ============================================================

def show_citizen_dashboard(
    risk,
    static,
    boundaries,
    hospitals,
    cooling_centres,
    hourly_risk=None,
):
    """
    Citizen-facing heat-health dashboard.

    Main purpose:
        Show a resident their area's forecast risk,
        identify the highest-risk period,
        provide practical preventive guidance,
        and show nearby support resources.

    Technical model information remains inside an expander.
    """

    # --------------------------------------------------------
    # HEADER
    # --------------------------------------------------------

    st.markdown("## Check Your Area")

    st.caption(
        "View your ward's heat outlook, identify the highest-risk period, "
        "and plan accordingly."
    )

    st.divider()

    # --------------------------------------------------------
    # WARD SELECTION
    # --------------------------------------------------------

    ward_lookup = (
        static[["Ward_No", "WardName"]]
        .drop_duplicates()
        .sort_values("Ward_No")
        .copy()
    )

    ward_lookup["label"] = ward_lookup.apply(
        lambda row: (
            f"Ward {int(row['Ward_No'])} — {row['WardName']}"
        ),
        axis=1,
    )

    ward_options = ward_lookup["label"].tolist()

    if not ward_options:
        st.error("No ward information is available.")
        return

    selected_label = st.selectbox(
        "Select your ward",
        ward_options,
    )

    selected_ward = int(
        ward_lookup.loc[
            ward_lookup["label"] == selected_label,
            "Ward_No",
        ].iloc[0]
    )

    selected_ward_name = ward_lookup.loc[
        ward_lookup["Ward_No"] == selected_ward,
        "WardName",
    ].iloc[0]

    # --------------------------------------------------------
    # DATE SELECTION
    # --------------------------------------------------------

    ward_dates = (
        risk[
            risk["Ward_No"] == selected_ward
        ]["target_date"]
        .dropna()
        .drop_duplicates()
        .sort_values()
        .tolist()
    )

    if not ward_dates:
        st.warning("No forecast is available for this ward.")
        return

    ward_dates = [
        pd.Timestamp(d).date()
        for d in ward_dates
    ]

    selected_date = st.selectbox(
        "Forecast date",
        ward_dates,
        format_func=lambda d: pd.Timestamp(d).strftime(
            "%A, %d %B %Y"
        ),
    )

    # --------------------------------------------------------
    # GET DAILY WARD RESULT
    # --------------------------------------------------------

    ward_rows = risk[
        (risk["Ward_No"] == selected_ward)
        & (
            pd.to_datetime(risk["target_date"]).dt.date
            == selected_date
        )
    ].copy()

    if ward_rows.empty:
        st.warning(
            "No forecast is available for this ward and date."
        )
        return

    ward_rows = ward_rows.sort_values("lead_time_days")

    ward = ward_rows.iloc[0]

    # --------------------------------------------------------
    # RISK CATEGORY
    # --------------------------------------------------------

    risk_category = str(
        ward.get("Risk_Category", "Moderate")
    )

    info = RISK_INFO.get(
        risk_category,
        RISK_INFO["Moderate"],
    )

    forecast_date_text = format_date(selected_date)

    # --------------------------------------------------------
    # FIND HOURLY PEAK PERIOD
    # --------------------------------------------------------

    peak = None

    if hourly_risk is not None and not hourly_risk.empty:

        peak = find_peak_risk_period(
            hourly_risk,
            selected_ward,
            selected_date,
        )

    # --------------------------------------------------------
    # MAIN OUTLOOK
    # --------------------------------------------------------

    st.markdown(
        f"### Heat outlook — {forecast_date_text}"
    )

    if risk_category in ["High", "Very High"]:

        st.error(
            f"**{info['title']}**\n\n"
            f"{info['message']}"
        )

    elif risk_category == "Moderate":

        st.warning(
            f"**{info['title']}**\n\n"
            f"{info['message']}"
        )

    else:

        st.success(
            f"**{info['title']}**\n\n"
            f"{info['message']}"
        )

    # --------------------------------------------------------
    # HIGHEST-RISK PERIOD
    # --------------------------------------------------------

    st.markdown("### Highest-risk period")

    if peak:

        st.info(
            f"**{peak['period_label']}**\n\n"
            "Predicted heat risk is highest during this period. "
            "If possible, avoid unnecessary outdoor activity at this time."
        )

    else:

        st.info(
            "The highest-risk hourly period is not currently available. "
            "As a general precaution, take extra care during the hottest "
            "part of the afternoon."
        )

    # --------------------------------------------------------
    # DAILY PLANNING
    # --------------------------------------------------------

    st.markdown("### Daily planning")

    if peak:

        start_hour = (
            pd.Timestamp(peak["peak_time"])
            - pd.Timedelta(hours=2)
        )

        end_hour = (
            pd.Timestamp(peak["peak_time"])
            + pd.Timedelta(hours=1)
        )

        plan_col1, plan_col2, plan_col3 = st.columns(3)

        with plan_col1:
            st.markdown("**Before the highest-risk period**")
            st.write(
                f"If you need to complete outdoor tasks, "
                f"consider doing them before {format_hour(start_hour)}."
            )

        with plan_col2:
            st.markdown("**During the highest-risk period**")
            st.write(
                f"Take extra care between "
                f"{format_hour(start_hour)} and {format_hour(end_hour)}. "
                "Avoid unnecessary outdoor activity where possible."
            )

        with plan_col3:
            st.markdown("**After the highest-risk period**")
            st.write(
                "Continue to stay hydrated and take breaks "
                "if you remain outdoors."
            )

    else:

        plan_col1, plan_col2, plan_col3 = st.columns(3)

        with plan_col1:
            st.markdown("**Morning**")
            st.write(
                "If possible, plan outdoor tasks earlier in the day."
            )

        with plan_col2:
            st.markdown("**Afternoon**")
            st.write(
                "Take extra care during the hottest part of the day."
            )

        with plan_col3:
            st.markdown("**Evening**")
            st.write(
                "Continue to stay hydrated, particularly "
                "if you have been outdoors."
            )

    # --------------------------------------------------------
    # RECOMMENDED PRECAUTIONS
    # --------------------------------------------------------

    st.markdown("### Recommended precautions")

    for action in info["actions"]:
        st.markdown(f"- {action}")

    # --------------------------------------------------------
    # PREPARATION
    # --------------------------------------------------------

    if risk_category in ["High", "Very High"]:

        st.markdown("### Prepare in advance")

        st.warning(
            "If you need to go out, plan before leaving. "
            "Carry water, identify a cool place where you can take "
            "a break, and avoid prolonged outdoor exposure during "
            "the highest-risk period."
        )

    elif risk_category == "Moderate":

        st.markdown("### Preparation")

        st.info(
            "If you expect to spend time outdoors, carry water "
            "and plan access to shade or a cool place."
        )

    # --------------------------------------------------------
    # STATIC WARD INFORMATION
    # --------------------------------------------------------

    static_rows = static[
        static["Ward_No"] == selected_ward
    ].copy()

    static_row = (
        static_rows.iloc[0]
        if not static_rows.empty
        else pd.Series(dtype="object")
    )

    counts = get_resource_counts(static_row)

    # --------------------------------------------------------
    # FIND WARD CENTROID
    # --------------------------------------------------------

    ward_lat, ward_lon = get_ward_centroid(
        boundaries,
        selected_ward,
    )

    nearest_hospital = find_nearest_facility(
        ward_lat,
        ward_lon,
        hospitals,
    )

    nearest_cooling = find_nearest_facility(
        ward_lat,
        ward_lon,
        cooling_centres,
    )

    # --------------------------------------------------------
    # LOCAL SUPPORT
    # --------------------------------------------------------

    st.divider()

    st.markdown("## Local support")

    # ---------------- HOSPITAL ----------------

    st.markdown("### Nearest hospital")

    if nearest_hospital:

        col1, col2 = st.columns([2, 1])

        with col1:
            st.markdown(
                f"**{nearest_hospital['name']}**"
            )

        with col2:
            st.metric(
                "Approx. distance",
                f"{nearest_hospital['distance_km']:.1f} km",
            )

        maps_url = (
            "https://www.google.com/maps/dir/?api=1"
            f"&destination={nearest_hospital['lat']},"
            f"{nearest_hospital['lon']}"
        )

        st.link_button(
            "Get directions",
            maps_url,
            use_container_width=True,
        )

    else:

        st.info(
            "Hospital location information is not available "
            "for this ward."
        )

    st.caption(
        f"Hospitals within 2 km: **{counts['hospitals_2km']}**"
    )

    st.caption(
        f"Hospital beds within 5 km: **{counts['beds_5km']}**"
    )

    # ---------------- COOLING SUPPORT ----------------

    st.markdown("### Cooling support")

    if nearest_cooling:

        col1, col2 = st.columns([2, 1])

        with col1:

            st.markdown(
                f"**{nearest_cooling['name']}**"
            )

            facility_type = nearest_cooling.get(
                "facility_type",
                None,
            )

            if pd.notna(facility_type):

                readable_type = str(
                    facility_type
                ).replace("_", " ").title()

                st.caption(
                    f"Listed as a {readable_type.lower()}."
                )

        with col2:

            st.metric(
                "Approx. distance",
                f"{nearest_cooling['distance_km']:.1f} km",
            )

        maps_url = (
            "https://www.google.com/maps/dir/?api=1"
            f"&destination={nearest_cooling['lat']},"
            f"{nearest_cooling['lon']}"
        )

        st.link_button(
            "Get directions",
            maps_url,
            use_container_width=True,
        )

        st.caption(
            "These are listed cooling-support locations in the "
            "prototype dataset and should not be assumed to be "
            "officially designated cooling centres."
        )

    else:

        st.info(
            "Cooling-support location information is not "
            "available for this ward."
        )

    st.caption(
        f"Cooling support within 1 km: **{counts['cooling_1km']}**"
    )

    st.caption(
        f"Cooling support within 2 km: **{counts['cooling_2km']}**"
    )

    # --------------------------------------------------------
    # TECHNICAL DETAILS
    # --------------------------------------------------------

    st.divider()

    with st.expander("How the forecast is calculated"):

        st.write(
            "The platform combines forecast thermal conditions "
            "with local heat exposure, population vulnerability "
            "and access to response resources to estimate "
            "ward-level human heat risk."
        )

        st.markdown("**Forecast thermal stress**")

        if peak:

            st.write(
                f"Highest predicted WBGT during the selected "
                f"3-hour period: **{peak['peak_wbgt']:.1f} °C**"
            )

        else:

            wbgt = ward.get(
                "forecast_wbgt_max_C",
                None,
            )

            if pd.notna(wbgt):

                st.write(
                    f"Forecast WBGT maximum: "
                    f"**{float(wbgt):.1f} °C**"
                )

        st.markdown("**Risk components**")

        if "Future_Heat_Hazard" in ward:

            st.write(
                f"Future heat hazard: "
                f"**{float(ward['Future_Heat_Hazard']):.3f}**"
            )

        if "Vulnerability_Score" in ward:

            st.write(
                f"Population vulnerability: "
                f"**{float(ward['Vulnerability_Score']):.3f}**"
            )

        if "Response_Gap_Score" in ward:

            st.write(
                f"Response gap: "
                f"**{float(ward['Response_Gap_Score']):.3f}**"
            )

        st.markdown(
            "**Important:** Human Heat Risk is a ward-level "
            "prioritisation index. It is **not** a probability "
            "that an individual will become ill."
        )

    # --------------------------------------------------------
    # DISCLAIMER
    # --------------------------------------------------------

    st.caption(
        "This tool provides area-level heat-risk information "
        "and general preventive guidance. It does not provide "
        "personal medical advice or diagnose heat-related illness."
    )