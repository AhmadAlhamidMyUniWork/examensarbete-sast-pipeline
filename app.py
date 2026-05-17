import io
import json
import time
import uuid
import zipfile
from typing import Any, Dict

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import streamlit as st

from scanner import get_tool_runtime_status, run_full_scan

SEVERITY_ORDER = ["critical", "high", "medium", "low"]
SEVERITY_COLORS = {
    "critical": "#8B0000",
    "high": "#D62728",
    "medium": "#FF7F0E",
    "low": "#2CA02C",
}
STATE_DEFAULTS = {
    "report": None,
    "job_id": None,
    "elapsed": None,
    "filtered_df": None,
    "last_file": None,
}


def _inject_styles() -> None:
    st.markdown(
        """
        <style>
            .block-container {
                padding-top: 1.2rem;
                padding-bottom: 2rem;
                max-width: 1400px;
            }
            .status-chip {
                display: inline-block;
                padding: 0.2rem 0.6rem;
                border-radius: 999px;
                font-size: 0.78rem;
                font-weight: 700;
                letter-spacing: 0.03em;
            }
            .status-pass { background: #d1fae5; color: #065f46; }
            .status-warn { background: #fef3c7; color: #92400e; }
            .status-fail { background: #fee2e2; color: #991b1b; }
            .tool-ok { color: #065f46; font-weight: 600; }
            .tool-missing { color: #991b1b; font-weight: 600; }
            [data-testid="stMetricValue"] {
                font-size: 2rem;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _init_state() -> None:
    for key, value in STATE_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _decision_chip(decision: str) -> str:
    d = (decision or "").upper()
    if d == "PASS":
        klass = "status-pass"
    elif d == "WARN":
        klass = "status-warn"
    else:
        klass = "status-fail"
    return f'<span class="status-chip {klass}">{d or "UNKNOWN"}</span>'


def _figure_bytes(fig: plt.Figure, fmt: str) -> bytes:
    buf = io.BytesIO()
    save_kwargs: Dict[str, Any] = {"format": fmt, "bbox_inches": "tight"}
    if fmt == "png":
        save_kwargs["dpi"] = 300
    fig.savefig(buf, **save_kwargs)
    return buf.getvalue()


def _render_chart_downloads(
    fig: plt.Figure,
    chart_df: pd.DataFrame,
    chart_id: str,
    chart_title: str,
    job_id: str,
    export_files: Dict[str, bytes],
) -> None:
    st.pyplot(fig, use_container_width=True)
    png_bytes = _figure_bytes(fig, "png")
    svg_bytes = _figure_bytes(fig, "svg")
    csv_bytes = chart_df.to_csv(index=False).encode("utf-8")
    plt.close(fig)

    export_files[f"{chart_id}.png"] = png_bytes
    export_files[f"{chart_id}.svg"] = svg_bytes
    export_files[f"{chart_id}.csv"] = csv_bytes

    c1, c2, c3 = st.columns(3)
    c1.download_button(
        f"Download {chart_title} (PNG)",
        data=png_bytes,
        file_name=f"{chart_id}_{job_id}.png",
        mime="image/png",
        key=f"{chart_id}_{job_id}_png",
        use_container_width=True,
    )
    c2.download_button(
        f"Download {chart_title} (SVG)",
        data=svg_bytes,
        file_name=f"{chart_id}_{job_id}.svg",
        mime="image/svg+xml",
        key=f"{chart_id}_{job_id}_svg",
        use_container_width=True,
    )
    c3.download_button(
        f"Download {chart_title} data (CSV)",
        data=csv_bytes,
        file_name=f"{chart_id}_{job_id}.csv",
        mime="text/csv",
        key=f"{chart_id}_{job_id}_csv",
        use_container_width=True,
    )


def render_publication_charts(findings_df: pd.DataFrame, job_id: str) -> None:
    if findings_df.empty:
        st.info("No findings available for chart generation.")
        return

    sns.set_theme(style="whitegrid", context="paper")
    st.caption(
        "High-resolution figures (300 DPI) for reports and research appendices. "
        "Each chart includes PNG, SVG, and source CSV downloads."
    )

    export_files: Dict[str, bytes] = {}
    tabs = st.tabs(
        [
            "Figure 1: Severity",
            "Figure 2: Tool x Severity",
            "Figure 3: Category",
            "Figure 4: Top Files",
            "Figure 5: Tool Overlap",
        ]
    )

    with tabs[0]:
        sev_series = findings_df["severity"].fillna("medium").astype(str).str.lower()
        sev_counts = sev_series.value_counts().reindex(SEVERITY_ORDER, fill_value=0)
        sev_plot_df = pd.DataFrame({"severity": sev_counts.index, "count": sev_counts.values})

        fig, ax = plt.subplots(figsize=(7.5, 4.5))
        ax.bar(
            sev_plot_df["severity"].str.title(),
            sev_plot_df["count"],
            color=[SEVERITY_COLORS.get(s, "#888888") for s in sev_plot_df["severity"]],
            edgecolor="#1f1f1f",
            linewidth=0.6,
        )
        ax.set_title("Figure 1. Finding Counts by Severity", fontsize=12, fontweight="bold")
        ax.set_xlabel("Severity")
        ax.set_ylabel("Number of findings")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.grid(axis="y", linestyle="--", alpha=0.4)
        _render_chart_downloads(
            fig=fig,
            chart_df=sev_plot_df,
            chart_id="figure_1_severity_distribution",
            chart_title="Figure 1",
            job_id=job_id,
            export_files=export_files,
        )

    with tabs[1]:
        matrix_df = findings_df.copy()
        matrix_df["severity"] = matrix_df["severity"].fillna("medium").astype(str).str.lower()
        matrix_df["tool"] = matrix_df["tool"].fillna("unknown").astype(str)
        pivot = (
            matrix_df.pivot_table(
                index="tool",
                columns="severity",
                values="fingerprint",
                aggfunc="count",
                fill_value=0,
            )
            .reindex(columns=SEVERITY_ORDER, fill_value=0)
            .sort_index()
        )
        pivot_plot_df = pivot.reset_index()

        fig, ax = plt.subplots(figsize=(8.5, 4.8))
        sns.heatmap(
            pivot,
            annot=True,
            fmt="d",
            cmap="YlOrRd",
            linewidths=0.5,
            linecolor="#f5f5f5",
            cbar_kws={"label": "Findings"},
            ax=ax,
        )
        ax.set_title("Figure 2. Findings by Tool and Severity", fontsize=12, fontweight="bold")
        ax.set_xlabel("Severity")
        ax.set_ylabel("Tool")
        _render_chart_downloads(
            fig=fig,
            chart_df=pivot_plot_df,
            chart_id="figure_2_tool_severity_matrix",
            chart_title="Figure 2",
            job_id=job_id,
            export_files=export_files,
        )

    with tabs[2]:
        cat_counts = (
            findings_df["category"]
            .fillna("unknown")
            .astype(str)
            .value_counts()
            .head(12)
            .sort_values(ascending=True)
        )
        cat_plot_df = pd.DataFrame({"category": cat_counts.index, "count": cat_counts.values})

        fig, ax = plt.subplots(figsize=(8.2, 5.0))
        ax.barh(
            cat_plot_df["category"],
            cat_plot_df["count"],
            color="#1F77B4",
            edgecolor="#1f1f1f",
            linewidth=0.6,
        )
        ax.set_title("Figure 3. Findings by Category", fontsize=12, fontweight="bold")
        ax.set_xlabel("Number of findings")
        ax.set_ylabel("Category")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.grid(axis="x", linestyle="--", alpha=0.4)
        _render_chart_downloads(
            fig=fig,
            chart_df=cat_plot_df,
            chart_id="figure_3_category_distribution",
            chart_title="Figure 3",
            job_id=job_id,
            export_files=export_files,
        )

    with tabs[3]:
        file_counts = (
            findings_df["file"]
            .fillna("unknown")
            .replace("", "unknown")
            .astype(str)
            .value_counts()
            .head(12)
            .sort_values(ascending=True)
        )
        file_plot_df = pd.DataFrame({"file": file_counts.index, "count": file_counts.values})

        fig, ax = plt.subplots(figsize=(9.0, 5.4))
        ax.barh(
            file_plot_df["file"],
            file_plot_df["count"],
            color="#17A2B8",
            edgecolor="#1f1f1f",
            linewidth=0.6,
        )
        ax.set_title("Figure 4. Top Files by Finding Count", fontsize=12, fontweight="bold")
        ax.set_xlabel("Number of findings")
        ax.set_ylabel("File")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.grid(axis="x", linestyle="--", alpha=0.4)
        _render_chart_downloads(
            fig=fig,
            chart_df=file_plot_df,
            chart_id="figure_4_top_files",
            chart_title="Figure 4",
            job_id=job_id,
            export_files=export_files,
        )
    with tabs[4]:
        if "tools" not in findings_df.columns:
            st.info("No tools overlap data available.")
        else:
            tools_exploded = findings_df.copy()
        tools_exploded["tools_count"] = tools_exploded["tools"].apply(
            lambda x: len(x) if isinstance(x, list) else 1
        )
        all_tools = sorted({
            t for row in findings_df["tools"]
            if isinstance(row, list) for t in row
        })
        overlap_rows = []
        for tool in all_tools:
            unique = findings_df[
                findings_df["tools"].apply(
                    lambda x: isinstance(x, list)
                    and len(x) == 1
                    and x[0] == tool
                )
            ].shape[0]
            shared = findings_df[
                findings_df["tools"].apply(
                    lambda x: isinstance(x, list)
                    and len(x) > 1
                    and tool in x
                )
            ].shape[0]
            overlap_rows.append({
                "tool": tool,
                "unique": unique,
                "shared": shared
            })
        overlap_df = pd.DataFrame(overlap_rows)

        fig, ax = plt.subplots(figsize=(8.5, 4.8))
        x = range(len(overlap_df))
        width = 0.35
        ax.bar(
            [i - width/2 for i in x],
            overlap_df["unique"],
            width,
            label="Unique findings",
            color="black"
        )
        ax.bar(
            [i + width/2 for i in x],
            overlap_df["shared"],
            width,
            label="Shared findings",
            color="gray"
        )
        ax.set_xticks(list(x))
        ax.set_xticklabels(overlap_df["tool"], fontsize=10)
        ax.set_ylabel("Finding count")
        ax.set_title(
            "Figure 5. Tool Overlap — Unique vs Shared Findings",
            fontsize=12,
            fontweight="bold"
        )
        ax.legend()
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        _render_chart_downloads(
            fig=fig,
            chart_df=overlap_df,
            chart_id="figure_5_tool_overlap",
            chart_title="Figure 5",
            job_id=job_id,
            export_files=export_files,
        )
        
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, file_bytes in export_files.items():
            zf.writestr(name, file_bytes)
    st.download_button(
        label="Download all publication charts (ZIP)",
        data=zip_buf.getvalue(),
        file_name=f"publication_charts_{job_id}.zip",
        mime="application/zip",
        key=f"publication_charts_{job_id}_zip",
        use_container_width=True,
    )


def _normalize_findings_df(findings: Any) -> pd.DataFrame:
    if not findings:
        return pd.DataFrame()
    df = pd.DataFrame(findings)
    for col in [
        "severity",
        "category",
        "tool",
        "file",
        "start_line",
        "end_line",
        "message",
        "recommendation",
        "rule_id",
        "confidence",
        "fingerprint",
    ]:
        if col not in df.columns:
            df[col] = ""

    df["severity"] = df["severity"].fillna("medium").astype(str).str.lower()
    column_order = [
        "severity",
        "category",
        "tool",
        "file",
        "start_line",
        "message",
        "recommendation",
        "rule_id",
        "confidence",
    ]
    ordered = [c for c in column_order if c in df.columns]
    df = df[ordered + [c for c in df.columns if c not in ordered]]
    return df


def _ordered_unique(series: pd.Series, preferred: list[str] | None = None) -> list[str]:
    values = [v for v in series.dropna().astype(str).unique().tolist() if v]
    if preferred:
        preferred_set = [v for v in preferred if v in values]
        rest = sorted([v for v in values if v not in preferred_set])
        return preferred_set + rest
    return sorted(values)


st.set_page_config(page_title="AI Code Security Scanner (Prototype)", layout="wide")
_init_state()
_inject_styles()

st.title("AI-generated Python Code Security Scanner")
st.caption(
    "Upload a ZIP of source code. The app safely extracts files and runs Bandit, Semgrep, detect-secrets, and pip-audit."
)

with st.expander("Assumptions / Notes", expanded=False):
    st.markdown(
        """
- This prototype **does not execute** uploaded code.
- Results are best-effort and may include false positives.
- Dependency CVE coverage is strongest when **requirements.txt** or **pyproject.toml** is present.
"""
    )

with st.sidebar:
    st.header("Scan Settings")
    max_total_mb = st.number_input(
        "Max extracted size (MB)", min_value=50, max_value=2000, value=500, step=50
    )
    max_files = st.number_input(
        "Max file count", min_value=1000, max_value=200000, value=50000, step=1000
    )
    st.divider()
    st.subheader("Tool Runtime")
    tool_status = get_tool_runtime_status()
    for tool_name, meta in tool_status.items():
        klass = "tool-ok" if meta.get("available") else "tool-missing"
        label = "Available" if meta.get("available") else "Missing"
        st.markdown(
            f"<span class='{klass}'>{tool_name}: {label}</span>",
            unsafe_allow_html=True,
        )
        st.caption(meta.get("resolved_path", ""))

uploaded = st.file_uploader(
    "Upload ZIP file",
    type=["zip"],
    accept_multiple_files=False,
    help="Upload a .zip containing your project.",
)

if uploaded is not None:
    st.info(f"Selected file: {uploaded.name} ({len(uploaded.getvalue()) / 1024:.1f} KB)")

action_col1, action_col2, action_col3 = st.columns([1.2, 1.2, 4])
scan_clicked = action_col1.button(
    "Run scan",
    type="primary",
    disabled=(uploaded is None),
    use_container_width=True,
)
clear_clicked = action_col2.button("Clear results", use_container_width=True)

if clear_clicked:
    for key, value in STATE_DEFAULTS.items():
        st.session_state[key] = value
    st.rerun()

if scan_clicked and uploaded is not None:
    job_id = str(uuid.uuid4())
    with st.status("Running security scan", expanded=True) as status:
        status.write("Preparing archive and applying extraction safety checks")
        started = time.time()
        report = run_full_scan(
            zip_bytes=uploaded.getvalue(),
            job_id=job_id,
            max_total_bytes=int(max_total_mb * 1024 * 1024),
            max_files=int(max_files),
        )
        elapsed = time.time() - started
        status.write("Collecting findings and building report")
        if report.get("status") == "ok":
            status.update(label="Scan complete", state="complete")
        else:
            status.update(label="Scan failed", state="error")

    st.session_state["job_id"] = job_id
    st.session_state["report"] = report
    st.session_state["elapsed"] = elapsed
    st.session_state["last_file"] = uploaded.name

report = st.session_state.get("report")
job_id = st.session_state.get("job_id")
elapsed = st.session_state.get("elapsed")

if report:
    decision = report.get("decision", "FAIL")
    status = report.get("status", "error")
    summary = report.get("summary", {})
    sev_counts = summary.get("severity_counts", {})

    info_col, dl_col = st.columns([3.4, 1.6])
    with info_col:
        if status == "ok":
            st.success(
                f"Scan completed in {elapsed:.1f}s for `{st.session_state.get('last_file', 'uploaded.zip')}`. "
                f"Decision: {decision}"
            )
        else:
            st.error(report.get("error", "Scan failed."))
        st.markdown(f"Policy decision: {_decision_chip(decision)}", unsafe_allow_html=True)
        st.caption(f"Job ID: {job_id}")
    with dl_col:
        st.download_button(
            label="Download report (JSON)",
            data=json.dumps(report, indent=2).encode("utf-8"),
            file_name=f"scan_report_{job_id}.json",
            mime="application/json",
            use_container_width=True,
        )

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Critical", sev_counts.get("critical", 0))
    m2.metric("High", sev_counts.get("high", 0))
    m3.metric("Medium", sev_counts.get("medium", 0))
    m4.metric("Low", sev_counts.get("low", 0))
    m5.metric("Total", summary.get("total", 0))

    findings_df = _normalize_findings_df(report.get("findings", []))
    result_tabs = st.tabs(["Findings", "Publication Charts", "Tool Logs", "Raw JSON"])

    with result_tabs[0]:
        if findings_df.empty:
            st.warning("No findings returned (or tools could not run). Check Tool Logs.")
            st.session_state["filtered_df"] = findings_df
        else:
            c1, c2, c3, c4 = st.columns([1.2, 1.2, 1.2, 2])
            severity_options = _ordered_unique(findings_df["severity"], preferred=SEVERITY_ORDER)
            tool_options = _ordered_unique(findings_df["tool"])
            category_options = _ordered_unique(findings_df["category"])

            with c1:
                sev_filter = st.multiselect(
                    "Severity",
                    options=severity_options,
                    default=severity_options,
                    key="findings_sev_filter",
                )
            with c2:
                tool_filter = st.multiselect(
                    "Tool",
                    options=tool_options,
                    default=tool_options,
                    key="findings_tool_filter",
                )
            with c3:
                cat_filter = st.multiselect(
                    "Category",
                    options=category_options,
                    default=category_options,
                    key="findings_cat_filter",
                )
            with c4:
                query = st.text_input(
                    "Search message/file/rule",
                    value="",
                    key="findings_text_query",
                    placeholder="e.g. eval, token, requirements.txt",
                ).strip().lower()

            filtered_df = findings_df[
                findings_df["severity"].isin(sev_filter)
                & findings_df["tool"].isin(tool_filter)
                & findings_df["category"].isin(cat_filter)
            ]
            if query:
                text_cols = ["message", "file", "rule_id", "category", "tool"]
                mask = pd.Series(False, index=filtered_df.index)
                for col in text_cols:
                    mask = mask | filtered_df[col].astype(str).str.lower().str.contains(query, na=False)
                filtered_df = filtered_df[mask]

            st.session_state["filtered_df"] = filtered_df
            st.caption(f"Showing {len(filtered_df)} of {len(findings_df)} findings")

            st.dataframe(
                filtered_df,
                use_container_width=True,
                height=460,
                column_config={
                    "message": st.column_config.TextColumn(width="large"),
                    "recommendation": st.column_config.TextColumn(width="large"),
                    "file": st.column_config.TextColumn(width="medium"),
                },
            )

            st.download_button(
                "Download filtered findings (CSV)",
                data=filtered_df.to_csv(index=False).encode("utf-8"),
                file_name=f"filtered_findings_{job_id}.csv",
                mime="text/csv",
            )

    with result_tabs[1]:
        source = st.radio(
            "Chart data source",
            options=["Filtered findings", "All findings"],
            horizontal=True,
            index=0,
        )
        chart_df = (
            st.session_state.get("filtered_df")
            if source == "Filtered findings"
            else findings_df
        )
        if chart_df is None or chart_df.empty:
            st.info("No data available for charts with the current selection.")
        else:
            render_publication_charts(chart_df, job_id=job_id)

    with result_tabs[2]:
        tool_logs = report.get("tool_logs", {}) or {}
        if not tool_logs:
            st.info("No tool logs available.")
        else:
            for tool_name, tool_log in tool_logs.items():
                preview = (tool_log or "(no output)").splitlines()
                preview_text = preview[0][:120] if preview else "(no output)"
                with st.expander(f"{tool_name} | {preview_text}", expanded=False):
                    st.code(tool_log or "(no output)")

    with result_tabs[3]:
        st.json(report)

else:
    st.info("Upload a ZIP and click Run scan to generate findings, charts, and exportable reports.")
