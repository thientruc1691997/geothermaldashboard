# Phase 3: Interactive Monitoring Dashboard

## 📌 Overview
This module contains the production-ready **Streamlit** application designed for real-time monitoring of the Balmatt Geothermal Plant. 
The dashboard bridges the gap between complex machine learning models and operational decision-making, allowing operators to visualize the relationship between plant parameters (Flow, Pressure) and induced seismicity risks.

## 📂 Files
* `dashboard.py`: The main application entry point containing UI layout and plotting logic.
* `../data/google_drive_loader.py`: Custom module to securely fetch large datasets from Google Drive at runtime.

## 🌟 Key Features

### 1. Multi-Parameter Visualization
Users can dynamically select and overlay various operational metrics to explore correlations:
* **Flow Rates:** Injection vs. Production flow.
* **Pressure:** Wellhead pressure (WHP) and Annulus pressure.
* **Temperature:** Injection vs. Production temperature differentials (`dT`).
* **Energy:** Cumulative energy injection and cooling.

### 2. Seismic Event Overlay
* **Correlation Plotting:** Seismic events are plotted on a secondary axis directly over operational data.
* **Magnitude Encoding:** Marker size and color intensity scale with event magnitude ($M_L$), making severe events immediately visible.

### 3. Operational Context
* **Phase Highlighting:** The background is dynamically shaded (e.g., Red/Green zones) to indicate whether the plant is in an active **Production Phase** or a Shut-in phase.
* **Risk Thresholds:** Visual indicators for model-predicted probabilities crossing safety thresholds (e.g., $P(\text{Event}) > 0.3$).

## ⚙️ Technical Implementation

### Performance Optimization
To handle high-frequency sensor data (5-minute intervals over 5 years) within a web browser:
* **Downsampling:** Large datasets are randomly downsampled (to ~100k points) for rendering speed while maintaining statistical distribution.
* **Plotly:** Uses WebGL-accelerated plotting for responsive zooming and panning.

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
          +---------------------------+