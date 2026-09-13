from pathlib import Path
import pandas as pd
import geopandas as gpd


# Project root
BASE_DIR = Path(__file__).resolve().parent.parent

# Data paths
RISK_PATH = BASE_DIR / "data" / "final_ward_risk_dataset_RF.csv"
STATIC_PATH = BASE_DIR / "data" / "final_ward_static_features_complete.csv"
BOUNDARY_PATH = BASE_DIR / "data" / "ward_boundaries.geojson"
HOSPITAL_PATH = BASE_DIR / "data" / "hospitals.csv"
COOLING_PATH = BASE_DIR / "data" / "cooling_centres.csv"


def load_risk_data():
    return pd.read_csv(RISK_PATH)

def load_static_data():
    return pd.read_csv(STATIC_PATH)

def load_boundaries():
    return gpd.read_file(BOUNDARY_PATH)


def load_hospitals():
    return pd.read_csv(HOSPITAL_PATH)


def load_cooling_centres():
    return pd.read_csv(COOLING_PATH)