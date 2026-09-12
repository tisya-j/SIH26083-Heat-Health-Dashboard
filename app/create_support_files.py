import pandas as pd
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

RISK_PATH = BASE_DIR / "data" / "final_ward_risk_dataset_RF.csv"
DATA_DIR = BASE_DIR / "data"


# ============================================================
# 1. CREATE WARD STATIC SCORES
# ============================================================

print("=" * 60)
print("CREATING WARD STATIC SCORE FILE")
print("=" * 60)

static_scores = pd.read_csv(
    RISK_PATH,
    usecols=[
        "Ward_No",
        "Static_Heat_Score",
        "Vulnerability_Score",
        "Response_Gap_Score",
    ],
)

static_scores = (
    static_scores
    .drop_duplicates(subset=["Ward_No"])
    .sort_values("Ward_No")
    .reset_index(drop=True)
)

static_path = DATA_DIR / "ward_static_scores.csv"

static_scores.to_csv(
    static_path,
    index=False
)

print(f"Created: {static_path}")
print(f"Rows: {len(static_scores)}")
print()


# ============================================================
# 2. CREATE WBGT HAZARD REFERENCE
# ============================================================

print("=" * 60)
print("CREATING WBGT HAZARD REFERENCE FILE")
print("=" * 60)

hazard_reference = pd.read_csv(
    RISK_PATH,
    usecols=[
        "forecast_wbgt_max_C",
        "WBGT_Hazard_Score",
    ],
)

hazard_reference = (
    hazard_reference
    .drop_duplicates()
    .dropna()
    .sort_values("forecast_wbgt_max_C")
    .reset_index(drop=True)
)

hazard_path = DATA_DIR / "wbgt_hazard_reference.csv"

hazard_reference.to_csv(
    hazard_path,
    index=False
)

print(f"Created: {hazard_path}")
print(f"Rows: {len(hazard_reference)}")
print()


# ============================================================
# 3. FINAL CHECK
# ============================================================

print("=" * 60)
print("SUPPORT FILES CREATED SUCCESSFULLY")
print("=" * 60)

print("\nWard static scores:")
print(static_scores.head())

print("\nWBGT hazard reference:")
print(hazard_reference.head())

print("\nFiles:")
print(static_path)
print(hazard_path)