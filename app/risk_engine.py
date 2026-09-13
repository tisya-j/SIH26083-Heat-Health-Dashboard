
import joblib
import numpy as np
import pandas as pd
from pathlib import Path

from weather import get_delhi_forecast, prepare_weather_for_rf


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

MODEL_PATH = BASE_DIR / "model" / "random_forest.pkl"

STATIC_SCORES_PATH = (
    BASE_DIR
    / "data"
    / "ward_static_scores.csv"
)

HAZARD_REFERENCE_PATH = (
    BASE_DIR
    / "data"
    / "wbgt_hazard_reference.csv"
)


# ============================================================
# LOAD TRAINED RANDOM FOREST
# ============================================================

def load_model():

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model not found:\n{MODEL_PATH}"
        )

    print("Loading trained Random Forest...")

    model = joblib.load(MODEL_PATH)

    print("Model loaded successfully.")

    return model


# ============================================================
# LOAD STATIC WARD SCORES
# ============================================================

def load_static():

    if not STATIC_SCORES_PATH.exists():
        raise FileNotFoundError(
            f"Ward static scores file not found:\n"
            f"{STATIC_SCORES_PATH}"
        )

    print("\nLoading ward static scores...")

    static_scores = pd.read_csv(
        STATIC_SCORES_PATH
    )

    static_scores["Ward_No"] = pd.to_numeric(
        static_scores["Ward_No"],
        errors="coerce"
    )

    static_scores = static_scores.dropna(
        subset=["Ward_No"]
    )

    static_scores["Ward_No"] = (
        static_scores["Ward_No"].astype(int)
    )

    print(
        f"Loaded static scores for "
        f"{static_scores['Ward_No'].nunique()} wards."
    )

    print("\nStatic Heat Score:")

    print(
        "  min:",
        round(
            static_scores["Static_Heat_Score"].min(),
            4
        ),
        "max:",
        round(
            static_scores["Static_Heat_Score"].max(),
            4
        )
    )

    print("Vulnerability Score:")

    print(
        "  min:",
        round(
            static_scores["Vulnerability_Score"].min(),
            4
        ),
        "max:",
        round(
            static_scores["Vulnerability_Score"].max(),
            4
        )
    )

    print("Response Gap Score:")

    print(
        "  min:",
        round(
            static_scores["Response_Gap_Score"].min(),
            4
        ),
        "max:",
        round(
            static_scores["Response_Gap_Score"].max(),
            4
        )
    )

    return static_scores


# ============================================================
# LOAD HISTORICAL WBGT HAZARD REFERENCE
# ============================================================

def load_hazard_reference():

    if not HAZARD_REFERENCE_PATH.exists():
        raise FileNotFoundError(
            f"WBGT hazard reference file not found:\n"
            f"{HAZARD_REFERENCE_PATH}"
        )

    print("\nLoading WBGT hazard reference...")

    reference = pd.read_csv(
        HAZARD_REFERENCE_PATH
    )

    reference = (
        reference
        .dropna()
        .sort_values("forecast_wbgt_max_C")
        .reset_index(drop=True)
    )

    print(
        f"Hazard reference points: "
        f"{len(reference)}"
    )

    return reference


# ============================================================
# WBGT → HAZARD SCORE
# ============================================================

def wbgt_to_hazard(
    wbgt_values,
    reference
):

    x = reference[
        "forecast_wbgt_max_C"
    ].values

    y = reference[
        "WBGT_Hazard_Score"
    ].values

    return np.interp(
        wbgt_values,
        x,
        y,
        left=y[0],
        right=y[-1]
    )


# ============================================================
# PREDICT FUTURE HOURLY WBGT
# ============================================================

def predict_future_wbgt():

    model = load_model()

    print(
        "\nFetching Delhi weather forecast..."
    )

    weather = get_delhi_forecast()

    print(
        f"Weather rows received: "
        f"{len(weather)}"
    )

    weather = prepare_weather_for_rf(
        weather
    )

    if weather.empty:
        raise ValueError(
            "No weather data remained after "
            "preparing the 1–5 day forecast."
        )

    print(
        f"Weather rows for 1–5 day prediction: "
        f"{len(weather)}"
    )

    # Exact features used during RF training
    rf_features = [
        "temp_forecast_C",
        "rh_forecast_pct",
        "wind_forecast_ms",
        "solar_forecast_wm2",
        "lead_time_days",
    ]

    missing_features = [
        column
        for column in rf_features
        if column not in weather.columns
    ]

    if missing_features:
        raise ValueError(
            "Weather data is missing these RF features:\n"
            f"{missing_features}"
        )

    print(
        "\nRunning Random Forest predictions..."
    )

    weather[
        "RF_WBGT_Predicted_C"
    ] = model.predict(
        weather[rf_features]
    )

    print(
        "Hourly WBGT prediction successful."
    )

    return weather


# ============================================================
# CREATE HOURLY RISK
# ============================================================

def create_hourly_risk():

    """
    Creates ward-level hourly Human Heat Risk
    for the next 1–5 forecast days.

    The risk formulation remains:

        Future Heat Hazard =
            70% dynamic WBGT hazard
            30% static spatial heat

        Human Heat Risk =
            50% future heat hazard
            30% vulnerability
            20% response gap
    """

    print(
        "\n"
        + "=" * 60
    )

    print(
        "CREATING HOURLY RISK DATASET"
    )

    print(
        "=" * 60
    )

    # --------------------------------------------------------
    # 1. Load ward static scores
    # --------------------------------------------------------

    static = load_static()

    # --------------------------------------------------------
    # 2. Generate hourly RF predictions
    # --------------------------------------------------------

    weather = predict_future_wbgt()

    # --------------------------------------------------------
    # 3. Load historical hazard reference
    # --------------------------------------------------------

    reference = load_hazard_reference()

    # --------------------------------------------------------
    # 4. Convert hourly WBGT → hazard
    # --------------------------------------------------------

    weather[
        "WBGT_Hazard_Score"
    ] = wbgt_to_hazard(
        weather["RF_WBGT_Predicted_C"],
        reference,
    )

    # --------------------------------------------------------
    # 5. Combine hourly weather with every ward
    # --------------------------------------------------------

    static["_key"] = 1
    weather["_key"] = 1

    result = static.merge(
        weather,
        on="_key",
        how="inner",
    )

    result.drop(
        columns="_key",
        inplace=True,
    )

    # --------------------------------------------------------
    # 6. FUTURE HEAT HAZARD
    # --------------------------------------------------------

    result[
        "Future_Heat_Hazard"
    ] = (
        0.70
        * result["WBGT_Hazard_Score"]

        + 0.30
        * result["Static_Heat_Score"]
    )

    # --------------------------------------------------------
    # 7. HUMAN HEAT RISK
    # --------------------------------------------------------

    result[
        "Human_Heat_Risk"
    ] = (
        0.50
        * result["Future_Heat_Hazard"]

        + 0.30
        * result["Vulnerability_Score"]

        + 0.20
        * result["Response_Gap_Score"]
    )

    # --------------------------------------------------------
    # 8. RISK CATEGORY
    # --------------------------------------------------------

    result[
        "Risk_Category"
    ] = pd.cut(
        result["Human_Heat_Risk"],

        bins=[
            -np.inf,
            0.20,
            0.40,
            0.60,
            0.80,
            np.inf,
        ],

        labels=[
            "Very Low",
            "Low",
            "Moderate",
            "High",
            "Very High",
        ],

        right=True,
    )

    # --------------------------------------------------------
    # 9. Clean column order
    # --------------------------------------------------------

    preferred_columns = [
        "Ward_No",
        "WardName",
        "target_date",
        "lead_time_days",
        "time",

        "temp_forecast_C",
        "rh_forecast_pct",
        "wind_forecast_ms",
        "solar_forecast_wm2",

        "RF_WBGT_Predicted_C",
        "WBGT_Hazard_Score",

        "Static_Heat_Score",
        "Vulnerability_Score",
        "Response_Gap_Score",

        "Future_Heat_Hazard",
        "Human_Heat_Risk",
        "Risk_Category",
    ]

    result = result[
        [
            column
            for column in preferred_columns
            if column in result.columns
        ]
    ]

    # --------------------------------------------------------
    # 10. Diagnostics
    # --------------------------------------------------------

    print(
        "\n"
        + "=" * 60
    )

    print(
        "HOURLY RISK DATASET CREATED SUCCESSFULLY"
    )

    print(
        "=" * 60
    )

    print(
        "\nShape:"
    )

    print(
        result.shape
    )

    print(
        "\nUnique wards:"
    )

    print(
        result["Ward_No"].nunique()
    )

    print(
        "\nForecast dates:"
    )

    print(
        result["target_date"].nunique()
    )

    print(
        "\nHourly timestamps:"
    )

    print(
        result["time"].nunique()
    )

    print(
        "\nRisk distribution:"
    )

    print(
        result[
            "Risk_Category"
        ]
        .value_counts()
        .sort_index()
    )

    return result


# ============================================================
# FIND PEAK RISK PERIOD
# ============================================================

def format_hour(timestamp):
    """
    Windows-safe time formatting.

    Example:
        13:00 → 1 PM
    """

    return pd.Timestamp(timestamp).strftime(
        "%I %p"
    ).lstrip("0")


def find_peak_risk_period(
    hourly_risk,
    ward_no,
    target_date
):

    """
    Find the highest-risk contiguous 3-hour period
    for a ward on a particular forecast date.

    The period is selected using the rolling 3-hour
    average of Human_Heat_Risk rather than a single
    maximum-risk hour.

    Returns:

        peak_time
            Timestamp corresponding to the final hour
            of the selected 3-hour window.

        peak_risk
            Average Human Heat Risk across the window.

        peak_wbgt
            Maximum predicted WBGT within the window.

        start_time
            Formatted start time.

        end_time
            Formatted end time.

        period_label
            Human-readable period such as:
            "12 PM – 3 PM"
    """

    # --------------------------------------------------------
    # 1. Filter to selected ward and date
    # --------------------------------------------------------

    rows = hourly_risk[
        (hourly_risk["Ward_No"] == ward_no)
        & (
            pd.to_datetime(
                hourly_risk["target_date"]
            ).dt.date
            == pd.Timestamp(
                target_date
            ).date()
        )
    ].copy()

    if rows.empty:
        return None

    # --------------------------------------------------------
    # 2. Ensure chronological order
    # --------------------------------------------------------

    rows["time"] = pd.to_datetime(
        rows["time"]
    )

    rows = (
        rows
        .sort_values("time")
        .reset_index(drop=True)
    )

    # --------------------------------------------------------
    # 3. Calculate rolling 3-hour average risk
    # --------------------------------------------------------

    rows["risk_3h"] = (
        rows["Human_Heat_Risk"]
        .rolling(
            window=3,
            min_periods=3
        )
        .mean()
    )

    valid = rows.dropna(
        subset=["risk_3h"]
    ).copy()

    if valid.empty:
        return None

    # --------------------------------------------------------
    # 4. Find highest-risk 3-hour window
    # --------------------------------------------------------

    peak_index = valid[
        "risk_3h"
    ].idxmax()

    peak_row = valid.loc[
        peak_index
    ]

    # The rolling window ends at this timestamp.
    end_timestamp = peak_row["time"]

    # Therefore the 3-hour window begins two hours earlier.
    start_timestamp = (
        end_timestamp
        - pd.Timedelta(hours=2)
    )

    # --------------------------------------------------------
    # 5. Extract the actual three rows
    # --------------------------------------------------------

    window = rows[
        (rows["time"] >= start_timestamp)
        & (rows["time"] <= end_timestamp)
    ].copy()

    if window.empty:
        return None

    # --------------------------------------------------------
    # 6. Calculate window statistics
    # --------------------------------------------------------

    peak_risk = float(
        window["Human_Heat_Risk"].mean()
    )

    # IMPORTANT:
    # The hourly dataset uses RF_WBGT_Predicted_C,
    # not forecast_wbgt_C.
    peak_wbgt = float(
        window["RF_WBGT_Predicted_C"].max()
    )

    # Display the period as an interval.
    # Example:
    # 12 PM – 3 PM
    #
    # The three observations are:
    # 12 PM
    # 1 PM
    # 2 PM
    #
    # So the period ends at 3 PM.
    display_end = (
        end_timestamp
        + pd.Timedelta(hours=1)
    )

    # --------------------------------------------------------
    # 7. Return result
    # --------------------------------------------------------

    return {
        "peak_time": end_timestamp,

        "peak_risk": peak_risk,

        "peak_wbgt": peak_wbgt,

        "start_time": format_hour(
            start_timestamp
        ),

        "end_time": format_hour(
            display_end
        ),

        "period_label": (
            f"{format_hour(start_timestamp)} – "
            f"{format_hour(display_end)}"
        ),
    }


# ============================================================
# CREATE DAILY HAZARD
# ============================================================

def create_daily_hazard():

    weather = predict_future_wbgt()

    daily = (
        weather
        .groupby(
            [
                "target_date",
                "lead_time_days",
            ],
            as_index=False,
        )
        .agg(

            forecast_wbgt_max_C=(
                "RF_WBGT_Predicted_C",
                "max",
            ),

            forecast_wbgt_mean_C=(
                "RF_WBGT_Predicted_C",
                "mean",
            ),

            forecast_temp_max_C=(
                "temp_forecast_C",
                "max",
            ),

            forecast_temp_mean_C=(
                "temp_forecast_C",
                "mean",
            ),

            forecast_rh_mean_pct=(
                "rh_forecast_pct",
                "mean",
            ),

            forecast_rh_max_pct=(
                "rh_forecast_pct",
                "max",
            ),

            forecast_wind_mean_ms=(
                "wind_forecast_ms",
                "mean",
            ),

            forecast_solar_mean_wm2=(
                "solar_forecast_wm2",
                "mean",
            ),
        )
    )

    print(
        f"\nDaily forecast scenarios: "
        f"{len(daily)}"
    )

    reference = load_hazard_reference()

    daily[
        "WBGT_Hazard_Score"
    ] = wbgt_to_hazard(
        daily["forecast_wbgt_max_C"],
        reference,
    )

    return daily


# ============================================================
# CREATE LIVE RISK DATASET
# ============================================================

def create_live_risk_dataset():

    print(
        "\n"
        + "=" * 60
    )

    print(
        "CREATING LIVE RISK DATASET"
    )

    print(
        "=" * 60
    )

    # --------------------------------------------------------
    # 1. Load static ward scores
    # --------------------------------------------------------

    static = load_static()

    # --------------------------------------------------------
    # 2. Generate live weather → WBGT → hazard
    # --------------------------------------------------------

    daily = create_daily_hazard()

    # --------------------------------------------------------
    # 3. Cross join
    #
    # 250 wards × forecast scenarios
    # --------------------------------------------------------

    static["_key"] = 1
    daily["_key"] = 1

    result = static.merge(
        daily,
        on="_key",
        how="inner",
    )

    result.drop(
        columns="_key",
        inplace=True,
    )

    # --------------------------------------------------------
    # 4. FUTURE HEAT HAZARD
    # --------------------------------------------------------

    result[
        "Future_Heat_Hazard"
    ] = (
        0.70
        * result["WBGT_Hazard_Score"]

        + 0.30
        * result["Static_Heat_Score"]
    )

    # --------------------------------------------------------
    # 5. HUMAN HEAT RISK
    # --------------------------------------------------------

    result[
        "Human_Heat_Risk"
    ] = (
        0.50
        * result["Future_Heat_Hazard"]

        + 0.30
        * result["Vulnerability_Score"]

        + 0.20
        * result["Response_Gap_Score"]
    )

    # --------------------------------------------------------
    # 6. RISK CATEGORY
    # --------------------------------------------------------

    result[
        "Risk_Category"
    ] = pd.cut(
        result["Human_Heat_Risk"],

        bins=[
            -np.inf,
            0.20,
            0.40,
            0.60,
            0.80,
            np.inf,
        ],

        labels=[
            "Very Low",
            "Low",
            "Moderate",
            "High",
            "Very High",
        ],

        right=True,
    )

    # --------------------------------------------------------
    # 7. Diagnostics
    # --------------------------------------------------------

    print(
        "\n"
        + "=" * 60
    )

    print(
        "LIVE RISK DATASET CREATED SUCCESSFULLY"
    )

    print(
        "=" * 60
    )

    print(
        "\nShape:"
    )

    print(
        result.shape
    )

    print(
        "\nUnique wards:"
    )

    print(
        result["Ward_No"].nunique()
    )

    print(
        "\nForecast dates:"
    )

    print(
        result[
            "target_date"
        ].nunique()
    )

    print(
        "\nRisk distribution:"
    )

    print(
        result[
            "Risk_Category"
        ]
        .value_counts()
        .sort_index()
    )

    return result

