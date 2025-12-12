# Phase 2: Feature Engineering & Predictive Modeling

## 📌 Overview
This module builds a machine learning pipeline to predict induced seismicity at the Balmatt Geothermal Project. 
The core challenge is the non-stationary nature of the reservoir: the relationship between injection pressure and seismic response changes over time.

To address this, we developed a **Time-Series Mixture of Experts (MoE)** architecture that adapts to different physical operating regimes.

## 📂 Files
* `Feature_Engineering_&_Modeling.ipynb`: The main notebook covering the full pipeline from raw data to model evaluation.
* `roll_lag_feature_operation.csv`: (Generated) The intermediate dataset containing 165+ lag features.
* `moe_models/`: (Generated) Directory storing saved model artifacts (`.joblib`) for each cross-validation fold.

## ⚙️ Methodology

### 1. Regime Change Detection
Geothermal operations shift between injection, shut-in, and stimulation phases. A single global model struggles to generalize across these states.
* **Technique:** `ruptures` (Change Point Detection) identifies structural breaks in the time series (e.g., sudden shifts in `net_flow` or `inj_ap`).
* **Result:** Data is segmented into distinct "Regimes" (0, 1, 2...), allowing models to train on relevant historical contexts.

### 2. Feature Engineering
We generate 160+ features to capture the cumulative stress on the reservoir:
* **Rolling Windows:** Mean, Max, Std Dev over 1, 3, and 7-day horizons.
* **Trends:** First-order differences between current and previous windows (e.g., pressure buildup rate).
* **Seismic History:** Count of past events ($M < 1.2$, $1.2 \le M < 1.8$, $M \ge 1.8$) merged using `merge_asof` to prevent data leakage.

### 3. Hierarchical Modeling Pipeline
We decompose the prediction problem into three stages:

#### **Stage 1: Event Probability (Mixture of Experts)**
* **Goal:** Predict if *any* seismic event ($M \ge 0.5$) will occur in the next 7 days.
* **Architecture:**
    * **Gating Network (K-Means):** Clusters incoming data based on hydraulic state (`net_flow`, `pressure`).
    * **Experts (Random Forest):** A specialized classifier is trained for each cluster.
    * **Fallback:** A Global Model handles edge cases where an expert has insufficient training data.
* **Metric:** F1-Macro Score (optimized for rare event detection).

#### **Stage 2:** 

### **Approach 1: Severity Classification**
* **Goal:** Given that an event occurs, will it be **Severe** ($M \ge 1.2$)?
* **Strategy:** Conditional model trained only on positive event samples using **RandomOverSampling** to handle extreme class imbalance.

#### **Stage 2:
### **Approach 2: Magnitude Regression**
* **Goal:** Predict the exact maximum magnitude ($M_{max}$) for the next 7 days.
* **Model:** Random Forest Regressor.
* **Metric:** Mean Absolute Error (MAE).

## 📊 Performance & Validation
* **Validation Strategy:** 5-Fold `TimeSeriesSplit` with a **7-day embargo (gap)** between train and test sets. This ensures zero data leakage from future events.
* **Results (Fold 5):**
    * **Stage 1 F1-Macro:** ~0.715 (High recall for events).
    * **Stage 2 (Approach 1) F1-Macro:** ~0.633 (Effective at distinguishing minor vs. severe shocks).
    * **Stage 2 (Approach 2) MAE:** ~0.20 - 0.40 magnitude units (depending on the regime).

## 🚀 Usage
To replicate the training pipeline:
1. Ensure `data/processed/merged_minute.csv` exists (output from Phase 1).
2. Run the notebook:
   ```bash
   jupyter notebook Feature_Engineering_&_Modeling.ipynb