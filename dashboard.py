"""Streamlit dashboard for construction video spatial memory analysis."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import streamlit as st

BASE_DIR = os.path.dirname(__file__)
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
FRAMES_DIR = os.path.join(BASE_DIR, "frames")

# --- Page Config ---
st.set_page_config(page_title="Construction Spatial Memory", layout="wide")

st.title("Construction Video — Spatial Memory Analysis")
st.caption("VLM-powered activity tracking with persistent spatial memory")


# --- Load Data ---
@st.cache_data
def load_timeline(mode: str) -> dict | None:
    path = os.path.join(OUTPUT_DIR, f"timeline_{mode}.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


@st.cache_data
def load_comparison() -> dict | None:
    path = os.path.join(OUTPUT_DIR, "comparison.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


def get_frame_path(chunk_idx: int, frames_per_chunk: int = 4) -> str | None:
    frame_num = chunk_idx * frames_per_chunk + 1
    path = os.path.join(FRAMES_DIR, f"frame_{frame_num:04d}.jpg")
    return path if os.path.exists(path) else None


# --- Sidebar ---
st.sidebar.header("Controls")
available_modes = []
for mode in ["memory", "structured", "naive"]:
    if load_timeline(mode):
        available_modes.append(mode)

if not available_modes:
    st.error("No analysis results found. Run the pipeline first:")
    st.code("cd visual-memory && python analyzer.py memory", language="bash")
    st.stop()

selected_mode = st.sidebar.selectbox("Analysis Mode", available_modes)
data = load_timeline(selected_mode)
comparison = load_comparison()

# --- Summary Stats ---
summary = data.get("summary", {})
productivity = summary.get("productivity", {})

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Segments", summary.get("total_segments", 0))
col2.metric("Productive", f"{productivity.get('productive_pct', 0)}%", delta=None)
col3.metric("Transitional", f"{productivity.get('transitional_pct', 0)}%")
col4.metric("Idle", f"{productivity.get('idle_pct', 0)}%")

# --- Productivity Timeline Bar ---
st.subheader("Productivity Timeline")
timeline = data.get("timeline", [])

# Build color-coded timeline
productivity_colors = {
    "PRODUCTIVE": "#22c55e",
    "TRANSITIONAL": "#eab308",
    "IDLE": "#ef4444",
}

timeline_html = '<div style="display:flex; width:100%; height:40px; border-radius:8px; overflow:hidden; gap:1px;">'
for i, entry in enumerate(timeline):
    prod = entry.get("productivity", "unknown")
    color = productivity_colors.get(prod, "#94a3b8")
    activity = entry.get("activity", "?")
    ts = entry.get("timestamp_range", "")
    timeline_html += f'<div title="{ts}: {activity} [{prod}]" style="flex:1; background:{color}; cursor:pointer;"></div>'
timeline_html += "</div>"
timeline_html += '<div style="display:flex; gap:16px; margin-top:4px; font-size:12px;">'
timeline_html += '<span><span style="color:#22c55e;">■</span> Productive</span>'
timeline_html += '<span><span style="color:#eab308;">■</span> Transitional</span>'
timeline_html += '<span><span style="color:#ef4444;">■</span> Idle</span>'
timeline_html += "</div>"
st.markdown(timeline_html, unsafe_allow_html=True)

# --- Activity Distribution ---
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Activity Breakdown")
    activities = summary.get("activity_distribution", {})
    if activities:
        import pandas as pd

        df = pd.DataFrame(
            [{"Activity": k, "Count": v} for k, v in sorted(activities.items(), key=lambda x: -x[1])]
        )
        st.bar_chart(df.set_index("Activity"))
    else:
        st.info("No activity data available")

with col_right:
    st.subheader("Hazards Detected")
    hazards = summary.get("unique_hazards", [])
    risk_levels = summary.get("risk_levels_seen", [])
    if hazards:
        for h in hazards:
            st.markdown(f"- {h}")
        st.markdown(f"**Risk levels observed:** {', '.join(risk_levels)}")
    else:
        st.info("No hazards recorded")

# --- Idle Stretches ---
idle_stretches = summary.get("idle_stretches", [])
if idle_stretches:
    st.subheader("Idle Stretches")
    for stretch in idle_stretches:
        st.warning(
            f"Idle for {stretch['duration_chunks']} segments "
            f"starting at chunk {stretch['start_chunk']} "
            f"({stretch.get('timestamp', '?')})"
        )

# --- Spatial Memory (memory mode only) ---
if selected_mode == "memory":
    spatial_mem = data.get("spatial_memory", [])
    if spatial_mem:
        st.subheader(f"Accumulated Spatial Memory ({len(spatial_mem)} objects)")

        # Group by type
        mem_by_type = {}
        for item in spatial_mem:
            t = item.get("type", "unknown")
            mem_by_type.setdefault(t, []).append(item)

        for obj_type, items in sorted(mem_by_type.items()):
            with st.expander(f"{obj_type.upper()} ({len(items)} items)"):
                for item in items:
                    st.markdown(
                        f"- **{item.get('object', '?')}** — {item.get('location', '?')} "
                        f"(first seen: {item.get('first_seen', '?')})"
                    )

# --- Detailed Timeline ---
st.subheader("Detailed Timeline")

for i, entry in enumerate(timeline):
    ts = entry.get("timestamp_range", f"Chunk {i}")
    activity = entry.get("activity", "?")
    prod = entry.get("productivity", "?")
    confidence = entry.get("confidence", 0)

    color = productivity_colors.get(prod, "#94a3b8")

    with st.expander(f"{ts} — {activity} [{prod}]", expanded=False):
        cols = st.columns([1, 2])

        with cols[0]:
            frame_path = get_frame_path(i)
            if frame_path:
                st.image(frame_path, caption=f"Frame from chunk {i}", use_container_width=True)

        with cols[1]:
            if selected_mode == "naive":
                st.markdown(entry.get("raw_response", "No response"))
            else:
                st.markdown(f"**Activity:** {activity}")
                st.markdown(f"**Productivity:** {prod}")
                st.markdown(f"**Confidence:** {confidence}")
                st.markdown(f"**Reasoning:** {entry.get('reasoning', 'N/A')}")
                st.markdown(f"**Hands:** {entry.get('hands', 'N/A')}")

                if isinstance(entry.get("hazards"), dict):
                    h = entry["hazards"]
                    risk = h.get("risk_level", "?")
                    badge_color = {
                        "LOW": "green",
                        "MEDIUM": "orange",
                        "HIGH": "red",
                        "CRITICAL": "red",
                    }.get(risk, "gray")
                    st.markdown(f"**Risk Level:** :{badge_color}[{risk}]")
                    st.markdown(f"**Hazard Details:** {h.get('details', 'N/A')}")
                    if h.get("items"):
                        st.markdown("**Hazards:**")
                        for item in h["items"]:
                            st.markdown(f"  - {item}")

                tools = entry.get("tools", [])
                if tools:
                    st.markdown(f"**Tools:** {', '.join(tools)}")

                env = entry.get("environment", {})
                if env:
                    st.markdown(
                        f"**Environment:** {env.get('structure_type', '?')} / "
                        f"{env.get('phase', '?')} / {env.get('level', '?')}"
                    )

# --- Comparison Tab ---
if comparison:
    st.divider()
    st.subheader("Mode Comparison")

    modes_data = comparison.get("modes", {})
    comp_cols = st.columns(len(modes_data))

    for col, (mode, mode_summary) in zip(comp_cols, modes_data.items()):
        with col:
            st.markdown(f"### {mode.upper()}")
            p = mode_summary.get("productivity", {})
            st.metric("Productive", f"{p.get('productive_pct', '?')}%")
            st.metric("Idle", f"{p.get('idle_pct', '?')}%")
            n_hazards = len(mode_summary.get("unique_hazards", []))
            st.metric("Unique Hazards Found", n_hazards)

# --- Footer ---
st.divider()
st.caption(
    "Built for Ironsite Spatial Intelligence Hackathon | "
    "UMD Startup Shell x Ironsite | Feb 2026"
)
