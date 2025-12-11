# Phase 3: Interactive Monitoring Dashboard

# 03_Dashboard – Geothermal Seismic Forecast

Streamlit app for:
- Visualizing geothermal **operation data**
- Visualizing **seismic events**
- Showing **7-day seismic event probability** using a Mixture-of-Experts (MoE) model

🔗 **Deployed app:**  
https://geothermaldashboard-mmrt8zvhkc2nmzrubjpzwh.streamlit.app/

---

## Structure

```text
03_Dashboard/
├── dashboard.py              # Main Streamlit app
├── README.md
├── data/
│   ├── data_source.yaml      # Google Drive file_ids (operation, seismic, processed_features)
│   ├── feature_cols.joblib   # List of features used by the model
│   └── google_drive_loader.py# Download CSVs from Google Drive
└── wrapped_models/
    ├── moe_fold1.joblib
    ├── moe_fold2.joblib
    ├── moe_fold3.joblib
    ├── moe_fold4.joblib
    └── moe_fold5.joblib      # Wrapped MoE models (one per CV fold)
```
---

## Tabs in the App

### **1. Operation**
Time-series plots of flow, pressure, temperature, energy, and volume variables.  
Includes phase colouring and shaded non-producing segments.

### **2. Seismics event**
Plots:
- Magnitude over time  

### **3. Forecast (MoE Model)**
- Uses last **7 days × 5-minute data**
- Computes probability of an event in the next 7 days  
- Shows risk summary, interactive thresholding, and a forecast table  
- No model training inside Streamlit (only inference)

---

## Credentials & Data Access

### `data_source.yaml`
```yaml
geothermal:
  operation: "<file_id>"
  seismic: "<file_id>"
  processed_features: "<file_id>"
```
All three Drive files must be shared (Viewer) with the Google Cloud service account used by the app.
---
## Models
Trained offline -> wrapped -> stored as:
```
wrapped_models/moe_fold*.joblib
data/feature_cols.joblib
```

----

### Data Architecture
To keep the GitHub repository lightweight and secure:
```text
          +---------------------------+
          |     GitHub Repository     |
          |---------------------------|
          | Code (dashboard.py)       |
          | Config (data_source)      |
          | No data files             |
          +--------------+------------+
                         |
                         |  (deploy from GitHub)
                         v
          +---------------------------+
          |     Streamlit Cloud App   |
          +--------------+------------+
                         |
                         |  HTTPS + Service Account
                         v
          +---------------------------+
          |       Google Drive        |
          |---------------------------|
          |  operation.csv (raw)      |
          |  seismic.csv   (raw)      |
          |  processed_features.csv   |
          +---------------------------+
```