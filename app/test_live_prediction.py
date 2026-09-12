from risk_engine import create_live_risk_dataset


print("Starting live prediction...")
print("=" * 60)

result = create_live_risk_dataset()

print("\nSUCCESS!")

print("\nShape:")
print(result.shape)

print("\nForecast dates:")
print(
    result[
        [
            "target_date",
            "lead_time_days"
        ]
    ]
    .drop_duplicates()
    .sort_values("lead_time_days")
    .to_string(index=False)
)

print("\nRisk distribution:")
print(
    result["Risk_Category"]
    .value_counts()
    .sort_index()
)

print("\nTop 10 wards:")
print(
    result[
        [
            "Ward_No",
            "target_date",
            "lead_time_days",
            "forecast_wbgt_max_C",
            "WBGT_Hazard_Score",
            "Vulnerability_Score",
            "Response_Gap_Score",
            "Human_Heat_Risk",
            "Risk_Category"
        ]
    ]
    .sort_values(
        "Human_Heat_Risk",
        ascending=False
    )
    .head(10)
    .to_string(index=False)
)