import requests
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo


# Delhi reference coordinate used by the project
DELHI_LAT = 28.6139
DELHI_LON = 77.2090

TIMEZONE = "Asia/Kolkata"

API_URL = "https://api.open-meteo.com/v1/forecast"


def get_delhi_forecast():

    params = {
        "latitude": DELHI_LAT,
        "longitude": DELHI_LON,

        "hourly": ",".join([
            "temperature_2m",
            "relative_humidity_2m",
            "wind_speed_10m",
            "shortwave_radiation",
        ]),

        "forecast_days": 7,

        "timezone": TIMEZONE,

        # Our RF expects wind in m/s
        "wind_speed_unit": "ms",
    }

    response = requests.get(
        API_URL,
        params=params,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    hourly = data["hourly"]

    weather = pd.DataFrame({
        "time": pd.to_datetime(hourly["time"]),
        "temp_forecast_C": hourly["temperature_2m"],
        "rh_forecast_pct": hourly["relative_humidity_2m"],
        "wind_forecast_ms": hourly["wind_speed_10m"],
        "solar_forecast_wm2": hourly["shortwave_radiation"],
    })

    return weather


def prepare_weather_for_rf(weather):

    prediction_date = datetime.now(
        ZoneInfo(TIMEZONE)
    ).date()

    weather["target_date"] = weather["time"].dt.date

    # Number of days between forecast issue date and target date
    weather["lead_time_days"] = (
        pd.to_datetime(weather["target_date"])
        - pd.Timestamp(prediction_date)
    ).dt.days

    # Keep only the 1–5 day horizons used by our RF
    weather = weather[
        weather["lead_time_days"].between(1, 5)
    ].copy()

    return weather