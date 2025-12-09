# dashboard.py
from pathlib import Path
import time

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from data.google_drive_loader import download_operation, download_seismic

# ==========================
# CONFIG
# ==========================
st.set_page_config(
    page_title="Geothermal Operation & Seismic Dashboard",
    layout="wide",
)

st.title("Geothermal Plant Dashboard")


# Variable groups by physical quantity
FEATURE_GROUPS = {
    "Flow": [
        "inj_flow",
        "prod_flow",
    ],
    "Temperature": [
        "inj_temp",
        "prod_temp",
    ],
    "Pressure": [
        "inj_whp",
        "prod_whp",
    ],
    "Energy": [
        "inj_energy",
        "cum_inj_energy",
        "cooling_energy",
        "cum_cooling_energy",
    ],
    "Volume": [
        "volume",
        "cum_volume",
    ],
}

shade_col = "is_producing"
shade_value = False
shade_color = "lightcoral"
shade_alpha = 0.3
phase_col = "phase"
alt_colors = ("steelblue", "darkorange")

# ==========================
# Utility
# ==========================


def downsample_for_plot(df: pd.DataFrame, max_rows: int = 100_000) -> pd.DataFrame:
    """Randomly sample at most max_rows rows for plotting to avoid heavy charts."""
    if len(df) <= max_rows:
        return df
    return df.sample(max_rows, random_state=42)


def add_seismic_targets(
    minute_data: pd.DataFrame,
    seismics: pd.DataFrame,
    horizon_days: int = 7,
    lookback_days: int = 7,
) -> pd.DataFrame:
    """
    Attach 7-day seismic targets to operation data, based on future events.

    For each timestamp t in minute_data, look at events in (t, t + horizon_days],
    compute the max magnitude, and bin it into classes:
      0: no event
      1: mag < 1.2
      2: 1.2 <= mag <= 1.8
      3: mag > 1.8

    Also count the number of events in the past (t - lookback_days, t].
    """
    op = minute_data.copy()
    ev = seismics.copy()

    # Normalize and sort time columns
    op["recorded_at"] = pd.to_datetime(op["recorded_at"], errors="coerce")
    ev["occurred_at"] = pd.to_datetime(ev["occurred_at"], errors="coerce")
    op = (
        op.dropna(subset=["recorded_at"])
        .sort_values("recorded_at")
        .reset_index(drop=True)
    )
    ev = (
        ev.dropna(subset=["occurred_at"])
        .sort_values("occurred_at")
        .reset_index(drop=True)
    )

    # If no seismic events, fill defaults
    if ev.empty:
        op["magnitude_bin_7days"] = 0
        op["no_event_7days"] = 1
        op["mag_lt_1_2_7days"] = 0
        op["mag_1_2_1_8_7days"] = 0
        op["mag_gt_1_8_7days"] = 0
        op["count_prev_7days"] = 0
        return op

    # Time and magnitude arrays
    op_times = op["recorded_at"].to_numpy(dtype="datetime64[ns]")
    ev_times = ev["occurred_at"].to_numpy(dtype="datetime64[ns]")
    ev_mag = pd.to_numeric(ev["magnitude"], errors="coerce").to_numpy()

    # Remove NaN magnitudes
    valid = ~np.isnan(ev_mag)
    ev_times = ev_times[valid]
    ev_mag = ev_mag[valid]

    # If still empty after filtering
    if ev_times.size == 0:
        op["magnitude_bin_7days"] = 0
        op["no_event_7days"] = 1
        op["mag_lt_1_2_7days"] = 0
        op["mag_1_2_1_8_7days"] = 0
        op["mag_gt_1_8_7days"] = 0
        op["count_prev_7days"] = 0
        return op

    # Vectorized window boundaries using searchsorted
    horizon_delta = np.timedelta64(horizon_days, "D")
    lookback_delta = np.timedelta64(lookback_days, "D")

    # Future window: (t, t+7d]
    left = np.searchsorted(ev_times, op_times, side="right")
    right = np.searchsorted(ev_times, op_times + horizon_delta, side="right")

    # Past window: (t-7d, t]
    left_prev = np.searchsorted(ev_times, op_times - lookback_delta, side="right")
    right_prev = np.searchsorted(ev_times, op_times, side="right")
    count_prev = (right_prev - left_prev).astype(int)

    # Max magnitude in each future window
    n = op_times.shape[0]
    max_mag_next = np.full(n, np.nan, dtype=float)

    for i in range(n):
        li, ri = left[i], right[i]
        if ri > li:
            max_mag_next[i] = np.max(ev_mag[li:ri])

    # Bin by thresholds
    # 0: no event; 1: <1.2; 2: 1.2-1.8; 3: >1.8
    bins = np.zeros(n, dtype=int)
    has_event = ~np.isnan(max_mag_next)

    bins[np.where((has_event) & (max_mag_next < 1.2))] = 1
    bins[np.where((has_event) & (max_mag_next >= 1.2) & (max_mag_next <= 1.8))] = 2
    bins[np.where((has_event) & (max_mag_next > 1.8))] = 3

    # One-hot columns
    no_event = (bins == 0).astype(int)
    lt_1_2 = (bins == 1).astype(int)
    btw_1_2_1_8 = (bins == 2).astype(int)
    gt_1_8 = (bins == 3).astype(int)

    op["magnitude_bin_7days"] = bins
    op["no_event_7days"] = no_event
    op["mag_lt_1_2_7days"] = lt_1_2
    op["mag_1_2_1_8_7days"] = btw_1_2_1_8
    op["mag_gt_1_8_7days"] = gt_1_8
    op["count_prev_7days"] = count_prev

    return op


# ==========================
# DATA LOADING
# ==========================


@st.cache_data(show_spinner=True)
def load_raw_data(op_path: str, sei_path: str):
    """
    Read raw CSVs from local paths, lowercase column names,
    and parse datetime columns if present.
    """
    op_path = Path(op_path)
    sei_path = Path(sei_path)

    df_op = pd.read_csv(op_path)
    df_op.columns = df_op.columns.str.lower()
    if "recorded_at" in df_op.columns:
        df_op["recorded_at"] = pd.to_datetime(df_op["recorded_at"], errors="coerce")

    df_sei = pd.read_csv(sei_path)
    df_sei.columns = df_sei.columns.str.lower()
    if "occurred_at" in df_sei.columns:
        df_sei["occurred_at"] = pd.to_datetime(df_sei["occurred_at"], errors="coerce")

    return df_op, df_sei


@st.cache_data(show_spinner=True)
def compute_targets_for_op(df_op: pd.DataFrame, df_sei: pd.DataFrame) -> pd.DataFrame:
    """Wrapper around add_seismic_targets with caching."""
    if "recorded_at" not in df_op.columns or "occurred_at" not in df_sei.columns:
        return df_op.copy()
    return add_seismic_targets(df_op, df_sei, horizon_days=7, lookback_days=7)


# Download files from Drive (only if not already present)
op_path = download_operation(force_download=False)
sei_path = download_seismic(force_download=False)

load_start = time.perf_counter()
df_op_raw, df_sei_raw = load_raw_data(str(op_path), str(sei_path))
load_time = time.perf_counter() - load_start
st.caption(f"⏱ Load raw CSV: {load_time:.2f} s")


@st.cache_data(show_spinner=True)
def load_fake_forecast_horizon(n_points: int = 50) -> pd.DataFrame:
    """
    Fake forward-looking forecast from now to next 7 days.
      - horizon_days: from 0 to 7
      - p_event: fake probability curve
      - pred_mag: fake magnitude distribution (conditional)
    """
    rng = np.random.default_rng(seed=123)

    horizon = np.linspace(0.0, 7.0, n_points)  # days from now

    # fake probability curve: low at edges, bump in the middle
    center = 3.0
    width = 1.5
    p_base = np.exp(-0.5 * ((horizon - center) / width) ** 2)  # bell shape
    p_base = p_base / p_base.max()  # normalize to [0, 1]
    noise = rng.normal(0, 0.05, size=n_points)
    p_event = np.clip(p_base + noise, 0.0, 1.0)

    # fake magnitude (if event happens): around 1.6 ± 0.4
    pred_mag = rng.normal(loc=1.6, scale=0.4, size=n_points)
    pred_mag = np.clip(pred_mag, 0.0, 3.0)

    df_f = pd.DataFrame(
        {
            "horizon_days": horizon,
            "p_event_7d": p_event,
            "pred_mag": pred_mag,
        }
    )
    return df_f


# ==========================
# GLOBAL FILTERS (no sidebar)
# ==========================

filter_container = st.container()
with filter_container:
    st.subheader("🔎 Global filters")

    # Date range based on recorded_at if available, otherwise occurred_at
    if "recorded_at" in df_op_raw.columns:
        min_date = df_op_raw["recorded_at"].min().date()
        max_date = df_op_raw["recorded_at"].max().date()
    elif "occurred_at" in df_sei_raw.columns:
        min_date = df_sei_raw["occurred_at"].min().date()
        max_date = df_sei_raw["occurred_at"].max().date()
    else:
        min_date = max_date = None

    col_filter1, col_filter2 = st.columns(2)

    if min_date is not None:
        with col_filter1:
            date_range = st.date_input(
                "Date range",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date,
            )
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_date, end_date = date_range
            if "recorded_at" in df_op_raw.columns:
                mask_op = (df_op_raw["recorded_at"].dt.date >= start_date) & (
                    df_op_raw["recorded_at"].dt.date <= end_date
                )
                df_op = df_op_raw.loc[mask_op].copy()
            else:
                df_op = df_op_raw.copy()

            if "occurred_at" in df_sei_raw.columns:
                mask_sei = (df_sei_raw["occurred_at"].dt.date >= start_date) & (
                    df_sei_raw["occurred_at"].dt.date <= end_date
                )
                df_sei = df_sei_raw.loc[mask_sei].copy()
            else:
                df_sei = df_sei_raw.copy()
        else:
            df_op = df_op_raw.copy()
            df_sei = df_sei_raw.copy()
    else:
        df_op = df_op_raw.copy()
        df_sei = df_sei_raw.copy()

    with col_filter2:
        selected_group = st.selectbox(
            "Operation – variable group",
            options=list(FEATURE_GROUPS.keys()),
            index=0,
        )

st.markdown("---")

# Prepare operation with targets for Tab 2
df_op_targets = compute_targets_for_op(df_op, df_sei)

# ==========================
# TABS
# ==========================

tab_op, tab_sei, tab_forecast = st.tabs(
    ["Operation", "Seismics event", "Forecast (demo)"]
)


# ==========================
# TAB 1 – OPERATION
# ==========================

with tab_op:
    st.subheader("🛠 Operation – by variable group")

    if "recorded_at" not in df_op.columns:
        st.info("Operation data does not contain 'recorded_at'. Cannot plot over time.")
    else:
        # Phase filter (dropdown)
        if phase_col in df_op.columns:
            phase_values = df_op[phase_col].dropna().unique()
            phase_values = sorted(phase_values)

            phase_options = ["All phases"] + list(phase_values)
            selected_phase = st.selectbox(
                "Filter by phase",
                options=phase_options,
            )

            if selected_phase != "All phases":
                df_op = df_op[df_op[phase_col] == selected_phase]
        else:
            st.info(
                f"Column '{phase_col}' not found in operation data (no phase filter)."
            )

        # Variable group chart – one feature at a time
        available_cols = [
            c for c in FEATURE_GROUPS[selected_group] if c in df_op.columns
        ]
        if not available_cols:
            st.warning(
                f"No columns from group '{selected_group}' found in operation data."
            )
        else:
            st.markdown(f"**Variable group: {selected_group}**")

            y_feature = st.selectbox(
                "Select feature to plot over time",
                options=available_cols,
            )

            plot_cols = ["recorded_at", y_feature]
            if phase_col in df_op.columns:
                plot_cols.append(phase_col)
            if shade_col in df_op.columns:
                plot_cols.append(shade_col)

            df_feat = df_op[plot_cols].dropna(subset=["recorded_at", y_feature])
            df_feat_plot = downsample_for_plot(df_feat, max_rows=200_000)
            df_feat_plot = df_feat_plot.sort_values("recorded_at").reset_index(
                drop=True
            )

            if df_feat_plot.empty:
                st.info("No data to plot for this selection.")
                st.stop()

            # --- FIGURE: dùng graph_objects để điều khiển line segments ---
            fig_feat = go.Figure()

            # 1) Shaded background where is_producing == False
            if shade_col in df_feat_plot.columns:
                df_shade = (
                    df_feat_plot[["recorded_at", shade_col]]
                    .dropna()
                    .sort_values("recorded_at")
                    .reset_index(drop=True)
                )
                if not df_shade.empty:
                    # convert to python datetime for Plotly
                    times = pd.to_datetime(df_shade["recorded_at"]).tolist()
                    vals = df_shade[shade_col].to_numpy()

                    def is_false(v):
                        # robust check for "False"
                        if isinstance(v, (bool, np.bool_)):
                            return v is False
                        if isinstance(v, (int, float, np.integer, np.floating)):
                            return v == 0
                        if isinstance(v, str):
                            return v.strip().lower() in ("false", "0", "no")
                        return False

                    in_segment = False
                    seg_start = None

                    for i in range(len(df_shade)):
                        v = is_false(vals[i])
                        if v and not in_segment:
                            in_segment = True
                            seg_start = times[i]
                        elif not v and in_segment:
                            fig_feat.add_vrect(
                                x0=seg_start,
                                x1=times[i],
                                fillcolor=shade_color,
                                opacity=shade_alpha,
                                layer="below",
                                line_width=0,
                            )
                            in_segment = False

                    if in_segment:
                        fig_feat.add_vrect(
                            x0=seg_start,
                            x1=times[-1],
                            fillcolor=shade_color,
                            opacity=shade_alpha,
                            layer="below",
                            line_width=0,
                        )

            # 2) Line, đổi màu xen kẽ theo phase
            x_all = pd.to_datetime(df_feat_plot["recorded_at"]).tolist()
            y_all = df_feat_plot[y_feature].to_numpy()

            if phase_col in df_feat_plot.columns:
                phases = df_feat_plot[phase_col].to_numpy()
                segments = []
                start_idx = 0
                for i in range(1, len(df_feat_plot)):
                    if phases[i] != phases[i - 1]:
                        segments.append((start_idx, i, phases[i - 1]))
                        start_idx = i
                segments.append((start_idx, len(df_feat_plot), phases[-1]))
            else:
                segments = [(0, len(df_feat_plot), None)]

            color_used = {}

            for seg_idx, (i0, i1, ph_val) in enumerate(segments):
                x_seg = x_all[i0:i1]
                y_seg = y_all[i0:i1]
                if len(x_seg) < 2:
                    continue

                color = alt_colors[seg_idx % 2]
                showlegend = color not in color_used
                color_used[color] = True

                name = (
                    f"{y_feature} (phase={ph_val})" if ph_val is not None else y_feature
                )

                fig_feat.add_trace(
                    go.Scatter(
                        x=x_seg,
                        y=y_seg,
                        mode="lines",
                        line=dict(color=color),
                        name=name,
                        showlegend=showlegend,
                    )
                )

            fig_feat.update_layout(
                title=f"{y_feature} over time",
                xaxis_title="Time",
                yaxis_title=y_feature,
            )

            st.plotly_chart(fig_feat, use_container_width=True)


# ==========================
# TAB 2 – SEISMICS
# ==========================

with tab_sei:
    st.subheader("Seismics event")

    # Fig 1: time vs magnitude
    st.markdown("### Seismic event magnitude over time")

    if "occurred_at" not in df_sei.columns or "magnitude" not in df_sei.columns:
        st.info(
            "Seismic data must contain 'occurred_at' and 'magnitude' to plot Fig 1."
        )
    else:
        df_sei_plot = df_sei[["occurred_at", "magnitude"]].dropna()
        df_sei_plot = downsample_for_plot(df_sei_plot, max_rows=200_000)

        fig_mag_time = px.scatter(
            df_sei_plot.sort_values("occurred_at"),
            x="occurred_at",
            y="magnitude",
            title="Seismic magnitude over time",
        )
        st.plotly_chart(fig_mag_time, use_container_width=True)

    # Fig 2: count of classes in (t, t+7] based on magnitude_bin_7days
    st.markdown("### Count of seismic classes in next 7 days")

    if "magnitude_bin_7days" not in df_op_targets.columns:
        st.info(
            "Column 'magnitude_bin_7days' not found in operation targets. "
            "Check data or time columns."
        )
    else:
        class_mapping = {
            0: "0 – no event",
            1: "1 – mag < 1.2",
            2: "2 – 1.2 ≤ mag ≤ 1.8",
            3: "3 – mag > 1.8",
        }

        df_bins = df_op_targets.copy()
        counts = (
            df_bins["magnitude_bin_7days"]
            .value_counts()
            .rename_axis("magnitude_bin_7days")
            .reset_index(name="count")
            .sort_values("magnitude_bin_7days")
        )
        counts["class_label"] = counts["magnitude_bin_7days"].map(class_mapping)

        fig_counts = px.bar(
            counts,
            x="class_label",
            y="count",
            title="Count of seismic classes in next 7 days",
            labels={"class_label": "Class", "count": "Count"},
        )
        st.plotly_chart(fig_counts, use_container_width=True)

# ==========================
# TAB 3 – FORECAST (DEMO)
# ==========================

with tab_forecast:
    st.subheader("Seismic event forecast (next 7 days) – demo")

    df_f = load_fake_forecast_horizon(n_points=80)

    # Overall risk summary (use mean prob as a simple proxy)
    mean_p = float(df_f["p_event_7d"].mean())
    expected_mag = float(df_f["pred_mag"].mean())

    if mean_p < 0.2:
        risk_label = "Low"
        risk_color = "green"
    elif mean_p < 0.5:
        risk_label = "Medium"
        risk_color = "orange"
    else:
        risk_label = "High"
        risk_color = "red"

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            "Avg P(event in next 7 days)",
            f"{mean_p:.2f}",
        )
    with col2:
        st.metric(
            "Expected magnitude (if event)",
            f"{expected_mag:.2f}",
        )
    with col3:
        st.markdown(f"**Risk level:**")
        st.markdown(
            f"<span style='color:{risk_color}; font-size: 24px;'>{risk_label}</span>",
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # Controls for this tab
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        thresh = st.slider(
            "Event threshold (P[event])",
            min_value=0.0,
            max_value=1.0,
            value=0.3,
            step=0.05,
        )
    with col_f2:
        show_mag_points = st.checkbox(
            "Show magnitude markers on risk curve", value=True
        )

    df_plot = df_f.copy()
    df_plot["above_thresh"] = df_plot["p_event_7d"] >= thresh

    # === Plot 1: Probability curve over horizon ===
    st.markdown("### P(event) over horizon (days from now)")

    fig_prob = go.Figure()

    # probability line
    fig_prob.add_trace(
        go.Scatter(
            x=df_plot["horizon_days"],
            y=df_plot["p_event_7d"],
            mode="lines",
            name="P(event)",
        )
    )

    # threshold line
    fig_prob.add_hline(
        y=thresh,
        line_dash="dash",
        line_color="gray",
        annotation_text=f"threshold = {thresh:.2f}",
        annotation_position="top left",
    )

    # shading where P(event) >= threshold
    times = df_plot["horizon_days"].to_numpy()
    probs = df_plot["p_event_7d"].to_numpy()

    in_segment = False
    seg_start = None
    for i in range(len(df_plot)):
        above = probs[i] >= thresh
        if above and not in_segment:
            in_segment = True
            seg_start = times[i]
        elif not above and in_segment:
            fig_prob.add_vrect(
                x0=seg_start,
                x1=times[i],
                fillcolor="lightcoral",
                opacity=0.2,
                layer="below",
                line_width=0,
            )
            in_segment = False
    if in_segment:
        fig_prob.add_vrect(
            x0=seg_start,
            x1=times[-1],
            fillcolor="lightcoral",
            opacity=0.2,
            layer="below",
            line_width=0,
        )

    # optional markers sized by magnitude
    if show_mag_points:
        fig_prob.add_trace(
            go.Scatter(
                x=df_plot.loc[df_plot["above_thresh"], "horizon_days"],
                y=df_plot.loc[df_plot["above_thresh"], "p_event_7d"],
                mode="markers",
                name="High-risk points (size ~ mag)",
                marker=dict(
                    size=5
                    + 8 * (df_plot.loc[df_plot["above_thresh"], "pred_mag"] / 3.0),
                    color="darkred",
                    opacity=0.7,
                ),
            )
        )

    fig_prob.update_layout(
        xaxis_title="Days from now",
        yaxis_title="P(event in next 7 days)",
    )
    st.plotly_chart(fig_prob, use_container_width=True)
