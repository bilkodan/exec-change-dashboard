import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

st.set_page_config(
    page_title="Exec Change Dashboard",
    page_icon="🚨",
    layout="wide",
)

st.title("🚨 Exec Change Intelligence Dashboard")
st.caption("Tracks U.S.-born CEO → Indian-origin CEO replacements at public companies via SEC EDGAR")


@st.cache_data(ttl=60)
def load_data() -> pd.DataFrame:
    try:
        conn = sqlite3.connect("exec_changes.db", check_same_thread=False)
        df = pd.read_sql("SELECT * FROM changes ORDER BY filed_at DESC", conn)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()


df = load_data()

# ── Summary metrics ───────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total CEO Events", len(df))

if not df.empty and {"outgoing_us", "incoming_indian", "trade_signal", "filed_at"}.issubset(df.columns):
    alerts_df = df[(df["outgoing_us"] >= 0.5) & (df["incoming_indian"] >= 0.5)]
    watch_count = (df["trade_signal"] == "WATCH").sum()
    latest_date = df["filed_at"].max()
else:
    alerts_df = pd.DataFrame()
    watch_count = 0
    latest_date = "—"

c2.metric("🔔 US→Indian Alerts", len(alerts_df))
c3.metric("WATCH Signals", watch_count)
c4.metric("Latest Filing", latest_date)

# ── Primary alert table ───────────────────────────────────────────────────────
st.subheader("🔔 U.S.-Born CEO → Indian-Origin CEO Replacements")

COLS = ["filed_at", "company", "ticker", "outgoing", "incoming",
        "outgoing_us", "incoming_indian", "signal_score", "trade_signal"]

if alerts_df.empty:
    st.info("No US→Indian CEO replacements detected yet. The worker polls SEC EDGAR every 5 minutes.")
else:
    show = [c for c in COLS if c in alerts_df.columns]
    st.dataframe(
        alerts_df[show],
        use_container_width=True,
        hide_index=True,
        column_config={
            "outgoing_us": st.column_config.ProgressColumn(
                "Outgoing US Score", min_value=0, max_value=1, format="%.2f"
            ),
            "incoming_indian": st.column_config.ProgressColumn(
                "Incoming Indian Score", min_value=0, max_value=1, format="%.2f"
            ),
            "signal_score": st.column_config.ProgressColumn(
                "Signal Score", min_value=0, max_value=1, format="%.3f"
            ),
        },
    )

# ── All changes ───────────────────────────────────────────────────────────────
with st.expander("📋 All Executive Changes", expanded=False):
    if df.empty:
        st.info("No data yet.")
    else:
        show_all = [c for c in COLS if c in df.columns]
        st.dataframe(df[show_all] if show_all else df, use_container_width=True, hide_index=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
col_left, col_right = st.columns([5, 1])
col_left.caption(f"Data source: SEC EDGAR · Last page load: {datetime.now():%Y-%m-%d %H:%M:%S}")
if col_right.button("🔄 Refresh"):
    st.cache_data.clear()
    st.rerun()
