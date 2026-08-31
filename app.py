from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from src.scoreboard_extractor import ScoreboardExtractor


ROOT = Path(__file__).resolve().parent
DEFAULT_VIDEO = ROOT / "input" / "bowling_scoreboard__.mp4"


def flatten_observations(data: dict) -> pd.DataFrame:
    """Convert nested extractor observations into chart-friendly rows."""
    records = []
    for observation in data.get("observations", []):
        for row in observation.get("rows", []):
            records.append({
                "frame": observation.get("frame"),
                "time_sec": observation.get("time_sec"),
                "scene_confidence": observation.get("scene_confidence"),
                "player": row.get("player"),
                "score": row.get("score"),
                "confidence": row.get("confidence"),
                "method": row.get("method"),
                "template": row.get("template"),
            })
    return pd.DataFrame(records)


def render_line_chart(
    data: pd.DataFrame,
    value_column: str,
    title: str,
    y_label: str,
) -> None:
    """Render a multi-series chart using Streamlit's built-in chart renderer."""
    chart_data = data.pivot_table(
        index="time_sec", columns="player", values=value_column, aggfunc="last",
    ).sort_index()
    st.caption(title)
    st.line_chart(chart_data, y_label=y_label)


def render_analysis_dashboard(data: dict) -> None:
    """Render charts and tables for a completed extraction."""
    df = flatten_observations(data)
    st.header("📊 Scoreboard Extraction Analysis")
    st.caption("Visualization of player scores and recognition confidence over video frames.")

    video_info = data.get("video_info", {})
    if video_info:
        columns = st.columns(4)
        columns[0].metric("Resolution", f"{video_info.get('width')} × {video_info.get('height')}")
        columns[1].metric("FPS", video_info.get("fps"))
        columns[2].metric("Total frames", video_info.get("frame_count"))
        columns[3].metric("Duration", f"{video_info.get('duration_sec', 0):.2f} sec")

    if df.empty:
        st.warning("No observations were detected, so charts are unavailable.")
        return

    players = sorted(df["player"].dropna().unique())
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📈 Score Trends", "📉 Confidence", "🎯 Scene Confidence", "🏁 Final Board", "📋 Raw Data",
    ])

    with tab1:
        selected = st.multiselect("Select players", players, default=players, key="score_players")
        if selected:
            chart_df = df[df["player"].isin(selected)].dropna(subset=["score"])
            render_line_chart(chart_df, "score", "Score Progression", "Score")
        else:
            st.info("Select at least one player to display scores.")

    with tab2:
        selected = st.multiselect("Select players", players, default=players, key="confidence_players")
        if selected:
            chart_df = df[df["player"].isin(selected)]
            render_line_chart(chart_df, "confidence", "Recognition Confidence per Player", "Confidence")
        else:
            st.info("Select at least one player to display confidence.")

    with tab3:
        scene_df = df[["frame", "time_sec", "scene_confidence"]].drop_duplicates().sort_values("time_sec")
        st.caption("Scene Confidence Over Time")
        st.line_chart(scene_df.set_index("time_sec")["scene_confidence"], y_label="Scene confidence")

    with tab4:
        final = data.get("final_scoreboard", [])
        if final:
            st.dataframe(pd.DataFrame(final), hide_index=True, use_container_width=True)
        else:
            st.info("No final scoreboard data available.")
        st.subheader("Average Confidence per Player")
        average = df.groupby("player", as_index=False)["confidence"].mean()
        average.columns = ["Player", "Avg Confidence"]
        st.dataframe(average.style.format({"Avg Confidence": "{:.3f}"}), hide_index=True, use_container_width=True)

    with tab5:
        st.dataframe(df, hide_index=True, use_container_width=True)

st.set_page_config(
    page_title="Scoreboard Vision",
    page_icon="🎳",
    layout="wide",
    initial_sidebar_state="auto",
)

st.markdown(
    """
    <style>
    [data-testid="stSidebar"] { min-width: 30vw; max-width: 30vw; }
    [data-testid="stSidebarContent"] { width: 100%; }
    .hero { padding: 1.5rem 1.8rem; border-radius: 18px; background: linear-gradient(120deg, #172554 0%, #1d4ed8 55%, #0ea5e9 100%); color: white; margin-bottom: 1.5rem; }
    .hero h1 { margin: 0; font-size: 2.4rem; }
    .hero p { margin: .45rem 0 0; color: #dbeafe; font-size: 1.05rem; }
    [data-testid="stMetricValue"] { color: #1d4ed8; }
    </style>
    <div class="hero">
        <h1>🎳 Scoreboard Vision</h1>
        <p>Upload a bowling video and extract the final scoreboard automatically.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Processing settings")
    sample_every = st.slider(
        "Analyze every Nth frame", 1, 60, 15,
        help="Lower values analyze more frames and may improve detection at the cost of speed.",
    )
    use_ocr = st.checkbox(
        "Enable OCR fallback", value=False,
        help="Use Tesseract when template matching confidence is low. This is slower.",
    )
    st.caption("Template matching is used by default. OCR requires Tesseract installed separately.")

st.subheader("Input video")
if DEFAULT_VIDEO.exists():
    st.success(f"Default video ready: **{DEFAULT_VIDEO.name}**")
    st.video(str(DEFAULT_VIDEO))
else:
    st.warning(f"Default video not found: `{DEFAULT_VIDEO.name}`. Upload a video below to continue.")

uploaded_file = st.file_uploader(
    "Upload a different video (optional)",
    type=["mp4", "mov", "avi", "mkv", "webm"],
    help="Leave this empty to process the default video, or upload another scoreboard video.",
)

if uploaded_file is not None:
    st.video(uploaded_file)
    st.caption(f"Custom video selected: **{uploaded_file.name}** ({uploaded_file.size / 1024 / 1024:.1f} MB)")
else:
    st.caption("No custom upload selected. The default video will be processed.")

video_available = uploaded_file is not None or DEFAULT_VIDEO.exists()
if not video_available:
    st.info("Upload a video to begin extraction.")
    st.markdown("#### How it works")
    st.markdown("1. Detect scoreboard frames  2. Read scores with computer vision  3. Aggregate observations  4. Download the results")
elif st.button("🚀 Extract scoreboard", type="primary", use_container_width=True):
    selected_name = uploaded_file.name if uploaded_file is not None else DEFAULT_VIDEO.name
    suffix = Path(selected_name).suffix or ".mp4"
    with tempfile.TemporaryDirectory(prefix="scoreboard_vision_") as temp_dir:
        temp_root = Path(temp_dir)
        input_path = temp_root / f"input{suffix}"
        output_dir = temp_root / "output"
        if uploaded_file is not None:
            input_path.write_bytes(uploaded_file.getvalue())
        else:
            input_path.write_bytes(DEFAULT_VIDEO.read_bytes())

        try:
            with st.spinner("Processing video and extracting scoreboard…"):
                extractor = ScoreboardExtractor(ROOT)
                result = extractor.process(
                    input_path, output_dir, sample_every=sample_every,
                    save_video=True, use_ocr=use_ocr,
                )
        except Exception as exc:
            st.error(f"Processing failed: {exc}")
            st.exception(exc)
        else:
            st.success("Scoreboard extracted successfully!")
            final_scoreboard = result["final_scoreboard"]
            columns = st.columns(len(final_scoreboard))
            for column, row in zip(columns, final_scoreboard):
                score = row["score"] if row["score"] is not None else "—"
                column.metric(row["player"], score)

            st.subheader("Final scoreboard")
            st.dataframe(final_scoreboard, hide_index=True, use_container_width=True)

            info = result["video_info"]
            metric_columns = st.columns(3)
            metric_columns[0].metric("Detected observations", len(result["observations"]))
            metric_columns[1].metric("Video duration", f"{info['duration_sec']:.1f} sec")
            metric_columns[2].metric("Resolution", f"{info['width']} × {info['height']}")

            with st.expander("View frame observations"):
                observation_rows = []
                for observation in result["observations"]:
                    for row in observation["rows"]:
                        observation_rows.append({
                            "Frame": observation["frame"],
                            "Time (sec)": observation["time_sec"],
                            "Player": row["player"],
                            "Score": row["score"],
                            "Confidence": row["confidence"],
                            "Method": row["method"],
                        })
                st.dataframe(observation_rows, hide_index=True, use_container_width=True)

            json_bytes = json.dumps(result, indent=2).encode("utf-8")
            csv_bytes = (output_dir / "scoreboard_data.csv").read_bytes()
            video_bytes = (output_dir / "detected_scoreboard.mp4").read_bytes()
            st.subheader("Download results")
            download_columns = st.columns(3)
            download_columns[0].download_button("⬇️ JSON", json_bytes, "scoreboard_data.json", "application/json", use_container_width=True)
            download_columns[1].download_button("⬇️ CSV", csv_bytes, "scoreboard_data.csv", "text/csv", use_container_width=True)
            download_columns[2].download_button("⬇️ Annotated video", video_bytes, "detected_scoreboard.mp4", "video/mp4", use_container_width=True)

            with st.expander("Preview annotated video"):
                st.video(video_bytes)

            render_analysis_dashboard(result)

           