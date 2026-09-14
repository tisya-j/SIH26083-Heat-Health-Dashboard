# AI-Driven Heat-Health Intelligence for Delhi

Live Demo: https://sih26083-heat-health-dashboard-tc7h6e7ja8j3quod3aagh3.streamlit.app/

A ward-level decision-support system for forecasting thermal stress and identifying areas of elevated human heat risk across Delhi.

Developed for **Smart India Hackathon 2026 Problem Statement 26083: Extreme Heatwave Early Warning and Human Thermal Stress Index**.

## Overview

Conventional heat warnings primarily communicate how hot conditions are expected to become. This project extends that approach by combining forecast thermal stress with spatial heat exposure, population vulnerability, and access to response infrastructure.

The system produces a **Human Heat Risk** index for Delhi's 250 municipal wards and provides separate interfaces for authorities and citizens.

The core workflow is:

```text
Weather Forecast
      ↓
Random Forest Thermal-Stress Forecast
      ↓
Future Heat Hazard
      ↓
Spatial Heat Context + Population Vulnerability
      ↓
Response Accessibility Gap
      ↓
Human Heat Risk
      ↓
Ward Prioritisation and Action
```

The objective is not to predict individual medical outcomes. The Human Heat Risk score is a **decision-support index** intended to help identify wards that may require greater attention during forecast heat events.

## Key Capabilities

* Forecasts a WBGT-based thermal-stress index for **1–5 days ahead**
* Generates risk estimates across **250 Delhi municipal wards**
* Integrates weather, satellite-derived heat context, demographic vulnerability, and response accessibility
* Provides ward-level GIS visualisation
* Identifies hourly and three-hour peak-risk periods
* Displays nearby hospitals and cooling-support locations
* Provides population context for selected wards
* Supports both authority-facing and citizen-facing views
* Includes sensitivity analysis to assess the stability of ward prioritisation

## Technical Approach

### 1. Thermal-Stress Forecasting

A Random Forest Regressor is trained on historical environmental data to estimate a WBGT-based thermal-stress index.

Model inputs:

* Air temperature
* Relative humidity
* Wind speed
* Shortwave radiation
* Forecast lead time

The model uses 300 trees with median imputation and a minimum leaf size of 3.

Validation uses **time-ordered expanding-window splits** rather than random train-test splitting, reducing temporal leakage and better representing future forecasting conditions.

The model achieved approximately:

**R² = 0.77–0.80 across the 1–5 day forecast horizons**

The model was evaluated against persistence, Ridge Regression, and Extra Trees baselines.

### 2. Spatial Heat Context

Satellite-derived land surface temperature (LST) and NDVI were aggregated to the ward level.

LST provides spatial information about surface heating and urban heat patterns. It is used as a spatial heat-context variable and should not be interpreted as equivalent to air temperature.

The static heat component is derived from ward-level LST statistics, with greater emphasis placed on the upper-tail temperature distribution to capture areas experiencing stronger surface heat.

### 3. Population Vulnerability

Ward-level vulnerability incorporates percentile-normalised indicators representing:

* Population density
* Child population share
* Workforce exposure proxy
* Scheduled Caste population share

The resulting vulnerability score is used to represent differences in population-level exposure and susceptibility across wards.

### 4. Response Accessibility

The system incorporates proximity to:

* Hospitals
* Cooling-support locations

These distances are transformed into a response-gap score, allowing the system to distinguish between wards with similar heat exposure but different access to nearby support infrastructure.

Cooling-support locations are treated as available support points in the prototype and should not be interpreted as a complete or authoritative inventory of designated cooling centres.

## Human Heat Risk

The final risk index combines three components:

```text
Human Heat Risk =
    0.50 × Future Heat Hazard
  + 0.30 × Population Vulnerability
  + 0.20 × Response Accessibility Gap
```

Future Heat Hazard combines forecast thermal stress with static spatial heat context:

```text
Future Heat Hazard =
    0.70 × WBGT Hazard
  + 0.30 × Static Heat Context
```

The WBGT hazard component is calculated using an empirical percentile reference derived from historical thermal-stress values.

The resulting score is categorised as:

|  Risk score | Category  |
| ----------: | --------- |
|      ≤ 0.20 | Very Low  |
| > 0.20–0.40 | Low       |
| > 0.40–0.60 | Moderate  |
| > 0.60–0.80 | High      |
|      > 0.80 | Very High |

These categories represent **relative decision-support priorities**, not probabilities of illness, hospitalisation, or mortality.

## Data Sources

The prototype uses publicly available environmental, geographic, demographic, and infrastructure data, including:

* **ERA5-Land** — historical meteorological data
* **Open-Meteo** — forecast weather data used by the deployed prototype
* **Landsat-derived LST and NDVI** — spatial heat and vegetation context
* **Delhi ward boundaries** — 250 municipal ward geometries
* **Ward-level demographic data** — population and demographic indicators
* **Hospital locations** — response accessibility
* **Cooling-support locations** — prototype response-accessibility layer

Historical analysis includes selected heat periods from 2015, 2019, and 2022 together with a 1991–2020 climatological reference.

## System Architecture

```text
                    ┌─────────────────────┐
                    │  Historical Weather │
                    │     ERA5-Land       │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Thermal-Stress      │
                    │ Model Training      │
                    │ Random Forest       │
                    └──────────┬──────────┘
                               │
                               │
Forecast Weather ──────────────▼
                    ┌─────────────────────┐
                    │ 1–5 Day Thermal     │
                    │ Stress Forecast     │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Future Heat Hazard  │
                    │ + LST Heat Context  │
                    └──────────┬──────────┘
                               │
             ┌─────────────────┼─────────────────┐
             ▼                 ▼                 ▼
      Population          Response          Spatial Data
      Vulnerability       Accessibility     Ward Geometry
             │                 │                 │
             └─────────────────┼─────────────────┘
                               ▼
                    ┌─────────────────────┐
                    │ Human Heat Risk     │
                    │ Ward Prioritisation │
                    └──────────┬──────────┘
                               │
                ┌──────────────┴──────────────┐
                ▼                             ▼
       Authority Dashboard             Citizen Dashboard
```

## Repository Structure

```text
SIH26083/
│
├── app/
│   ├── app.py
│   ├── citizen_dashboard.py
│   ├── risk_engine.py
│   ├── weather.py
│   └── ...
│
├── data/
│   ├── final_ward_risk_dataset_RF.csv
│   ├── ward_static_scores.csv
│   ├── wbgt_hazard_reference.csv
│   └── ...
│
├── model/
│   └── random_forest.pkl
│
├── README.md
└── requirements.txt
```

The repository structure may change as the prototype is further developed.

## Running Locally

Clone the repository:

```bash
git clone https://github.com/tisya-j/SIH26083-Heat-Health-Dashboard.git
cd SIH26083-Heat-Health-Dashboard
```

Create and activate a virtual environment:

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the Streamlit application:

```bash
streamlit run app/app.py
```

The application requires internet access for the live Open-Meteo forecast used by the forecasting pipeline.

## Deployment

The prototype is deployed using Streamlit Community Cloud.

The deployed application uses the same repository code and retrieves current forecast weather through Open-Meteo.

## Validation

The forecasting model was evaluated using time-ordered expanding-window validation across 1–5 day forecast horizons.

The Random Forest achieved approximately **0.77–0.80 R²** across these horizons.

This metric indicates how much variance in the historical target is explained by the model under the validation setup. It should not be interpreted as percentage accuracy or as a probability of heat-related illness.

## Sensitivity Analysis

The relative weights assigned to heat hazard, vulnerability, and response gaps were varied to test whether ward prioritisation depended excessively on one component.

Across the tested scenarios:

* 8 wards remained in the top 20 under all weighting configurations
* Pairwise top-20 overlap ranged from 10 to 17 wards

This indicates a stable core of high-priority wards while preserving sensitivity to different intervention objectives.

## Limitations

This repository contains a working prototype rather than a production public-health warning system.

Important limitations include:

1. **Spatial weather resolution**
   The current forecasting pipeline uses a Delhi reference location for forecast weather. Spatial differentiation is introduced primarily through ward-level static layers.

2. **Simplified thermal-stress formulation**
   The historical target is based on a simplified WBGT formulation. The system should therefore be described as forecasting a WBGT-based thermal-stress index rather than as a full operational implementation of all WBGT measurement protocols.

3. **Demographic data completeness**
   Some ward-level demographic indicators required median imputation. A production deployment should use updated official population and demographic datasets.

4. **LST versus air temperature**
   Satellite LST represents land surface temperature and is used as spatial heat context. It is not a substitute for near-surface air temperature.

5. **Response infrastructure coverage**
   Hospital and cooling-support layers represent the available prototype dataset and should be replaced or continuously updated with authoritative operational inventories.

6. **Health-outcome calibration**
   The current Human Heat Risk score is not calibrated against mortality, hospitalisation, or other clinical outcomes.

7. **Forecast uncertainty**
   Forecast uncertainty increases with lead time and should be incorporated into future production versions.

## Future Work

Potential extensions include:

* Gridded or downscaled forecast weather across Delhi
* Integration of updated official demographic datasets
* Health-outcome calibration using hospitalisation and mortality records
* Real-time availability of hospitals and cooling facilities
* Automated SMS/WhatsApp alert integration
* Additional urban morphology and built-environment indicators
* Probabilistic forecasts and uncertainty estimates
* Extension to other heat-vulnerable Indian cities

## Project Context

This project was developed for **Smart India Hackathon 2026, Problem Statement 26083**.

The prototype focuses on translating environmental heat forecasts into spatially targeted decision support:

```text
Predict → Warn → Protect → Rescue
```

The intended use is to help decision-makers answer:

* Where is heat risk highest?
* When is the risk expected to peak?
* Which factors are contributing to that risk?
* Where is response accessibility weaker?
* Which wards should receive priority attention?

## License

This project is released under the MIT License.
