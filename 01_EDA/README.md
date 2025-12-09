# Phase 1: Data Wrangling & Exploratory Analysis

## 📌 Overview
This folder contains the initial exploration and cleaning of the Balmatt Geothermal Project data (2019-2025). The goal of this phase is to transform raw operational logs and seismic catalogs into a unified, high-quality dataset suitable for machine learning.

We focus on two key dimensions of data quality:
1.  **Completeness:** Handling missing values in high-frequency operational sensors.
2.  **Validity:** Ensuring physical constraints (e.g., zero flow during non-production phases) are respected.

## 📂 Files
* `Seismicity_Data_Clearning_&_Assessing_&_EDA.ipynb`: The main notebook containing the full pipeline from raw data assessment to final feature visualization.

## 📊 Data Sources
The analysis uses two primary datasets provided by VITO:

### 1. Operational Metrics (`operational_metrics.csv`)
High-frequency time-series data (5-minute intervals) tracking the plant's physical state.
* **Dimensions:** ~695,000 observations x 25 columns.
* **Key Variables:**
    * `inj_flow`: Injection flow rate [m³/h].
    * `inj_whp`: Injection Wellhead Pressure [bar].
    * `inj_temp` / `prod_temp`: Temperatures at injection and production [°C].
    * `is_producing`: Boolean flag for plant status.
    * `phase`: Operational phase identifier (18 distinct phases).

### 2. Seismic Events (`seismic_events.csv`)
A catalog of induced seismicity events linked to the plant's operation.
* **Dimensions:** 378 recorded events.
* **Key Variables:**
    * `magnitude`: Local magnitude ($M_L$) of the event.
    * `pgv_max`: Peak Ground Velocity [m/s].
    * `distance_to_fault`: Distance from epicenter to nearest fault [m].
    * `hourly_seismicity_rate`: Count of events > 0.5 $M_L$ in the last hour.

## 🛠 Data Cleaning Strategy
Our assessment revealed several quality issues, categorized as "Dirty Data" (content issues) and "Messy Data" (structural issues).

### Key Issues & Fixes
| Issue Type | Description | Remediation Strategy |
| :--- | :--- | :--- |
| **Data Types** | Timestamps (e.g., `recorded_at`, `phase_started_at`) and `phase` IDs were stored as objects/floats. | Converted all time columns to `datetime64[ns]` and `phase` to categorical for memory efficiency. |
| **Missing Data** | `hedh_thpwr` and heat exchanger energy columns had ~5.9% missing values. | Variables with >5% missing data were dropped or imputed based on production status. |
| **Logic Errors** | Non-zero flow/pressure readings recorded after production phases ended. | Implemented `zero_pct_after_prod_end_fixed()` to audit and force-zero operational variables when `is_producing == False`. |
| **Time Gaps** | Irregular intervals between sensor readings (expected 5 min). | Resampled data to a strict 5-minute grid, using interpolation for short gaps (≤15 min) and masking long gaps. |

## 🔎 Exploratory Findings
* **Production Phases:** The data covers 18 distinct operational phases.
* **Zero-Inflated Data:** A heat map analysis of "Zero Ratio After Phase End" confirmed that variables like `inj_flow` and `inj_whp` correctly drop to zero/near-zero when the plant enters an idle state, validating the `is_producing` flag.
* **Seismic Correlation:** Preliminary analysis suggests a lag between peak injection pressure and seismic events (further detailed in the modeling section).

## 🔜 Next Steps
The cleaned data from this module is saved as `merged_minute.csv` and serves as the input for the **Feature Engineering** phase in the `02_Modeling` folder.