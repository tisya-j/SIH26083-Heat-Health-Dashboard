from risk_engine import (
    create_hourly_risk,
    find_peak_risk_period,
)

print("\nSTARTING HOURLY TEST...\n")

hourly = create_hourly_risk()

print("\nFIRST 10 ROWS:")
print(hourly.head(10))

print("\nSHAPE:")
print(hourly.shape)

print("\nDATES:")
print(hourly["target_date"].unique())

print("\nHOURS:")
print(hourly["time"].min())
print(hourly["time"].max())

# Test Ward 34
ward = 34

date = hourly[
    hourly["Ward_No"] == ward
]["target_date"].min()

print(
    f"\nPEAK RISK TEST — WARD {ward}"
)

peak = find_peak_risk_period(
    hourly,
    ward,
    date,
)

print(peak)